# Preprocessing TK2: snapshot → preprocess → review → audit

Pipeline ini mengubah raw JSONL hasil kolektor menjadi dataset kandidat, subset model-ready, log
eksklusi, antrean review, dan laporan kualitas. Pipeline ini **terpisah** dari kolektor
(`twscrape_pipeline.py`, launcher `.cmd`) dan dari `03_preprocess.py` lama. Pipeline tidak
menghentikan atau menjalankan kolektor, tidak membaca kredensial, dan tidak mengubah `data/raw/`.

Tahap ini **persiapan data**, bukan pelatihan model. Tidak ada label sentimen/topik yang dibuat.

## Instalasi

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-preprocess.txt
```

Run referensi memakai Python 3.13.7, pandas 3.0.0, numpy 2.4.2, dan scikit-learn 1.8.0. Versi aktual
setiap run tercatat di `snapshot_manifest.json`.

## Perintah

```powershell
python preprocess_tk2.py snapshot                # 1. bekukan raw
python preprocess_tk2.py run                     # 2. proses snapshot terbaru (atau --snapshot ID)
python preprocess_tk2.py import-review FILE.csv  # 3. masukkan keputusan peninjau (append-only)
python preprocess_tk2.py run                     #    jalankan ulang agar keputusan diterapkan
python preprocess_tk2.py audit                   # 4. cek rekonsiliasi & integritas
python preprocess_tk2.py all                     # snapshot + run + audit sekaligus
python -m unittest test_preprocess_tk2 test_promosi -v
```

`run` dan `audit` memakai snapshot terbaru bila `--snapshot` tidak diberikan.

## 1. Snapshot

- Setiap `data/raw/x_*.jsonl` dan `threads_*.jsonl` dibaca sekali sebagai bytes, lalu dipotong pada
  newline fisik terakhir. Baris terakhir yang belum lengkap (misalnya kolektor sedang menulis) tidak
  diambil. Jumlah byte-nya dicatat sebagai `incomplete_tail_bytes`.
- Pemisahan record memakai `b"\n"`, bukan `str.splitlines()`, karena 48 teks X memuat U+2028/U+2029.
- Salinan disimpan di `data/interim/snapshots/<id>/raw/`. Folder ini diabaikan Git karena masih memuat
  username. Log/checkpoint kolektor ikut dibekukan di `raw/_meta/` untuk audit cakupan.
- `snapshot_manifest.json` mencatat file, ukuran saat dibaca, batas byte, jumlah record, SHA-256,
  waktu UTC/WIB, metode, commit Git, hash file kode, dan versi dependensi. Environment, cookie, dan
  database sesi tidak dibaca.
- ID snapshot = tanggal + hash isi. Input yang sama menghasilkan ID dan output yang sama (idempoten).
  Karena raw bersifat append-only, `tk2prep.snapshot.rekonstruksi_dari_raw()` dapat membangun ulang
  salinan dari batas byte dan hash.
- Pembacaan antarfile berurutan dan **tidak atomic**. Kolektor yang menulis di tengah snapshot
  dapat membuat file yang dibaca belakangan memuat record yang lebih baru.

## 2. Run: urutan pengolahan

1. **Validasi per record.** ID wajib string. ID numerik dikonversi dan ditandai, sedangkan ID float
   dikarantina karena presisinya hilang. Teks tidak boleh kosong. Timestamp harus timezone-aware.
   Platform harus konsisten. Engagement yang tidak ada tetap `null` (bukan 0). Nilai negatif atau
   bukan angka menjadi `null` dan diberi flag. Record invalid masuk `karantina.csv` beserta alasannya.
2. **Dedup `(platform, post_id)`.** Teks dipilih dengan urutan: `text_truncated=False`, lalu
   `None` (tidak diketahui), lalu `True`; kemudian teks terpanjang; kemudian pengambilan terbaru.
   Engagement diambil dari pengambilan terbaru dan waktunya dicatat. Konflik versi disimpan di
   `konflik_versi_id.csv`.
3. **Waktu.** `created_at_asal` disimpan apa adanya. Fase dihitung dari waktu WIB aktual dengan
   interval `[awal 00:00 WIB, akhir 00:00 WIB)` dari `config.JENDELA_WAKTU`.
4. **Relevansi** (`relevansi.py`, v2) dinilai dari bukti di teks, bukan dari kueri gabungan OR.
   Untuk platform di `config.RELEVANSI_KONTEKS_DIABAIKAN` (saat ini Threads), post jalur konteks
   (tanpa nama program di teks) langsung di-exclude dengan alasan `relevansi_konteks_tidak_dipakai`,
   bukan pending. Keputusan reviewer manusia tetap menang.
5. **Promosi** (`promosi.py`, v4): penawaran dengan bukti jelas di-exclude, kasus ambigu masuk
   review, dan permintaan/kritik/diskusi uang saku tetap dipertahankan. Sejak v4 juga di-exclude:
   pengumuman lowongan dari instansi/perusahaan mitra (`pengumuman_lowongan_mitra`), iklan jasa
   titipan "chat @akun + layanan + bukti jual" (`layanan_dengan_kontak_dan_bukti_jual`), dan ajakan
   ikut webinar/pelatihan (`promosi_acara_pelatihan`).
6. **Akun.** Akun di daftar config diberi label `resmi`/`media`. `meta.ai` di-exclude sebagai akun
   otomatis. Label `tidak_terdaftar` belum berarti akun publik.
7. **Versi teks** (`tk2prep/teks.py`): lihat tabel di bawah.
8. **Grup duplikat.** Teks identik dan near-duplicate hanya ditandai, tidak dihapus. Hasilnya juga
   dipakai untuk `split_group_id`.
9. **Keputusan akhir.** Keputusan manusia dari `data/annotations/` menang atas aturan.
   Setiap post mendapat tepat satu `status_final` (`keep`/`pending`/`exclude`) dan satu
   `alasan_utama` (urutan: di luar jendela > akun otomatis > relevansi > promosi). Alasan lain
   disimpan di `alasan_lain`.

### Versi teks

| Kolom | Untuk | Isi |
|---|---|---|
| `text_minimal` | baseline/arsip analitik | NFC, unescape HTML (`&amp;`), whitespace, masking `[URL]` `[USER]` `[EMAIL]` `[PHONE]` `[NIK]`. Emoji (termasuk ZWJ/variation selector), negasi, tanda baca, kapitalisasi, hashtag, urutan kata, dan pemanjangan huruf dipertahankan. |
| `text_sentiment` | input transformer sentimen | `text_minimal` dengan deret `[USER]` pembuka reply diringkas menjadi satu. Tanpa stemming, stopword removal, atau normalisasi slang. Casing/tokenisasi mengikuti tokenizer model yang dipilih nanti. |
| `text_sentiment_slang_v1` + `slang_v1_ganti` | varian eksperimen | 22 slang tak ambigu (`yg`, `gak`, `bgt`, …). `u`, `sm`, `kl`, `km` sengaja tidak dinormalisasi. Setiap penggantian dicatat (posisi, asal, hasil) sehingga dapat dibalik. Tidak otomatis lebih baik. |
| `text_embedding` | sentence embedding BERTopic | Konteks utuh: tanpa `[URL]`, tanpa alamat reply, `#` dilepas (`#MagangHub` → `Magang Hub`). Stopword tidak dibuang. |
| `text_topic_repr` | CountVectorizer/c-TF-IDF setelah clustering | Huruf kecil (NFKC), tanpa placeholder/angka/emoji/tanda baca, stopword fungsi dibuang (`stopword_topik.txt`). Negasi, kata domain, dan nama program tetap ada. Parameter vectorizer ada di `vectorizer_config.json`. |

