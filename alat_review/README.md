# Alat review manusia

Alat bantu untuk mengisi `antrean_review_*.csv` dan `sampel_review_*.csv` dari
`preprocess_tk2.py`. Panduan nilai label ada di `PANDUAN_LABEL.md` pada folder output preprocessing.

## Melabeli

1. Buka `review.html` di browser (klik dua kali, tidak perlu internet atau server).
2. Isi **Reviewer** dengan inisial sendiri, lalu pilih berkas CSV:
   - X: `data/processed/preprocess_<id>/antrean_review_x.csv` atau `sampel_review_x.csv`
   - Threads: `data/processed/preprocess_<id>/threads/antrean_review_threads.csv` atau `sampel_review_threads.csv`
3. Tombol: `1`–`3` relevansi, `4`–`6` promosi, `7`/`8` privasi, `←`/`→` pindah, `Enter` berikutnya.
   Kolom lain (jenis akun, sentimen, stance, aspek, catatan) diisi dengan klik/ketik.
4. **Ekspor CSV** berkala. Progres juga tersimpan di browser, tetapi hanya di browser itu.
5. Impor hasil ekspor, lalu proses ulang:

   ```
   python preprocess_tk2.py import-review <hasil_ekspor>.csv
   python preprocess_tk2.py run
   ```

Data tidak dikirim ke mana pun; berkas hanya dibaca oleh browser di komputer sendiri.

## Presisi aturan

Dari berkas `sampel_review_*` yang sudah diisi (bukan `antrean_review_*`, karena antrean tidak
berstrata):

```
python alat_review/presisi_aturan.py data/processed/preprocess_<id>/<sampel_terisi>.csv
```

Keluarannya memakai bobot strata, sehingga berlaku untuk populasi status, bukan untuk sampel
saja. Baris `ragu` tidak dihitung sebagai benar maupun salah; jumlahnya dilaporkan terpisah
beserta batas bawah pesimistis bila seluruhnya dianggap keputusan aturan yang salah.
Tanpa argumen, skrip menjalankan pemeriksaan sendiri (`demo OK`).

## Kalibrasi dua peninjau

Pada berkas `sampel_review_*`, centang **hanya kalibrasi** (40 baris). Dua peninjau mengisi
secara terpisah dengan nama reviewer masing-masing, tanpa melihat label satu sama lain. Berkas
sampel dibekukan: `preprocess_tk2.py run` tidak mengundinya ulang, sehingga peninjau kedua
menilai 40 baris yang sama dengan peninjau pertama meski preprocessing sudah dijalankan lagi.
Petunjuk otomatis disembunyikan secara default pada berkas sampel agar penilaian tidak terarah.
Setelah kedua hasil diimpor:

```
python alat_review/kappa_kalibrasi.py
```

Dua berkas ekspor juga bisa dibandingkan langsung tanpa impor:

```
python alat_review/kappa_kalibrasi.py A.csv B.csv
```

Kalau nama peninjau di kedua berkas sama, yang terukur adalah konsistensi satu orang pada dua
kesempatan, bukan kesepakatan antarpeninjau. Skripnya memperingatkan sendiri bila itu terjadi.