Colloquial Indonesian Lexicon (`data/lexicon/`, Salsabila dkk. 2018) **tidak diterapkan** karena
banyak entrinya ambigu atau bergantung konteks. Keputusan ini tercatat di `config_preprocess.json`.

## 3. Review manusia

- `antrean_review_<platform>.csv` berisi semua post `pending`. `sampel_review_<platform>.csv` berisi
  maksimal 200 post berstrata (status × fase × kolektor, seed 20261026) dengan `bobot` dan 40 baris
  `kalibrasi_dua_peninjau`. Panduan nilai ada di `PANDUAN_LABEL.md`.
- Isi `reviewer` dan kolom keputusan, lalu jalankan `import-review`. Keputusan ditambahkan ke
  `data/annotations/review_decisions_log.csv` (append-only) dan digabung berdasarkan
  `(platform, post_id)`.
  - Sel kosong tidak menghapus keputusan lama.
  - Jika reviewer tidak sepakat, status menjadi `konflik` (pending).
  - Reviewer `auto`/`agent`/`model` ditolak.
  - `post_id` yang rusak oleh spreadsheet (`2.09E+18`) ditolak.
- Rerun tidak menimpa keputusan. Folder anotasi berada di luar folder output versi.

## 4. Output `data/processed/preprocess_<snapshot_id>/`

X ada di root folder, Threads di subfolder `threads/` dengan skema yang sama. Kedua korpus tidak
dicampur.

| Berkas | Isi |
|---|---|
| `dataset_<p>_semua_keputusan.csv` | semua post unik + versi teks, metadata, provenance, keputusan, dan flag |
| `model_ready_<p>.csv` / `.jsonl` | status `keep`. JSONL menjaga `post_id` tetap string |
| `model_ready_<p>_tanpa_resmi_media.csv` | tanpa akun resmi/media (daftar config atau keputusan manual) |
| `model_ready_<p>_satu_per_teks_identik.csv` | satu wakil per teks identik. Opsional untuk BERTopic agar template berulang tidak membentuk klaster semu |
| `exclusion_log_<p>.csv`, `karantina.csv`, `konflik_versi_id.csv` | log eksklusi, record invalid, dan konflik versi |
| `antrean_review_<p>.csv`, `sampel_review_<p>.csv`, `PANDUAN_LABEL.md` | bahan review |
| `tahapan_<p>.csv` | hitungan tiap tahap yang dapat direkonsiliasi dengan snapshot |
| `distribusi_*`, `pergeseran_fase_*`, `tumpang_tindih_*`, `missingness_*` | distribusi status per fase/tanggal/kolektor/jenis konten, perubahan distribusi akibat filter, dan missingness |
| `cakupan_harian_x.csv`, `threads/cakupan_threads_log.csv` | cakupan dari log/checkpoint aktual |
| `LAPORAN_KUALITAS.md` | ringkasan angka run ini (dibuat otomatis) |
| `config_preprocess.json`, `vectorizer_config.json`, `stopword_topik.txt`, `kamus_data.csv`, `snapshot_manifest.json` | konfigurasi, kamus data, dan provenance |

Username dan URL (yang memuat username) tidak ikut ke output. `user_hash` adalah pseudonim SHA-256
bergaram dengan salt lokal `.salt` yang diabaikan Git. Ini **bukan anonimisasi sempurna**: `post_id`
dan kutipan teks tetap dapat dilacak ke post asli. Untuk publikasi, kutipan harus diparafrasakan.

### Membaca di spreadsheet / pandas

```python
pd.read_csv(path, dtype={"post_id": str, "conversation_id": str}, keep_default_na=False)
```

Di Excel, impor kolom `post_id` sebagai Teks. Jika tidak, ID 19 digit akan berubah menjadi angka
ilmiah dan rusak.

## Untuk evaluasi supervised nanti

- Pakai `split_group_id` agar teks identik atau near-duplicate tidak melintasi train/test. Pertimbangkan
  split per `user_hash` (generalisasi lintas penulis) atau split temporal (prediksi periode berikutnya)
  sesuai klaim yang ingin dibuat.
- Fit vocabulary/statistik (TF-IDF, normalisasi, threshold) hanya pada train.
- Jangan melakukan balancing dengan label palsu. Topic modeling eksploratif pada satu korpus tidak
  memerlukan train/test.

## Hubungan dengan skrip lama

`03_preprocess.py` dan `04_audit_collection.py` tetap ada untuk launcher kolektor dan masih menulis
ke `data/processed/*.csv` lama. Keduanya kini memakai `promosi_v4` dan perbaikan `relevansi.py`.
Output versi baru tidak menimpa file lama.
