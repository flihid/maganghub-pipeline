# MagangHub Data Collection Pipeline

Pipeline pengumpulan dan *preprocessing* data media sosial X dan Threads untuk penelitian
**"Analisis Pro Kontra Publik terhadap Program Magang Nasional MagangHub pada Media Sosial X"**
(Tugas Kelompok 2, CSIE604284 Analitika Media Sosial, Fasilkom UI, Gasal 2026/2027).

Pipeline ini mengumpulkan unggahan publik berbahasa Indonesia yang menyebut Program Magang
Nasional/MagangHub dalam tiga jendela waktu penyelenggaraan program, dari X (korpus utama) dan
Threads (korpus pelengkap), lalu membersihkannya menjadi satu dataset siap analisis untuk
pemodelan topik (BERTopic) dan klasifikasi sentimen (IndoBERT).

Ringkasan hasil pengumpulan data untuk laporan bagian C ada di
[Temuan pengumpulan data](#temuan-pengumpulan-data), terbagi menjadi
[korpus X](#temuan-pengumpulan-data-x), [korpus Threads](#temuan-pengumpulan-data-threads), dan
[ringkasan gabungan](#ringkasan-gabungan-x-dan-threads).

**Penulis laporan mulai dari [Panduan menulis laporan bagian C](#panduan-menulis-laporan-bagian-c)
di bagian paling bawah.** Di sana sudah dipilihkan isi tiap subbagian C1 sampai C7, angka mana
yang dipakai, dan klaim mana yang tidak boleh ditulis. Bagian-bagian di atasnya adalah bahan
mentah yang jauh melebihi batas kata.

## Alur pipeline

```
                 X:       01_simpan_sesi.py ─────► 02_scrape_x.py ─────► data/raw/x_<fase>.jsonl ─────┐
config.py ──►                login manual           cari + scroll,                                    ├─► 03_preprocess.py ─► data/processed/
(parameter)                                         ekstrak DOM                                       │   gabung, dedup, saring,  maganghub_bersih.csv
                 Threads: 01_simpan_sesi_threads.py ► 02_scrape_threads.py ► data/raw/threads_<kata>.jsonl ┘   anonimisasi, normalisasi
                             login manual (IG)      cari + scroll,
                                                    baca JSON halaman & respons
```

## Struktur folder

```
maganghub-pipeline/
├── config.py                   # SEMUA parameter: kata kunci, jendela waktu, batas, jeda, daftar akun
├── 01_simpan_sesi.py           # X: login manual sekali, simpan cookie ke sesi_x.json
├── 02_scrape_x.py              # X: scraping hasil pencarian
├── 01_simpan_sesi_threads.py   # Threads: login manual sekali, simpan cookie ke sesi_threads.json
├── 02_scrape_threads.py        # Threads: scraping hasil pencarian
├── relevansi.py                # aturan relevansi dua jalur (dipakai cek_cakupan & preprocess)
├── cek_cakupan.py              # cek rentang tanggal & presisi kata kunci sebelum preprocessing
├── 03_preprocess.py            # pembersihan data mentah X + Threads -> dataset bersih
├── requirements.txt
└── data/
    ├── raw/                # hasil scraping mentah (tidak di-commit)
    ├── processed/          # dataset bersih (tidak di-commit)
    └── lexicon/            # kamus kata tidak baku (opsional, lihat di bawah)
```

## Instalasi (Windows, PowerShell)

Butuh Python 3.10 atau lebih baru.

```powershell
cd maganghub-pipeline
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

Jika `Activate.ps1` ditolak dengan pesan *running scripts is disabled*, jalankan sekali:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, lalu ulangi aktivasi.

**Opsional, sangat disarankan:** unduh `colloquial-indonesian-lexicon.csv` dari
<https://github.com/nasalsabila/kamus-alay> (Salsabila dkk., IALP 2018) dan letakkan di
`data/lexicon/`. Tanpa file ini, normalisasi kata tidak baku memakai ±80 entri bawaan.

## Cara menjalankan

Ringkasan urutan lengkap (X dan Threads bisa dijalankan oleh orang berbeda di laptop berbeda;
hasilnya digabung di langkah 4):

```powershell
# X (jalur yang dipakai untuk korpus final; rincian di README_TWSCRAPE.md)
python twscrape_pipeline.py plan
python twscrape_pipeline.py setup
python twscrape_pipeline.py collect --mode pilot
python twscrape_pipeline.py collect --mode full --per-day 300 --max-raw 10000

# Threads
python 01_simpan_sesi_threads.py
python 02_scrape_threads.py --uji
python 02_scrape_threads.py

# Gabungan (rincian di README_PREPROCESSING.md)
python preprocess_tk2.py snapshot
python preprocess_tk2.py run

# Peninjauan manusia (rincian di alat_review/README.md)
# Buka alat_review/review.html di browser, labeli, lalu ekspor CSV.
python preprocess_tk2.py import-review <hasil_ekspor>.csv
python preprocess_tk2.py run
python alat_review/presisi_aturan.py <hasil_ekspor_sampel>.csv
python alat_review/kappa_kalibrasi.py

# Pemeriksaan akhir
python preprocess_tk2.py audit
python cek_angka_readme.py
```

Jalur lama `02_scrape_x.py` dan `03_preprocess.py` masih ada di repositori, tetapi angka yang
dilaporkan di bagian [Temuan pengumpulan data](#temuan-pengumpulan-data) berasal dari
`preprocess_tk2.py`. Jangan mencampur keluaran kedua jalur tersebut.

`cek_angka_readme.py` memeriksa `sha256` data mentah terhadap `snapshot_manifest.json` dan
membandingkan angka utama di README dengan `tahapan_*.csv`. Jalankan setiap kali *preprocessing*
diulang; bila gagal, angka di README perlu diperbarui lebih dahulu.

### 1. Simpan sesi login (sekali per platform)

Pencarian di X maupun Threads hanya dapat diakses oleh akun yang login, sehingga langkah ini wajib.
Gunakan akun cadangan, bukan akun pribadi utama.

**X**

```powershell
python 01_simpan_sesi.py
```

Jendela Chromium terbuka. Login ke X secara manual, tunggu sampai Beranda muncul, lalu tekan
ENTER di terminal. Cookie sesi tersimpan di `sesi_x.json`.

**Threads**

```powershell
python 01_simpan_sesi_threads.py
```

Login ke Threads dengan akun Instagram, tunggu sampai beranda Threads muncul, lalu tekan ENTER.
Login lewat Instagram sering terjadi di tab atau jendela baru, sehingga skrip tidak memeriksa URL
tab pertama. Skrip menyimpan cookie dari seluruh browser ke `sesi_threads.json`, lalu membuktikan
sesi berlaku dengan membuka halaman pencarian Threads. Jika halaman itu masih mengarah ke login,
file sesi dihapus dan skrip berhenti.

Jika salah satu platform menolak login dari browser ini (misalnya muncul pesan "Kami membatasi
proses masuk Anda"), hentikan dan jangan diulang berkali-kali.

### 2. Scraping

Selalu jalankan mode `--uji` lebih dulu untuk memastikan scraper bekerja sebelum menjalankan
pengambilan penuh.

#### 2a. X (korpus utama)

```powershell
python 02_scrape_x.py --uji      # 1 kueri, 1 subjendela, maks 20 post
python 02_scrape_x.py            # semua fase
python 02_scrape_x.py --fase fase2_seleksi
```

Setiap kata kunci dijalankan untuk setiap subjendela 7 hari di dalam tiga fase
(`config.JENDELA_WAKTU`), dengan URL pencarian tab *Terbaru*:

```
https://x.com/search?q=<kata kunci> lang:id since:<YYYY-MM-DD> until:<YYYY-MM-DD>&f=live
```

Skrip **aman dihentikan dan dijalankan ulang**. Kombinasi kueri yang sudah selesai dicatat di
`data/raw/progres.json` dan dilewati; post yang sudah tersimpan tidak ditulis dua kali.

#### 2b. Threads (korpus pelengkap)

```powershell
python 02_scrape_threads.py --uji  # 1 kata kunci, maks 20 post
python 02_scrape_threads.py        # semua kata kunci di config.KATA_KUNCI_THREADS
```

Sebelum menjalankan, pastikan `config.URL_PENCARIAN_THREADS` sama dengan URL tab *Terbaru* ketika
mencari secara manual di threads.com.

Threads memakai nama class HTML yang diacak, sehingga scraper ini tidak mengandalkan selector DOM.
Data post diambil dari JSON yang dikirim Threads ke browser, yaitu JSON yang tertanam di halaman
(`<script type="application/json" data-sjs>`) dan respons yang dimuat saat halaman di-scroll.
Pencarian Threads tidak memiliki filter tanggal, sehingga hasil diurutkan dari yang terbaru dan
scroll dihentikan setelah tiga putaran berturut-turut hanya berisi post sebelum awal jendela
penelitian. Post di luar jendela dibuang di tahap *preprocessing*.

Seperti scraper X, skrip ini aman dihentikan dan dijalankan ulang (`data/raw/progres_threads.json`).
Jika Threads membalas dengan status 429 (terlalu banyak permintaan), skrip berhenti sendiri;
tunggu minimal beberapa jam sebelum menjalankan lagi.

**Jika sebuah kata kunci berhenti di `batas_maks` sebelum menjangkau awal jendela penelitian**,
ambil ulang kata kunci itu dengan batas lebih tinggi:

```powershell
python 02_scrape_threads.py --kata "magang kemnaker" --kata maganghub --maks 4000
```

Post yang sudah tersimpan tidak ditulis ulang. Skrip tetap scroll melewatinya, karena deteksi
"hasil sudah habis" dihitung dari post yang terlihat, bukan dari post yang disimpan. Kolom
`tertua_terlihat` di `log_scraping_threads.csv` mencatat sejauh mana scroll menjangkau.

### 3. Cek cakupan sebelum preprocessing

```powershell
python cek_cakupan.py
python cek_cakupan.py --contoh "magang kemnaker"   # contoh post yang tidak lolos saring relevansi
```

Menampilkan, per platform dan kata kunci: jumlah post, rentang tanggal, apakah fase 1 tercakup,
persentase post yang relevan (presisi kata kunci), dan sebaran post relevan per fase.
Angka-angka ini bahan langsung untuk bagian C4 dan C5 laporan.

### 4. Preprocessing

```powershell
python 03_preprocess.py
```

Skrip ini membaca semua `data/raw/x_*.jsonl` dan `data/raw/threads_*.jsonl` sekaligus. Jika X dan
Threads di-*scrape* di laptop berbeda, salin file `.jsonl` dari kedua laptop ke satu folder
`data/raw` sebelum menjalankan langkah ini. Data dari satu platform saja juga bisa diproses.

## Keluaran

### `data/raw/x_<fase>.jsonl` — data mentah, satu post per baris

| Kolom | Isi |
|---|---|
| `tweet_id` | ID unik post (kunci deduplikasi; nama kolom dipertahankan untuk kedua platform) |
| `url` | permalink post |
| `username` | handle pembuat post (dihapus di tahap *preprocessing*) |
| `created_at` | waktu unggah, ISO 8601 UTC |
| `text` | isi teks post |
| `n_reply`, `n_repost`, `n_like` | metrik keterlibatan saat di-*scrape* |
| `fase`, `kueri`, `since`, `until` | parameter pencarian yang menjaring post ini |
| `scraped_at` | waktu pengambilan data, UTC |

Nama tampilan, foto profil, bio, jumlah pengikut, dan media **tidak diambil** karena tidak
diperlukan untuk menjawab pertanyaan penelitian (prinsip minimalisasi data).

### `data/raw/threads_<kata-kunci>.jsonl`
Kolom sama dengan file X, ditambah `platform = threads`. ID post diberi awalan `th_` agar tidak
bentrok dengan ID X. `fase`, `since`, dan `until` kosong karena ditetapkan di tahap *preprocessing*.

### `data/raw/log_scraping.csv` dan `log_scraping_threads.csv`
Satu baris per kombinasi kueri: jumlah post baru, status (`selesai`, `batas_maks`,
`tidak_ada_hasil`, `timeout`, `error_x`, `sesi_kedaluwarsa`, `dibatasi_429`,
`melewati_awal_jendela`), dan durasi.

### `data/processed/maganghub_bersih.csv` — dataset siap analisis

| Kolom | Isi |
|---|---|
| `post_id` | ID post (untuk keperluan internal tim; jangan dipublikasikan) |
| `platform` | `x` atau `threads` |
| `user_hash` | SHA-256 bergaram dari username, 16 karakter (pseudonim) |
| `jenis_akun` | `publik`, `media`, atau `resmi` (lihat `config.AKUN_MEDIA` / `AKUN_RESMI`) |
| `waktu_wib`, `tanggal` | waktu unggah dalam WIB |
| `fase` | `fase1_pengumuman`, `fase2_seleksi`, atau `fase3_penempatan` |
| `dasar_relevansi` | `eksplisit` (menyebut nama program) atau `konteks` (lihat Tahapan preprocessing no. 4) |
| `n_reply`, `n_repost`, `n_like` | metrik keterlibatan |
| `teks_model` | pembersihan ringan — **input IndoBERT dan embedding BERTopic** |
| `teks_token` | pembersihan berat — **input analisis frekuensi/n-gram dan CountVectorizer BERTopic** |

Perbedaan dua versi teks:

| Langkah | `teks_model` | `teks_token` |
|---|---|---|
| Hapus URL, ubah @mention menjadi `@user`, huruf kecil | ✓ | ✓ |
| Kurangi huruf berulang (`bangettt` → `banget`) | ✓ | ✓ |
| Normalisasi kata tidak baku (`gak` → `tidak`) | ✓ | ✓ |
| Hapus emoji, angka, tanda baca | | ✓ |
| Hapus *stopword* (kata negasi tetap dipertahankan) | | ✓ |

Model transformer membaca konteks kalimat, sehingga *stopword* dan tanda baca dipertahankan
pada `teks_model`. Kata negasi (*tidak, bukan, jangan, belum, tanpa*) tidak pernah dibuang karena
menentukan arah pro/kontra.

### `data/processed/log_preprocessing.csv`
Jumlah baris sebelum dan sesudah setiap tahap pembersihan beserta alasannya.

### `data/processed/sampel_cek_relevansi_konteks.csv`
30 sampel acak post yang lolos lewat jalur konteks. Isi kolom `relevan_manual` dengan 1 atau 0,
lalu hitung presisinya (jumlah 1 ÷ 30) untuk dilaporkan di C5.

### `data/processed/ringkasan_per_fase.csv`, `volume_harian.csv`
Jumlah post per platform × fase × jenis akun, dan jumlah post per hari per platform.

## Tahapan preprocessing

1. Gabung semua file mentah X dan Threads, beri kolom `platform`
2. Deduplikasi berdasarkan ID post per platform (satu post bisa terjaring beberapa kata kunci)
3. Buang post tanpa teks
4. Saring relevansi dua jalur (`relevansi.py`):
   - **eksplisit**: teks menyebut nama program (`config.POLA_RELEVAN`);
   - **konteks**: teks tidak menyebut nama program, tetapi post terjaring kata kunci jangkar
     (`config.KUERI_JANGKAR_KONTEKS`: maganghub, magang hub, magang kemnaker) DAN memuat istilah
     khas program (`config.POLA_KONTEKS`: *batch* + angka, uang saku, mentor, absen, pencairan,
     pemagang, dsb.). Jalur ini dibuat karena Threads menampilkan post bertopik MagangHub yang
     teksnya tidak menyebut nama program. Jalur ini tidak berlaku untuk kata kunci generik
     (`magang nasional`, `pemagangan nasional`).
5. Buang duplikat-dekat: teks identik setelah dinormalisasi (salin-tempel), disimpan yang paling awal.
   Berlaku lintas platform, sehingga post yang disalin dari X ke Threads hanya dihitung sekali
6. Buang spam: pola promosi/joki (`config.POLA_SPAM`), lebih dari 5 tagar, atau kurang dari 4 kata bermakna
7. Buang akun otomatis (`config.AKUN_DIBUANG`, misalnya `meta.ai`), lalu tandai jenis akun
   (resmi/media/publik) — akun resmi dan media tidak dibuang
8. Pseudonimisasi username, hapus URL, ganti @mention
9. Konversi waktu ke WIB, tetapkan fase, buang post di luar jendela penelitian

## Etika dan keamanan

- **Ketentuan layanan X.** Sejak 29 September 2023, ketentuan layanan X melarang *crawling* atau
  *scraping* tanpa persetujuan tertulis, dan pencarian hanya dapat diakses pengguna yang login.
  Penggunaan pipeline ini untuk tugas mata kuliah harus dikonfirmasi kepada pengampu, dan
  pertimbangannya dibahas pada bagian C6 laporan.
- **Ketentuan layanan Threads.** Pencarian Threads juga hanya tersedia bagi pengguna yang login.
  Ketentuan layanan Threads/Meta terkait pengumpulan data otomatis perlu diperiksa dan dibahas pada
  bagian C6. Akun Threads terhubung ke akun Instagram, sehingga pembatasan akibat aktivitas otomatis
  dapat berdampak pada akun Instagram.
- **Jika platform menolak login dari browser otomatis, pengumpulan dihentikan.** Pipeline ini tidak
  menyertakan cara untuk menembus pembatasan login atau menyamarkan otomatisasi.
- **Kesopanan crawling.** Jeda acak 5–9 detik antar-*scroll* dan 25–50 detik antar-kueri; skrip
  berhenti otomatis ketika X menampilkan pesan error atau batas akses, atau ketika Threads
  membalas dengan status 429.
- **Rahasia lokal.** `sesi_x.json` dan `sesi_threads.json` (cookie login) serta `.salt` (garam
  hashing) tidak boleh di-commit atau dibagikan; semuanya tercantum di `.gitignore`.
- **Data tidak dipublikasikan.** Folder `data/raw` dan `data/processed` tidak di-commit. Pseudonimisasi
  tidak sama dengan anonimisasi: teks post publik tetap dapat dicari di X maupun Threads. Kutipan di laporan
  sebaiknya diparafrasekan dan tidak menyertakan identitas pengguna.

## Pemecahan masalah

| Gejala | Penyebab dan solusi |
|---|---|
| `0 post baru (timeout)` padahal post terlihat di browser | Selector DOM X berubah. Buka DevTools (F12), *inspect* sebuah post, sesuaikan `JS_EKSTRAK` di `02_scrape_x.py`. |
| `sesi_kedaluwarsa` | Cookie habis. Jalankan ulang `01_simpan_sesi.py` (X) atau `01_simpan_sesi_threads.py` (Threads). |
| `dibatasi_429` (Threads) | Threads membatasi permintaan. Tunggu minimal beberapa jam, lalu jalankan ulang; skrip melanjutkan dari kata kunci terakhir. |
| `error_x` | X membatasi akses. Tunggu 15–30 menit, jalankan ulang; skrip melanjutkan dari kombinasi terakhir. |
| Hasil sangat sedikit pada satu subjendela | Normal untuk periode sepi. Cek `log_scraping.csv`; perkecil `PANJANG_SUBJENDELA_HARI` jika banyak subjendela mencapai `batas_maks`. |
| Threads: `0 post baru` padahal post terlihat di browser | URL pencarian berbeda dari `config.URL_PENCARIAN_THREADS`, atau Threads mengubah struktur JSON-nya. Salin URL tab *Terbaru* dari pencarian manual; jika masih kosong, periksa respons di DevTools (F12 → Network → Fetch/XHR) dan sesuaikan fungsi `tampak_post`. |
| Login ditolak ("membatasi proses masuk", dsb.) | Platform menolak login dari browser otomatis. Hentikan; jangan diulang berkali-kali. |

## Keterbatasan

- Pencarian X tidak menjamin semua post yang cocok dikembalikan; korpus bukan sensus percakapan.
- Post yang dihapus atau dari akun terkunci tidak terjaring.
- Metrik keterlibatan adalah nilai saat *scraping*, bukan nilai akhir.
- Post panjang yang terpotong di hasil pencarian ("Tampilkan lebih banyak") hanya terambil sebagian.
- Heuristik spam berbasis aturan dapat meloloskan akun bot yang menulis seperti manusia.
- Pencarian Threads tidak mendukung frasa persis maupun filter bahasa dan tanggal, sehingga lebih
  banyak post tidak relevan yang terjaring dan harus disaring di tahap *preprocessing*.
- Jumlah balasan, repost, dan suka di Threads bergantung pada field yang tersedia di respons JSON;
  nilainya bisa kosong jika field tersebut tidak dikirim.

---

## Temuan pengumpulan data

Bagian ini adalah bahan laporan bagian C. Semua angka berasal dari satu *snapshot*
*preprocessing*, `data/processed/preprocess_20261026_3067bfd95e/`, yang dibuat
26 Oktober 2026 pukul 23.05 WIB oleh `preprocess_tk2.py run`. *Snapshot* membekukan data mentah
lebih dulu dan mencatat `sha256` setiap berkas di `snapshot_manifest.json`, sehingga angka di
bawah dapat diverifikasi ulang tanpa menjalankan kembali pengumpulan data. Rincian lengkap ada
di `LAPORAN_KUALITAS.md` di folder yang sama, dan `cek_angka_readme.py` membandingkan angka di
bawah dengan keluaran *snapshot*.

Angka di bawah sudah memuat putaran pertama peninjauan manusia: 312 baris keputusan atas 252
unggahan unik, dari satu peninjau. Keputusan peninjau mengalahkan aturan otomatis, sehingga
angka *model-ready* di sini lebih kecil daripada hasil aturan murni (X 4.286, Threads 3.183).
Keputusannya tersimpan *append-only* di `data/annotations/review_decisions_log.csv`, di luar
folder *snapshot*, sehingga menjalankan ulang *preprocessing* tidak menghapusnya.

Jangan mengutip angka dari sumber lain. Folder `preprocess_20261026_d11a2b74c6/` adalah
*snapshot* sebelumnya dengan aturan promosi versi lama, sedangkan `maganghub_bersih.csv`,
`ringkasan_per_fase.csv`, dan `log_preprocessing.csv` adalah keluaran `03_preprocess.py` yang
jauh lebih lama dan hanya memuat korpus X. Ketiganya angkanya berbeda.

Sesuai prinsip privasi di C6, nama akun pribadi tidak dicantumkan dan contoh unggahan
diparafrasekan.

**Angka inti kedua korpus:**

| Korpus | Mentah | Karantina | Unik | *Model-ready* | Menunggu peninjau | Dikeluarkan |
|---|---:|---:|---:|---:|---:|---:|
| X | 5.257 | 0 | 5.257 | **4.263** | 20 | 974 |
| Threads | 6.028 | 0 | 6.028 | **3.190** | 0 | 2.838 |
| **Gabungan** | **11.285** | **0** | **11.285** | **7.453** | **20** | **3.812** |

Rekonsiliasi kedua korpus berstatus OK: setiap unggahan unik mendapat tepat satu
`status_final`, dan `keep + pending + exclude` sama dengan jumlah unggahan unik.

---

## Temuan pengumpulan data X

Korpus utama. Dijalankan di laptop anggota tim yang memegang sesi akun X.

### C1. Kebutuhan data

| Aspek | Spesifikasi |
|---|---|
| Platform | X (korpus utama) |
| Sasaran konten | Unggahan publik berbahasa Indonesia tentang Program Magang Nasional/MagangHub |
| Kata kunci | `maganghub`, `"magang hub"`, `"magang nasional"`, `"magang kemnaker"`, `"pemagangan nasional"`, digabung dengan `OR` menjadi satu kueri |
| Filter bahasa | `lang:in` (bukan `lang:id`; lihat C5) |
| Periode | 1 Juli sampai 25 Oktober 2026, dibagi tiga fase: pengumuman (1 Juli sampai 31 Agustus), seleksi (1 sampai 20 September), penempatan (21 September sampai 25 Oktober) |
| Granularitas kueri | Satu kueri per hari kalender, 117 hari |
| Lingkup geografis | Tidak dibatasi eksplisit; dibatasi tidak langsung oleh filter bahasa dan topik program nasional |
| Atribut konten | Teks unggahan, waktu unggah, bahasa, jenis unggahan (asli, balasan, kutipan), jumlah balasan, *repost*, suka, kutipan |
| Metadata | ID unggahan, ID percakapan, kata kunci penjaring, rentang tanggal *job*, kolektor, versi adapter, waktu pengambilan, penanda teks terpotong |
| Volume terkumpul | 5.257 unggahan mentah unik, 4.263 *model-ready* |
| Kriteria inklusi | Teks memuat bukti nama program, dan waktu unggah berada di dalam periode penelitian |
| Kriteria eksklusi | Tidak ada bukti nama program di teks, penawaran jasa komersial dengan bukti jelas, pengumuman lowongan mitra, akun otomatis (`meta.ai`), unggahan di luar periode |
| Ditahan untuk peninjau | Relevansi yang hanya bersandar konteks, dan indikasi promosi yang belum pasti |

Kebutuhan data per pertanyaan penelitian:

| Pertanyaan penelitian | Kebutuhan data | Atribut utama | Alasan |
|---|---|---|---|
| RQ1: topik yang membentuk dukungan dan keberatan | Teks unggahan publik | `text_embedding`, `text_topic_repr` | Masukan *sentence embedding* dan c-TF-IDF BERTopic |
| RQ2: polaritas penilaian per topik | Teks unggahan yang sama | `text_sentiment` | Masukan IndoBERT; negasi, emoji, dan kapitalisasi dipertahankan |
| RQ3: pergeseran antarfase | Waktu unggah | `waktu_wib`, `tanggal_wib`, `fase` | Mengelompokkan unggahan ke tiga fase penyelenggaraan |
| Pemisahan opini publik dari narasi resmi | Jenis akun | `jenis_akun_otomatis`, `jenis_akun_manual` | Unggahan media dan akun resmi bukan opini publik |
| Resonansi argumen (pelengkap) | Metrik keterlibatan | `n_reply`, `n_repost`, `n_like`, `n_quote` | Menandai unggahan yang paling banyak ditanggapi |
| Kontrol kualitas | Status dan alasan keputusan | `status_final`, `alasan_utama`, `relevansi_jalur` | Memungkinkan analisis ulang tanpa jalur relevansi tertentu |

### C2. Pipeline pengumpulan data

```
                        config.py
                  parameter kueri, jendela
                  waktu, bahasa, daftar akun
                             |
        +--------------------+--------------------+
        v                                         v
twscrape_pipeline.py setup              connected_browser_collector.mjs
sesi akun lokal di                      Playwright, baca DOM hasil
.twscrape/accounts.db                   pencarian (129 unggahan)
(tidak di-commit)                                 |
        |                                         |
        v                                         |
twscrape_pipeline.py collect                      |
twscrape 0.20.1, satu kueri OR per hari,          |
checkpoint per hari, dapat dilanjutkan            |
        |                                         |
        +--------------------+--------------------+
                             v
                  data/raw/x_<fase>.jsonl
                             |
                             v
                preprocess_tk2.py snapshot
                bekukan raw, catat sha256 per berkas
                -> data/interim/snapshots/<id>/
                             |
                             v
                   preprocess_tk2.py run
     validasi record -> dedup (platform, post_id) -> fase dari
     waktu WIB -> relevansi v2 -> promosi v3 -> label akun ->
     lima versi teks -> grup duplikat -> keputusan akhir
                -> data/processed/preprocess_<id>/
                             |
                             v
                   alat_review/review.html
            peninjau manusia melabeli di browser,
            lalu ekspor CSV
                             |
                             v
            preprocess_tk2.py import-review
            keputusan masuk data/annotations/ (append-only),
            lalu jalankan run sekali lagi
                             |
       +---------------------+---------------------+
       v                     v                     v
preprocess_tk2.py     alat_review/          alat_review/
audit                 presisi_aturan.py     kappa_kalibrasi.py
cek rekonsiliasi      presisi aturan        kesepakatan dua
dan integritas        berbobot strata       peninjau (kappa)
```

Teknologi: Python 3.12 sampai 3.13; [twscrape](https://github.com/vladkens/twscrape) 0.20.1
sebagai mesin pengambil data lewat *endpoint* internal X dengan sesi akun, bukan API resmi
berbayar; Playwright (Chromium) untuk kolektor DOM pelengkap; pandas dan NumPy untuk pengolahan
tabel; scikit-learn untuk TF-IDF `char_wb` 3-5 pada deteksi duplikat-dekat dan untuk Cohen's
kappa; HTML dan JavaScript tanpa kerangka kerja untuk alat pelabelan luring; SHA-256 bergaram
untuk pseudonimisasi *username*; SHA-256 tanpa garam untuk sidik jari berkas *snapshot*. Versi
persis setiap paket dan sidik jari setiap berkas kode tercatat di `snapshot_manifest.json`.

### C3. Metode pengumpulan data

Repositori publik: <https://github.com/flihid/maganghub-pipeline>

| Aspek | Implementasi |
|---|---|
| Pendekatan | Pencarian internal X lewat `twscrape` 0.20.1 (5.128 unggahan), dilengkapi pembacaan DOM halaman pencarian memakai Playwright (129 unggahan) |
| Otentikasi | Sesi akun X disimpan lokal di `.twscrape/accounts.db`. Berkas ini tidak dibagikan dan tidak masuk repositori. Telemetri paket dimatikan lewat `TWS_TELEMETRY=0`; paket tidak diizinkan mengambil *cookie* dari *browser* maupun memakai *proxy* |
| Kueri | Satu kueri gabungan `(maganghub OR "magang hub" OR "magang nasional" OR "magang kemnaker" OR "pemagangan nasional")` dengan `lang:in`, bukan lima pencarian terpisah |
| Granularitas | Satu *job* per hari kalender. Rentang pendek membuat X mengembalikan lebih banyak hasil daripada satu rentang panjang. Parameter `until` di pencarian X bersifat eksklusif |
| Penjadwalan | Hari yang belum pernah dicoba diprioritaskan, lalu hari lain disebar dengan pemilihan titik tengah secara *breadth-first*, sehingga awal, tengah, dan akhir setiap fase terjangkau lebih dahulu |
| *Pagination* | Kursor halaman dari SDK, dengan jeda minimum 5 detik antar-halaman dan 25 detik antar-kueri |
| Kondisi berhenti | (1) `stream_ended_unverified`, aliran hasil habis tanpa bukti kelengkapan; (2) `daily_limit_partial`, kuota harian tercapai; (3) `eligible_day_limit_partial`, batas unggahan layak per hari tercapai; (4) `page_budget_partial`, anggaran halaman habis; (5) `quota_partial`, batas data mentah total tercapai |
| Deteksi duplikat | Per ID unggahan saat pengumpulan; `(platform, post_id)` dan duplikat-dekat saat *preprocessing* |
| Penanganan kegagalan | Status setiap *job* dicatat di `data/raw/browser_collection_log.jsonl`. Keadaan pengumpulan disimpan di `twscrape_state_*.json`, sehingga pengumpulan dapat dilanjutkan tanpa mengulang hari yang sudah selesai |
| Format luaran | JSON Lines, satu unggahan per baris, satu berkas per fase |
| Penyimpanan | Data mentah dan keluaran olahan dimasukkan ke repositori publik atas keputusan tim (lihat C6) |

Contoh struktur satu *record* mentah, nilainya diganti contoh:

```json
{"tweet_id": "19xxxxxxxxxxxxxxxx", "username": "<username>",
 "url": "https://x.com/<username>/status/19xxxxxxxxxxxxxxxx",
 "text": "<isi unggahan>", "created_at": "2026-08-14T04:21:08+00:00",
 "post_lang": "in", "n_reply": 4, "n_repost": 1, "n_like": 23, "n_quote": 0,
 "conversation_id": "19xxxxxxxxxxxxxxxx", "content_type": "original",
 "fase": "fase1_pengumuman", "kueri": "(maganghub OR \"magang hub\" OR ...)",
 "language_filter": "in", "since": "2026-08-14", "until": "2026-08-15",
 "scraped_at": "2026-10-26T02:31:44+07:00", "text_truncated": "unknown",
 "collector": "twscrape_0.20.1"}
```

### C4. Implementasi pipeline

Cakupan pengumpulan (`cakupan_harian_x.csv`):

| Aspek | Nilai |
|---|---|
| Hari dalam periode penelitian | 117 |
| Hari yang dicoba | 117 (100%) |
| Total percobaan | 361, minimum 2 percobaan per hari |
| Hari tanpa satu pun unggahan | 0 |
| Unggahan unik per hari | minimum 4, median 27, maksimum 308 |
| Status percobaan terakhir | 114 hari `stream_ended_unverified`, 3 hari `daily_limit_partial` |
| Hari yang pernah kena batas | 50 dari 117 |
| Hari yang pernah bergalat | 3 dari 117 |

Tidak ada status yang berarti lengkap. `stream_ended_unverified` hanya berarti aliran hasil
berhenti mengirim unggahan baru, bukan sensus percakapan di X.

Jumlah *record* per berkas (`hitung_per_file.csv`):

| Berkas | *Record* | Valid | Karantina |
|---|---:|---:|---:|
| `x_fase1_pengumuman.jsonl` | 2.473 | 2.473 | 0 |
| `x_fase2_seleksi.jsonl` | 936 | 936 | 0 |
| `x_fase3_penempatan.jsonl` | 1.848 | 1.848 | 0 |
| **Total** | **5.257** | **5.257** | **0** |

Tahapan *preprocessing* (`tahapan_x.csv`). Setiap unggahan mendapat tepat satu status dan satu
alasan utama, sehingga angka di bawah tidak tumpang tindih:

| No. | Tahap | Jumlah | Keterangan |
|---:|---|---:|---|
| 1 | *Record* mentah dari *snapshot* | 5.257 | 3 berkas |
| 2 | Karantina *record* invalid | 0 | `karantina.csv` kosong |
| 3 | *Record* valid | 5.257 | |
| 4 | Versi ID sama digabung | 0 | `konflik_versi_id.csv` kosong |
| 5 | Unggahan unik | 5.257 | Basis keputusan |
| 6 | Dikeluarkan | 974 | Rincian di bawah |
| 7 | Menunggu peninjau | 20 | Rincian di bawah |
| 8 | *Model-ready* | 4.263 | |

Alasan pengeluaran:

| Alasan utama | Jumlah |
|---|---:|
| Tidak ada bukti nama program di teks | 478 |
| Penawaran eksplisit jasa atau joki | 129 |
| Penawaran layanan dengan kontak, harga, atau testimoni | 115 |
| Paket layanan dengan ajakan kontak | 64 |
| Peninjau menilai iklan | 61 |
| Peninjau menilai tidak relevan | 39 |
| Layanan dengan kontak dan bukti jual | 30 |
| Layanan berharga dengan bukti jual | 27 |
| Pengumuman lowongan mitra | 17 |
| Promosi komersial dengan kode referal | 14 |
| **Total** | **974** |

Alasan penahanan untuk peninjau:

| Alasan utama | Jumlah |
|---|---:|
| Peninjau ragu atas relevansi | 19 |
| Peninjau ragu atas indikasi promosi | 1 |
| **Total** | **20** |

Seluruh 52 unggahan yang sebelumnya ditahan karena aturan otomatis sudah dibaca peninjau.
Yang tersisa adalah 20 unggahan yang peninjau sendiri tidak bisa putuskan, umumnya karena
keputusannya bergantung pada teks kutipan atau unggahan induk yang tidak ikut tersimpan.

Komposisi korpus *model-ready* per fase:

| Fase | Media | Tidak terdaftar | Resmi | Total | % korpus | Per hari |
|---|---:|---:|---:|---:|---:|---:|
| Fase 1: pengumuman (62 hari) | 14 | 2.274 | 57 | 2.345 | 55,0% | 37,8 |
| Fase 2: seleksi (20 hari) | 1 | 893 | 1 | 895 | 21,0% | 44,8 |
| Fase 3: penempatan (35 hari) | 8 | 995 | 20 | 1.023 | 24,0% | 29,2 |
| **Total** | **23** | **4.162** | **78** | **4.263** | | |

Label `tidak_terdaftar` berarti akun tidak ada di daftar akun resmi dan media di `config.py`.
Label itu belum berarti akun publik, dan masih perlu diperiksa peninjau.

Sebaran bulanan korpus *model-ready*: Juli 1.414, Agustus 931, September 1.036, Oktober 882.
Setiap hari dalam ketiga fase memiliki setidaknya satu unggahan *model-ready*.

Pergeseran distribusi fase akibat penyaringan (`pergeseran_fase_x.csv`):

| Fase | Unggahan unik | *Model-ready* | Proporsi unik | Proporsi *model-ready* | Retensi |
|---|---:|---:|---:|---:|---:|
| Fase 1: pengumuman | 2.473 | 2.345 | 47,0% | 55,0% | 94,8% |
| Fase 2: seleksi | 936 | 895 | 17,8% | 21,0% | 95,6% |
| Fase 3: penempatan | 1.848 | 1.023 | 35,2% | 24,0% | 55,4% |

Retensi fase 3 jauh lebih rendah karena penawaran jasa komersial menumpuk di periode
penempatan. Penyaringan menggeser proporsi antarfase, sehingga perbandingan antarfase pada RQ3
harus memakai korpus *model-ready*, bukan data mentah.

Kontribusi per kolektor:

| Kolektor | Dikeluarkan | *Model-ready* | Menunggu peninjau | Total |
|---|---:|---:|---:|---:|
| `twscrape_0.20.1` | 900 | 4.210 | 18 | 5.128 |
| `connected_brave_dom_v2` | 72 | 43 | 2 | 117 |
| `connected_brave_dom_v1` | 2 | 10 | 0 | 12 |

Varian korpus yang tersedia untuk analisis:

| Berkas | Isi | Jumlah |
|---|---|---:|
| `model_ready_x.csv` dan `.jsonl` | Semua unggahan *model-ready* | 4.263 |
| `model_ready_x_satu_per_teks_identik.csv` | Satu wakil per grup teks identik | 4.234 |
| `model_ready_x_tanpa_resmi_media.csv` | Tanpa akun resmi dan media terdaftar | 4.162 |
| `dataset_x_semua_keputusan.csv` | Seluruh 5.257 unggahan beserta status dan alasannya | 5.257 |

### C5. Kualitas data dan keterbatasannya

| Isu | Temuan | Dampak | Mitigasi |
|---|---|---|---|
| Filter bahasa salah di pengambilan awal | `lang:id` mengembalikan nol hasil untuk rentang yang `lang:in` mengembalikan unggahan Indonesia. Uji pembanding tiga tanggal tercatat di `perbandingan_kueri_v3.csv` | Hasil kosong dengan filter lama tidak menandakan tidak ada percakapan | Filter diganti `lang:in`. Hari yang kosong dengan filter lama tidak dihitung selesai dan diambil ulang |
| Tidak ada bukti kelengkapan | Tidak satu pun dari 117 hari berstatus lengkap. 50 hari pernah kena batas, 3 hari pernah bergalat | Volume per tanggal tidak boleh dibaca sebagai volume percakapan sebenarnya | Status percobaan terakhir per hari dilaporkan apa adanya di `cakupan_harian_x.csv` |
| Teks berpotensi terpotong | Status pemotongan tidak diketahui untuk 5.128 dari 5.257 unggahan (97,6%). Terbukti terpotong 9, terbukti utuh 120 | Unggahan panjang bisa hilang sebagian isinya | `unknown` dicatat sebagai tidak diketahui, bukan sebagai bukti utuh. Saat *dedup*, versi `text_truncated=False` diprioritaskan |
| Presisi kueri gabungan | 478 unggahan terjaring tanpa bukti nama program di teksnya, karena kueri `OR` memuat frasa generik | 9,1% data mentah tidak dapat dipastikan membahas program ini | Relevansi dinilai dari bukti di teks, bukan dari kueri. Jalur relevansi disimpan di `relevansi_jalur` |
| Relevansi yang bersandar konteks | 22 unggahan hanya relevan karena kueri jangkar atau konteks. Seluruhnya sudah dibaca peninjau: sebagian dinyatakan relevan dan masuk korpus, sebagian dinyatakan tidak relevan dan dikeluarkan | Keputusannya tidak lagi bersandar pada aturan | Dibaca manusia, bukan diputuskan aturan. Jalur asalnya tetap tersimpan di `relevansi_jalur` |
| Promosi komersial | 396 unggahan dikeluarkan oleh aturan karena penawaran jasa atau pengumuman lowongan mitra, 61 lagi dikeluarkan atas penilaian peninjau, dan 1 masih ditahan karena peninjau ragu | Jasa joki pendaftaran menggelembungkan frekuensi topik dan bukan opini publik | Aturan `promosi_v3` memisahkan penawaran berbukti dari kritik dan diskusi uang saku. Sinyal dan alasan setiap keputusan tercatat di `exclusion_log_x.csv` |
| Konten kampanye terkoordinasi | 32 unggahan *model-ready* (0,8%) memakai tagar kampanye `#magangnasional`, `#jagaindonesia`, `#indonesiamaju`, atau `#magangnasional2026`, dari 19 penulis unik | Unggahan promosi program bukan opini publik, dan dapat menggeser distribusi sentimen ke arah positif | Proporsinya kecil di korpus X. Tagar disimpan di teks, sehingga unggahan ini dapat dikeluarkan saat analisis sentimen |
| Dominasi akun | 2.651 penulis unik untuk 5.257 unggahan. Akun paling aktif menyumbang 125 unggahan; lima akun teratas menyumbang 125, 110, 107, 92, dan 90 unggahan | Opini segelintir akun sangat aktif dapat ikut membentuk gambaran | Dinyatakan sebagai keterbatasan. `user_hash` memungkinkan pembobotan atau analisis per akun |
| Duplikasi dan salin-tempel | 47 grup teks identik mencakup 287 unggahan; grup terbesar berisi 85 unggahan. 44 grup duplikat-dekat mencakup 344 unggahan | Menggelembungkan frekuensi topik | Hanya ditandai, tidak dihapus. Varian satu wakil per teks identik disediakan (4.234 unggahan) |
| Metadata tidak lengkap | `n_quote`, `conversation_id`, dan `content_type` kosong pada 2,45% unggahan; `post_lang` kosong pada 0,23% | Analisis jenis unggahan dan percakapan kehilangan sebagian data | Kekosongan disimpan sebagai `null`, bukan 0, dan dilaporkan di `missingness_x.csv` |
| Bahasa bukan Indonesia lolos filter | Dari 5.257 unggahan, 5.202 terdeteksi `in`, 25 berbahasa Inggris, 18 berbahasa lain atau tidak terdeteksi, dan 12 tanpa nilai | *Noise* kecil pada analisis berbasis kata | `post_lang` disimpan, sehingga penyaringan ulang dapat dilakukan |
| Teks sangat pendek | 95 unggahan kurang dari 4 token | Sedikit informasi untuk pemodelan topik | Hanya ditandai di `teks_pendek`, tidak dibuang |
| Presisi aturan terukur, satu peninjau | 312 baris keputusan masuk, mencakup 252 unggahan unik, 232 di korpus X. Pada sampel berstrata 200 unggahan, status `keep` otomatis disetujui peninjau pada **91,5% ± 5,0** populasi *model-ready* (n=118 baris tegas, 17 baris `ragu`). Aturan relevansi saja 95,0% ± 3,9; aturan promosi saja 89,2% ± 4,9. Status `exclude` disetujui 98,6% ± 1,6, jadi aturan jarang membuang unggahan yang relevan | Presisi korpus sudah terukur, tetapi hanya oleh satu peninjau, sehingga kesepakatan antarpeninjau belum ada. 17 baris `ragu` berarti batas bawah pesimistis presisi `keep` adalah 80,0% | Dihitung dengan `alat_review/presisi_aturan.py` memakai bobot strata dan koreksi populasi terbatas. Baris `ragu` tidak dibuang diam-diam, melainkan dilaporkan sebagai dua batas |
| Kesepakatan antarpeninjau belum ada | 40 baris kalibrasi `kalibrasi_dua_peninjau=1` sudah diisi satu peninjau; peninjau kedua belum | Cohen's kappa tidak dapat dilaporkan, sehingga tidak diketahui apakah definisi "relevan" dipahami sama oleh dua orang | `alat_review/kappa_kalibrasi.py` siap dijalankan begitu peninjau kedua mengisi 40 baris yang sama secara terpisah |
| Konsistensi satu peninjau rendah untuk relevansi | 20 unggahan kebetulan dinilai dua kali oleh peninjau yang sama, di berkas sampel (petunjuk mesin disembunyikan) dan di berkas antrean (petunjuk ditampilkan). Relevansi: setuju 70%, kappa 0,51. Promosi: setuju 85%, kappa 0,71. Seluruh perbedaannya satu arah, yaitu memilih `ragu` ketika petunjuk mesin terlihat | Penilaian relevansi tidak stabil bahkan untuk satu orang, dan tampilan petunjuk mesin ikut memengaruhinya. Ini batas bawah, bukan pengganti kesepakatan antarpeninjau, dan diukur pada 20 unggahan tersulit karena semuanya berasal dari antrean `pending` | Dilaporkan apa adanya. Dihitung ulang dengan `python alat_review/kappa_kalibrasi.py <sampel>.csv <antrean>.csv`. Untuk putaran berikutnya, petunjuk mesin sebaiknya disembunyikan di kedua jenis berkas |
| Garam pseudonimisasi tidak diversikan | `.salt` adalah berkas lokal dan sengaja tidak masuk repositori, sehingga `user_hash` berbeda bila *preprocessing* dijalankan di komputer lain | Nilai `user_hash` hanya dapat dibandingkan di dalam satu kali pengolahan. Jumlah penulis unik tidak terpengaruh, karena pemetaannya tetap satu-ke-satu | Dinyatakan sebagai konsekuensi yang diterima. Analisis per akun harus memakai keluaran dari satu kali pengolahan yang sama |
| Batas fase belum terverifikasi | Batas di `config.JENDELA_WAKTU` mengikuti TK1 §1.6 yang merujuk berita, bukan tanggal resmi yang sudah diverifikasi | Unggahan di dekat batas fase bisa salah kelompok | Dinyatakan sebagai asumsi. `fase_raw` dan `fase_raw_berbeda` disimpan untuk pemeriksaan ulang |
| Keterwakilan populasi | Pengguna X tidak mewakili seluruh lulusan baru Indonesia. Unggahan yang dihapus atau dari akun terkunci tidak terjaring. Metrik keterlibatan adalah nilai saat pengambilan, bukan nilai akhir | Temuan bersifat indikatif atas wacana daring | Tidak digeneralisasi sebagai opini nasional. Waktu pengambilan metrik disimpan di `metrik_scraped_at` |

### C6. Pertimbangan etika

- **Konten publik.** Data yang diambil hanya unggahan yang tampil di hasil pencarian publik X.
  Ketentuan layanan X tentang pengumpulan data otomatis perlu dirujuk langsung dalam laporan.
- **Tidak menembus pembatasan.** Pipeline tidak menyamarkan otomatisasi, tidak mengambil *cookie*
  dari *browser* pengguna, dan tidak mengakali batas permintaan. Ketika platform membatasi akses,
  *job* berhenti dan statusnya dicatat sebagai keterbatasan.
- **Pengambilan yang sopan.** Jeda minimum 5 detik antar-halaman dan 25 detik antar-kueri
  dipaksakan di tingkat validasi argumen, sehingga tidak dapat diturunkan lewat parameter.
- **Minimalisasi data.** Nama tampilan, foto profil, bio, jumlah pengikut, dan media tidak diambil.
- **Pseudonimisasi.** *Username* diganti hash SHA-256 bergaram (`user_hash`) di seluruh keluaran
  olahan. Garam disimpan di `.salt` lokal dan tidak dipublikasikan. Pseudonimisasi tidak sama
  dengan anonimisasi, karena teks unggahan publik tetap dapat dicari, sehingga kutipan di laporan
  diparafrasekan.
- **Penyamaran data sensitif dalam teks.** Pola URL, sebutan akun, surel, nomor telepon, dan NIK
  diganti penanda `[URL]`, `[USER]`, `[EMAIL]`, `[PHONE]`, `[NIK]` di seluruh versi teks. Sebanyak
  33 unggahan X bertanda indikasi data pribadi di teks aslinya.
- **Pelabelan luring.** `alat_review/review.html` berjalan di browser peninjau tanpa server dan
  tanpa internet. Berkas CSV hanya dibaca di komputer sendiri dan tidak dikirim ke layanan luar.
- **Kredensial.** Sesi akun (`.twscrape/accounts.db`, `sesi_x.json`, `sesi_threads.json`) dan garam
  (`.salt`) tercantum di `.gitignore` dan tidak masuk repositori. Berkas keadaan
  `twscrape_state_*.json` hanya memuat jadwal *job*, bukan kredensial.
- **Data mentah di repositori publik.** Atas keputusan tim, `data/raw/` dan `data/processed/`
  dimasukkan ke repositori publik agar pipeline dapat direproduksi penuh oleh pemeriksa. Data
  mentah masih memuat *username* dan teks unggahan asli, jadi pseudonimisasi hanya berlaku pada
  keluaran olahan. Pilihan ini perlu dinyatakan terbuka di laporan sebagai konsekuensi yang
  diterima, bukan sebagai jaminan privasi.
- **Risiko akun pengumpul.** Sesi akun X milik anggota tim dipakai untuk pencarian, sehingga
  pembatasan akibat aktivitas otomatis berisiko berdampak pada akun tersebut.

### C7. Ringkasan

Korpus X terdiri dari 4.263 unggahan *model-ready* dari 5.257 unggahan mentah unik yang
dikumpulkan dengan satu kueri gabungan lima kata kunci berfilter `lang:in`, dijalankan per hari
kalender atas seluruh 117 hari periode penelitian. Mesin utamanya `twscrape` 0.20.1 yang memakai
*endpoint* internal X dengan sesi akun, dilengkapi pembacaan DOM Playwright untuk 129 unggahan.
Penyaringan memakai aturan relevansi berbasis bukti teks dan aturan promosi `promosi_v3`, dan
setiap keputusan dapat dilacak ke alasannya. Korpus ini menutup kekurangan terbesar korpus
Threads: fase 1 terisi 2.345 unggahan, atau 37,8 unggahan per hari selama 62 hari, dan setiap
hari dalam periode penelitian terwakili. Peninjauan manusia atas sampel berstrata 200 unggahan
menunjukkan presisi status `keep` sebesar 91,5% ± 5,0 pada populasi *model-ready*, dengan batas
bawah pesimistis 80,0% bila seluruh baris `ragu` dianggap salah. Keterbatasan utamanya adalah
tidak adanya bukti kelengkapan pencarian pada satu hari pun, status pemotongan teks yang tidak
diketahui untuk 97,6% unggahan, dan kesepakatan antarpeninjau yang belum dapat dihitung karena
baru satu peninjau mengisi baris kalibrasi.

---

## Temuan pengumpulan data Threads

Korpus pelengkap, dengan satu pembatasan penting yang dibuat tim pada 26 Oktober 2026.

Pencarian Threads terlalu longgar: 2.615 dari 6.028 unggahan terjaring tanpa menyebut nama
program di teksnya, dan pemeriksaan sampel menunjukkan sekitar separuh di antaranya membahas
magang umum, bukan program ini. Karena itu jalur relevansi konteks **tidak dipakai untuk
Threads**. Unggahan tanpa bukti nama program langsung dikeluarkan dengan alasan
`relevansi_konteks_tidak_dipakai`, bukan ditahan untuk peninjau. Keputusan ini tercatat di
`config.RELEVANSI_KONTEKS_DIABAIKAN` dan membuang 1.089 unggahan yang pada *snapshot* sebelumnya
berstatus `pending`. Keputusan peninjau manusia tetap mengalahkan aturan ini bila ada.

Akibatnya korpus Threads lebih kecil tetapi lebih bersih, dan antrean peninjau Threads turun
dari 1.109 menjadi 20.

### C1. Kebutuhan data

| Aspek | Spesifikasi |
|---|---|
| Platform | Threads (korpus pelengkap) |
| Sasaran konten | Unggahan publik berbahasa Indonesia tentang Program Magang Nasional/MagangHub |
| Kata kunci | `maganghub`, `magang hub`, `magang nasional`, `magang kemnaker`, `pemagangan nasional`, dicari satu per satu |
| Filter bahasa | Tidak tersedia di pencarian Threads |
| Periode | Sama dengan X: 1 Juli sampai 25 Oktober 2026, tiga fase |
| Lingkup geografis | Tidak dibatasi eksplisit; dibatasi tidak langsung oleh topik program nasional |
| Atribut konten | Teks unggahan, waktu unggah, jumlah balasan, *repost*, suka |
| Metadata | ID unggahan, kata kunci penjaring, waktu pengambilan |
| Volume terkumpul | 6.028 unggahan mentah unik, 3.190 *model-ready* |
| Kriteria inklusi | Teks menyebut nama program, dan waktu unggah berada di dalam periode penelitian. Lebih ketat daripada X karena jalur konteks tidak dipakai |
| Kriteria eksklusi | Tidak ada bukti nama program di teks, unggahan di luar periode, akun otomatis, penawaran jasa komersial, pengumuman lowongan mitra, promosi acara pelatihan |

Kebutuhan data per pertanyaan penelitian sama dengan korpus X, kecuali `n_quote` dan
`content_type` yang tidak tersedia di Threads.

### C2. Pipeline pengumpulan data

```
config.py --> 01_simpan_sesi_threads.py --> 02_scrape_threads.py --> preprocess_tk2.py
 parameter     login manual (Instagram),     Playwright: cari,        snapshot -> run ->
               simpan cookie sesi            scroll, baca JSON        import-review -> audit
                                             -> data/raw/*.jsonl      (sama dengan korpus X)
```

Teknologi: Python 3, Playwright (Chromium) untuk halaman dinamis, lalu *preprocessing* yang sama
dengan korpus X. Keluaran Threads berada di subfolder `threads/` di dalam folder *snapshot*.

### C3. Metode pengumpulan data

Repositori publik: <https://github.com/flihid/maganghub-pipeline>

| Aspek | Implementasi |
|---|---|
| Pendekatan | *Web scraping* dengan Playwright. API resmi Threads punya pencarian kata kunci, tetapi tanpa izin `threads_keyword_search` melalui *App Review* Meta, pencarian hanya mencakup unggahan milik akun sendiri |
| Otentikasi | Login manual sekali dengan akun Instagram; *cookie* sesi disimpan di `sesi_threads.json`. Keabsahan sesi diverifikasi dengan membuka halaman pencarian, karena login Instagram terjadi di tab baru |
| Kueri | `https://www.threads.com/search?q=<kata kunci>&serp_type=default&filter=recent` (tab *Terbaru*) |
| Ekstraksi | Tidak memakai *selector* HTML, karena Threads memakai nama *class* yang diacak. Data diambil dari JSON yang tertanam di halaman (`<script type="application/json" data-sjs>`) dan dari respons jaringan yang dimuat saat halaman di-*scroll*. Objek unggahan dikenali dari kombinasi *field* `code`, `taken_at`, `caption.text`, dan `user.username` |
| *Pagination* | *Infinite scroll*. Pencarian Threads tidak punya filter tanggal, sehingga hasil diurutkan dari yang terbaru |
| Kondisi berhenti | (1) Batas unggahan per kata kunci tercapai; (2) 6 kali *scroll* tanpa unggahan baru terlihat; (3) 3 putaran berturut-turut hanya berisi unggahan sebelum 1 Juli 2026; (4) status HTTP 429 |
| *Rate limiting* | Jeda acak 5 sampai 9 detik antar-*scroll* (awalnya 2,5 sampai 5 detik, diperlambat setelah menerima status 429) dan 25 sampai 50 detik antar-kata kunci |
| Deteksi duplikat | Per ID unggahan saat pengumpulan; `(platform, post_id)` dan duplikat-dekat saat *preprocessing* |
| Penanganan kegagalan | Status setiap kata kunci dicatat di `data/raw/log_scraping_threads.csv`. Skrip berhenti otomatis ketika sesi kedaluwarsa atau menerima 429, menyimpan progres, dan dapat dilanjutkan tanpa mengulang kata kunci yang selesai |
| Format luaran | JSON Lines (`data/raw/threads_<kata-kunci>.jsonl`), satu unggahan per baris |
| Penyimpanan | Sama dengan korpus X (lihat C6) |

Contoh struktur satu *record* mentah, nilainya diganti contoh:

```json
{"tweet_id": "th_1234567890", "platform": "threads",
 "url": "https://www.threads.com/@<username>/post/<kode>",
 "username": "<username>", "created_at": "2026-10-20T05:00:00+00:00",
 "text": "<isi unggahan>", "n_reply": 3, "n_repost": 0, "n_like": 12,
 "kueri": "maganghub", "scraped_at": "2026-10-25T07:12:03+00:00"}
```

### C4. Implementasi pipeline

Pengumpulan berjalan dalam 11 putaran antara 25 dan 26 Oktober 2026
(`threads/cakupan_threads_log.csv`). Lima putaran berhenti karena hasil pencarian habis, empat
putaran karena batas maksimum tercapai, dan dua putaran karena status HTTP 429. Putaran terakhir
pada kata kunci `magang kemnaker` menambahkan 1.882 unggahan sebelum dibatasi 429.

Jumlah *record* per berkas (`hitung_per_file.csv`):

| Berkas | *Record* | Valid | Karantina |
|---|---:|---:|---:|
| `threads_magang-kemnaker.jsonl` | 2.684 | 2.684 | 0 |
| `threads_maganghub.jsonl` | 1.416 | 1.416 | 0 |
| `threads_magang-hub.jsonl` | 899 | 899 | 0 |
| `threads_pemagangan-nasional.jsonl` | 767 | 767 | 0 |
| `threads_magang-nasional.jsonl` | 262 | 262 | 0 |
| **Total** | **6.028** | **6.028** | **0** |

Tahapan *preprocessing* (`threads/tahapan_threads.csv`):

| No. | Tahap | Jumlah | Keterangan |
|---:|---|---:|---|
| 1 | *Record* mentah dari *snapshot* | 6.028 | 5 berkas |
| 2 | Karantina *record* invalid | 0 | |
| 3 | *Record* valid | 6.028 | |
| 4 | Versi ID sama digabung | 0 | |
| 5 | Unggahan unik | 6.028 | Basis keputusan |
| 6 | Dikeluarkan | 2.838 | Rincian di bawah |
| 7 | Menunggu peninjau | 0 | Seluruhnya sudah diputuskan peninjau |
| 8 | *Model-ready* | 3.190 | |

Alasan pengeluaran:

| Alasan utama | Jumlah |
|---|---:|
| Tidak ada bukti nama program di teks | 1.421 |
| Relevansi konteks tidak dipakai untuk Threads | 1.089 |
| Di luar periode penelitian | 139 |
| Pengumuman lowongan mitra | 124 |
| Akun otomatis (`meta.ai`) | 36 |
| Penawaran eksplisit jasa atau joki | 5 |
| Promosi acara pelatihan | 4 |
| Penawaran layanan dengan kontak, harga, atau testimoni | 3 |
| Paket layanan dengan ajakan kontak | 2 |
| Promosi komersial dengan kode referal | 2 |
| Peninjau menilai iklan | 13 |
| **Total** | **2.838** |

Tidak ada unggahan yang masih menunggu peninjau. Seluruh 20 unggahan yang sebelumnya ditahan
aturan promosi sudah dibaca: 7 dinyatakan bukan iklan dan masuk korpus, 13 dinyatakan iklan dan
dikeluarkan.

Komposisi korpus *model-ready* per fase:

| Fase | Media | Tidak terdaftar | Resmi | Total | % korpus | Per hari |
|---|---:|---:|---:|---:|---:|---:|
| Fase 1: pengumuman (62 hari) | 10 | 695 | 24 | 729 | 22,9% | 11,8 |
| Fase 2: seleksi (20 hari) | 26 | 600 | 17 | 643 | 20,2% | 32,2 |
| Fase 3: penempatan (35 hari) | 79 | 1.697 | 42 | 1.818 | 57,0% | 51,9 |
| **Total** | **115** | **2.992** | **83** | **3.190** | | |

Sebaran bulanan korpus *model-ready*: Juli 366, Agustus 363, September 1.107, Oktober 1.354.
Angka ini membatalkan temuan putaran pertama bahwa kedalaman pencarian Threads tidak menjangkau
sebelum September. Kepadatannya tetap paling rendah di fase 1, 11,8 unggahan per hari berbanding
51,9 di fase 3, dan sebarannya belum merata: hanya 47 dari 62 hari fase 1 memiliki setidaknya
satu unggahan *model-ready*, sedangkan fase 2 dan fase 3 terisi penuh.

Pergeseran distribusi fase akibat penyaringan (`threads/pergeseran_fase_threads.csv`):

| Fase | Unggahan unik | *Model-ready* | Proporsi unik | Proporsi *model-ready* | Retensi |
|---|---:|---:|---:|---:|---:|
| Fase 1: pengumuman | 1.173 | 729 | 19,9% | 22,9% | 62,1% |
| Fase 2: seleksi | 1.056 | 643 | 17,9% | 20,2% | 60,9% |
| Fase 3: penempatan | 3.660 | 1.818 | 62,2% | 57,0% | 49,7% |

Varian korpus: `model_ready_threads.csv` 3.190 unggahan, `..._satu_per_teks_identik.csv` 3.090,
`..._tanpa_resmi_media.csv` 2.992, dan `dataset_threads_semua_keputusan.csv` seluruh 6.028
unggahan beserta status dan alasannya.

Akun resmi yang teridentifikasi: `kemnaker`, `maganghub.kemnaker`. Akun media dan informasi
karier: `viralyn.daily`, `mcinews.id`, `titik_temu.news`, `satu_meja.id`, `temankarirofficial`,
`internship.career`.

### C5. Kualitas data dan keterbatasannya

| Isu | Temuan | Dampak | Mitigasi |
|---|---|---|---|
| Presisi kata kunci rendah | 2.615 dari 6.028 unggahan terjaring tanpa menyebut nama program di teksnya, 43,4% data mentah. Pencarian Threads tidak mendukung frasa persis | Hampir separuh data mentah tidak dapat dipastikan membahas program ini | Jalur relevansi konteks tidak dipakai untuk Threads. Korpus dibatasi pada unggahan yang menyebut nama program |
| Konsekuensi pembatasan itu | 1.089 unggahan dikeluarkan dengan alasan `relevansi_konteks_tidak_dipakai`. Pemeriksaan kata kunci otomatis atas seluruh 1.089: 827 (75,9%) tetap menyebut "magang" atau "pemagangan", 325 (29,8%) menyebut "kemnaker", dan 262 (24,1%) tidak menyebut magang sama sekali. Sebarannya fase 1 271, fase 2 250, fase 3 568 | 325 unggahan yang menyebut Kemnaker adalah kerugian *recall* yang paling mungkin nyata: pola `kemnaker` termasuk istilah konteks, bukan nama program, sehingga keluhan seperti "kemnaker belum cairkan uang saku" ikut terbuang. Sebaliknya 262 unggahan tanpa kata magang memang pantas keluar | Keputusan dan alasannya tercatat di `config.py` dan `threads/exclusion_log_threads.csv`, sehingga analisis ulang tanpa pembatasan ini masih mungkin. Pemeriksaan di atas bersifat otomatis dan berbasis kata kunci, bukan pembacaan manusia, dan harus disebut demikian di laporan |
| Perlakuan berbeda antarplatform | Korpus X memakai jalur konteks, korpus Threads tidak | Kriteria inklusi kedua korpus tidak identik, sehingga penggabungan perlu dinyatakan sebagai korpus dengan dua aturan | Kolom `relevansi_jalur` memungkinkan penyeragaman dengan membuang jalur konteks di korpus X juga |
| Tidak ada filter tanggal | 139 unggahan terjaring di luar periode penelitian, paling tua 16 Desember 2025 | Pencarian tidak dapat diarahkan ke fase tertentu | Penyaringan tanggal dilakukan saat *preprocessing* dengan interval `[awal 00.00 WIB, akhir 00.00 WIB)` |
| Metadata minim | `post_lang`, `content_type`, `n_quote`, dan `text_truncated` kosong untuk seluruh 6.028 unggahan | Penyaringan bahasa, analisis jenis unggahan, dan verifikasi keutuhan teks tidak mungkin dilakukan di korpus ini | Dilaporkan di `threads/missingness_threads.csv`. Analisis yang memerlukan atribut ini dibatasi pada korpus X |
| Kepadatan fase 1 rendah | 11,8 unggahan per hari di fase 1 berbanding 51,9 di fase 3, dan hanya 47 dari 62 hari fase 1 terisi | Tidak dapat dipisahkan apakah ini peningkatan diskusi yang nyata atau efek urutan hasil pencarian yang mengutamakan unggahan terbaru | Dinyatakan sebagai keterbatasan. Perbandingan RQ3 memakai proporsi dan menyertakan korpus X yang kepadatannya merata |
| Dominasi akun | 3.881 penulis unik untuk 6.028 unggahan. Akun paling aktif menyumbang 79 unggahan | Opini akun sangat aktif dapat ikut membentuk gambaran | Dinyatakan sebagai keterbatasan. `user_hash` memungkinkan analisis per akun |
| Konten kampanye terkoordinasi | 218 unggahan *model-ready* (6,8%) memakai tagar kampanye, terbanyak `#magangnasional` 153, `#indonesiakita` 59, dan `#jagaindonesia` 51. Berasal dari 143 penulis unik, dengan 38 unggahan berteks identik dalam 9 grup | Teks promosi yang sama diunggah banyak akun berbeda. Ini bukan opini publik dan menggeser distribusi sentimen ke arah positif, tepat pada variabel yang diukur penelitian ini | Belum disaring. Proporsinya delapan kali lebih besar daripada korpus X, sehingga analisis sentimen Threads sebaiknya dilaporkan dengan dan tanpa 218 unggahan ini |
| Duplikasi | 88 grup teks identik mencakup 252 unggahan; 42 grup duplikat-dekat mencakup 138 unggahan | Menggelembungkan frekuensi topik | Hanya ditandai. Varian satu wakil per teks identik disediakan (3.090 unggahan) |
| Pembatasan platform | Status 429 diterima pada dua putaran | Pengumpulan terhenti sebagian | Skrip berhenti otomatis, jeda *scroll* diperlambat, pengambilan diulang setelah beberapa jam |
| Data pribadi dalam teks | 85 unggahan bertanda indikasi data pribadi di teks aslinya | Risiko privasi | Disamarkan dengan penanda di seluruh versi teks |
| Teks sangat pendek | 97 unggahan kurang dari 4 token | Sedikit informasi untuk pemodelan topik | Hanya ditandai |
| Metrik keterlibatan | Bergantung pada *field* yang tersedia di respons JSON | Nilai bisa kosong | Dipakai sebagai pelengkap, bukan variabel utama |
| Presisi aturan belum diukur untuk Threads | 20 keputusan peninjau masuk, seluruhnya dari antrean `pending`. Sampel berstrata 200 unggahan `threads/sampel_review_threads.csv` belum diisi | Angka presisi 91,5% hanya berlaku untuk korpus X dan tidak boleh dipakai untuk Threads. Korpus Threads memakai aturan inklusi yang berbeda, sehingga presisinya bisa berbeda jauh | Berkas sampelnya sudah siap dengan 40 baris kalibrasi. Bila tidak terisi sebelum tenggat, laporan harus menyatakan presisi Threads belum terukur |
| Keterwakilan populasi | Pengguna Threads tidak mewakili seluruh lulusan baru Indonesia. Unggahan terhapus atau dari akun privat tidak terjaring | Temuan bersifat indikatif atas wacana daring | Tidak digeneralisasi sebagai opini nasional |

### C6. Pertimbangan etika

Berlaku sama dengan C6 korpus X, dengan dua tambahan khusus Threads:

- **Login wajib.** Pencarian Threads mensyaratkan login, sehingga unggahan yang diambil tetap
  publik tetapi aksesnya memakai akun. Ketentuan layanan Meta/Threads tentang pengumpulan data
  otomatis perlu dirujuk langsung dalam laporan.
- **Risiko akun pengumpul.** Akun Threads terhubung ke akun Instagram pribadi pengumpul data,
  sehingga pembatasan akibat aktivitas otomatis berisiko berdampak pada akun tersebut.

### C7. Ringkasan

Korpus Threads terdiri dari 3.190 unggahan *model-ready* dari 6.028 unggahan mentah unik yang
dikumpulkan dari lima kata kunci dalam 11 putaran *scraping* berbasis JSON dengan Playwright.
Karena pencarian Threads tidak mendukung frasa persis maupun filter bahasa, 43,4% data mentah
terjaring tanpa menyebut nama program, sehingga tim memutuskan membatasi korpus Threads pada
unggahan yang menyebut nama program dan mengeluarkan 1.089 unggahan jalur konteks. Korpus ini
menyediakan teks untuk RQ1 dan RQ2 serta penanda waktu dan fase untuk RQ3, dan menjangkau
ketiga fase. Keterbatasan utamanya adalah metadata yang jauh lebih miskin daripada X, karena
bahasa, jenis unggahan, dan status pemotongan teks seluruhnya kosong; kriteria inklusi yang
lebih ketat daripada korpus X; kepadatan fase 1 yang baru mengisi 47 dari 62 hari; serta presisi
aturan yang belum terukur karena sampel berstrata Threads belum ditinjau.

---

## Ringkasan gabungan X dan Threads

| Aspek | X | Threads | Gabungan |
|---|---:|---:|---:|
| Unggahan mentah unik | 5.257 | 6.028 | 11.285 |
| *Model-ready* | 4.263 | 3.190 | 7.453 |
| Menunggu peninjau | 20 | 0 | 20 |
| Dikeluarkan | 974 | 2.838 | 3.812 |
| Unggahan yang sudah diputuskan peninjau | 232 | 20 | 252 |
| Penulis unik atas seluruh unggahan unik | 2.651 | 3.881 | 6.532 |
| Tanpa akun resmi dan media terdaftar | 4.162 | 2.992 | 7.154 |
| Satu wakil per teks identik | 4.234 | 3.090 | 7.324 |

Komposisi *model-ready* gabungan per fase:

| Fase | X | Threads | Gabungan | % korpus gabungan |
|---|---:|---:|---:|---:|
| Fase 1: pengumuman (62 hari) | 2.345 | 729 | 3.074 | 41,2% |
| Fase 2: seleksi (20 hari) | 895 | 643 | 1.538 | 20,6% |
| Fase 3: penempatan (35 hari) | 1.023 | 1.818 | 2.841 | 38,1% |
| **Total** | **4.263** | **3.190** | **7.453** | |

Angka penulis unik gabungan adalah penjumlahan sederhana. `user_hash` dihitung per platform,
sehingga satu orang yang aktif di X dan Threads terhitung dua kali dan tidak dapat dipadankan.

Dua catatan penting sebelum angka gabungan dipakai di laporan. Pertama, kriteria inklusi kedua
korpus tidak identik: korpus X memakai jalur relevansi konteks, korpus Threads tidak. Kedua,
fase 1 kini menjadi fase dengan unggahan terbanyak (3.074 unggahan, 41,2% korpus), berbeda jauh
dari pengumpulan putaran pertama yang hampir tidak menjangkau fase itu. Ketiga, presisi aturan
baru terukur untuk korpus X; angka 91,5% tidak boleh dipakai untuk korpus Threads.

### Yang belum selesai sebelum laporan dikumpulkan

| Pekerjaan | Keadaan | Akibat bila dibiarkan |
|---|---|---|
| Peninjau kedua untuk kalibrasi | 40 baris `kalibrasi_dua_peninjau=1` di `sampel_review_x.csv` sudah diisi `peninjau_1`; peninjau kedua tidak jadi mengisi karena keterbatasan waktu tim | Cohen's kappa antarpeninjau tidak dapat dilaporkan. Yang tersedia hanya konsistensi satu peninjau pada dua kesempatan (relevansi kappa 0,51; promosi kappa 0,71, n=20), dan itu bukan penggantinya. Angka validasi 76,7% dari putaran pertama berasal dari korpus lama dan tidak berlaku untuk *snapshot* ini |
| Sampel berstrata Threads | `threads/sampel_review_threads.csv` 200 baris, tidak jadi diisi pada putaran ini; 20 unggahan Threads yang sudah ditinjau seluruhnya berasal dari antrean `pending`, bukan dari sampel acak | Presisi aturan untuk korpus Threads tidak dapat dilaporkan. Angka 91,5% hanya berlaku untuk korpus X, dan laporan harus menyebut kekosongan ini di C5 |
| Antrean `pending` | 20 unggahan di korpus X, seluruhnya ditahan karena peninjau sendiri ragu | 0,2% unggahan unik gabungan tidak masuk korpus maupun dibuang. Keputusannya bergantung pada teks kutipan atau unggahan induk yang tidak tersimpan |
| Dasar pembatasan Threads | Pemeriksaan manusia yang mendasari pengecualian 1.089 unggahan tercatat sebagai komentar di `config.py`, bukan sebagai keputusan peninjau di `data/annotations/`. Sebagai gantinya tersedia pemeriksaan kata kunci otomatis atas seluruh 1.089 unggahan, angkanya ada di C5 korpus Threads | Pengecualian terbesar di korpus Threads tidak punya jejak pembacaan manusia yang dapat diverifikasi. Laporan harus menyebut dasarnya sebagai pemeriksaan otomatis, bukan sebagai peninjauan manusia |
| Pemeriksaan label akun | 7.154 unggahan *model-ready* berlabel `tidak_terdaftar` | Pemisahan opini publik dari narasi resmi belum terjamin |
| Audit *snapshot* | `data/interim/` tercantum di `.gitignore`, sehingga folder *snapshot* tidak ada di salinan repositori | Terpecahkan. Folder *snapshot* dapat dibangun ulang dari `data/raw/` memakai `byte_limit` dan `sha256` di `snapshot_manifest.json`; setelah itu `preprocess_tk2.py audit` berjalan dan berstatus OK. Langkahnya ada di "Catatan reproduksi" |

Alur peninjauan: buka `alat_review/review.html` di browser, isi nama peninjau, pilih
`sampel_review_<platform>.csv` atau `antrean_review_<platform>.csv`, labeli dengan pintasan
tombol, lalu ekspor CSV. Jalankan `python preprocess_tk2.py import-review <berkas>` diikuti
`python preprocess_tk2.py run` agar keputusan diterapkan. Presisi aturan dihitung dari berkas
sampel yang sudah diisi dengan `python alat_review/presisi_aturan.py <berkas>`. Untuk
kesepakatan antarpeninjau, dua orang mengisi 40 baris `kalibrasi_dua_peninjau=1` secara
terpisah, lalu jalankan `python alat_review/kappa_kalibrasi.py`. Keputusan manusia mengalahkan
aturan, dan peninjau bernama `auto`, `agent`, atau `model` ditolak oleh skrip.

Putaran peninjauan pertama memakai nama peninjau `peninjau_1`, bukan nama orang, karena
berkas ekspornya ikut masuk repositori publik. Berkas hasilnya:

| Berkas | Isi | Baris terisi |
|---|---|---:|
| `review_peninjau1_kalibrasi.csv` | 40 baris kalibrasi korpus X | 40 |
| `review_peninjau1_sampel.csv` | Sampel berstrata 200 unggahan korpus X | 200 |
| `antrean_review_x__peninjau1.csv` | Seluruh antrean `pending` korpus X | 52 |
| `threads/antrean_review_threads__peninjau1.csv` | Seluruh antrean `pending` korpus Threads | 20 |

Sampel berstrata dibekukan sekali per folder keluaran. `preprocess_tk2.py run` tidak mengundi
ulang `sampel_review_*.csv` bila berkasnya sudah ada, karena strata dan bobotnya memakai
`status_final`, yang bergeser setiap kali keputusan peninjau masuk. Tanpa pembekuan ini, undian
ulang akan membuat label yang sudah diisi kehilangan populasi acuannya, sehingga presisi dan
kappa tidak lagi dapat dihitung. Untuk mengundi ulang dengan sengaja, hapus berkas sampelnya.

Dua catatan jujur tentang putaran ini. Pertama, 20 dari 52 baris antrean X juga ada di sampel
berstrata, dan di 9 di antaranya peninjau memberi nilai berbeda pada dua kesempatan: di berkas
antrean, yang menampilkan tebakan mesin, ia lebih sering memilih `ragu`. Impor memakai urutan
waktu pengisian, sehingga penilaian terakhir yang berlaku. Kedua, berkas kalibrasi dan sampel
memuat 40 baris yang sama dan penilaiannya identik, jadi tidak ada konflik di dalam satu
peninjau.

### Keputusan: data Threads putaran pertama tidak digabungkan

Pengumpulan Threads putaran pertama menyimpan 1.092 unggahan yang tidak terjaring lagi pada
putaran kedua, karena hasil pencarian Threads bergeser antar-waktu. Berkasnya ada di
`data/raw_tambahan_putaran1/threads_putaran1_tambahan.jsonl` dan sengaja diletakkan di luar
`data/raw/` agar tidak ikut terbaca oleh `preprocess_tk2.py snapshot`.

Simulasi dengan aturan yang berlaku sekarang memberi 425 unggahan lolos, 666 dikeluarkan, dan 1
menunggu peninjau. Pemeriksaan atas 425 unggahan yang lolos menunjukkan masalah:

| Temuan | Angka |
|---|---:|
| Lolos lewat jalur `eksplisit_generik`, yaitu hanya menyebut "magang nasional" atau "pemagangan nasional" | 309 dari 425 (73%) |
| Di antaranya yang sama sekali tidak menyebut MagangHub maupun Kemnaker | 302 dari 309 (98%) |
| Terjaring oleh kata kunci `magang nasional` | 304 dari 309 |
| Memakai tagar kampanye (`#jagaindonesia` 22%, `#indonesiakita` 20%, `#indonesiamaju` 9%) | 196 dari 305 (64%) |
| Berteks identik dengan unggahan lain dalam kumpulan yang sama | 55 unggahan dalam 16 grup, dari 216 penulis unik |

Pola ini khas kampanye terkoordinasi: naskah promosi yang sama diunggah banyak akun berbeda,
bukan satu akun berulang. Isinya seragam positif, misalnya ajakan mengambil peluang dan
pernyataan bahwa program membuka kesempatan. Memasukkan 302 unggahan semacam itu akan menambah
korpus 13,4% tetapi menggeser distribusi sentimen ke arah positif secara sistematis, tepat pada
variabel yang diukur RQ2, dan memunculkan slogan kampanye sebagai topik di RQ1.

Sisa yang bersih, yaitu unggahan yang menyebut nama khas program, hanya sekitar 120 unggahan atau
1,6% korpus gabungan. Nilainya tidak sebanding dengan risiko di atas maupun dengan biaya
menjalankan ulang seluruh *preprocessing*.

Karena itu kumpulan ini **tidak digabungkan**. Berkasnya tetap disimpan di repositori agar
keputusan ini dapat diperiksa ulang, dan pemeriksaan di atas dapat diulang dengan
`relevansi.py` serta `promosi.py` versi sekarang.

### Catatan reproduksi

*Snapshot* `20261026_3067bfd95e` pertama kali dijalankan di macOS dengan Python 3.12.11,
pandas 3.1.0, NumPy 2.5.4, dan scikit-learn 1.9.1. *Snapshot* sebelumnya dijalankan di Windows
dengan pandas 3.0.0. Perbedaan versi paket tidak mengubah aturan, tetapi perlu dicatat karena
deteksi duplikat-dekat memakai TF-IDF dari scikit-learn. Versi persis setiap *snapshot* tercatat
di `snapshot_manifest.json` masing-masing.

*Snapshot* yang sama dijalankan ulang di Windows 11 dengan Python 3.13 sebelum keputusan peninjau
dimasukkan, dan hasilnya identik angka per angka: X 4.286 *model-ready*, 52 `pending`, 919
dikeluarkan; Threads 3.183, 20, dan 2.825. Satu-satunya kolom yang berbeda adalah `user_hash`,
karena garam pseudonimisasi bersifat lokal per komputer. Jadi perbedaan angka sesudahnya berasal
dari keputusan peninjau, bukan dari lingkungan.

Folder *snapshot* sendiri tidak ikut masuk repositori, tetapi dapat dibangun ulang dari
`data/raw/` karena berkas mentahnya bersifat *append-only* dan manifestnya menyimpan `byte_limit`
serta `sha256` setiap berkas:

```python
import json
from pathlib import Path
from tk2prep import snapshot as sn

m = json.loads(Path("data/processed/preprocess_20261026_3067bfd95e/snapshot_manifest.json")
               .read_text(encoding="utf-8"))
folder = Path("data/interim/snapshots") / m["snapshot_id"]
sn.rekonstruksi_dari_raw(m, Path("data/raw"), folder)          # gagal bila raw sudah berubah
meta = folder / "raw" / "_meta"
meta.mkdir(parents=True, exist_ok=True)
for f in m["supporting_files"]:                                 # metadata cakupan kolektor
    (meta / f["file"]).write_bytes((Path("data/raw") / f["file"]).read_bytes())
(folder / "snapshot_manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2),
                                               encoding="utf-8", newline="
")
sn.verifikasi_snapshot(folder)                                  # melempar galat bila tidak cocok
```

Sesudah itu `python preprocess_tk2.py run` dan `python preprocess_tk2.py audit` berjalan dari
salinan repositori, dan audit berstatus OK.

Agar `sha256` tetap cocok di Windows, macOS, dan Linux, `.gitattributes` memuat `data/** -text`
sehingga Git tidak mengubah akhir baris berkas data. Laporan dan konfigurasi yang dihasilkan
`preprocess_tk2.py run` juga ditulis dengan akhir baris LF di semua sistem operasi, supaya
keluaran dari dua komputer berbeda dapat dibandingkan langsung.

## Panduan menulis laporan bagian C

Bagian ini untuk penulis laporan. Seluruh README di atas adalah bahan mentah dan jauh melebihi
batas kata, jadi di bawah ini sudah dipilihkan apa yang masuk ke tiap subbagian, angka mana yang
dipakai, dan klaim mana yang tidak boleh ditulis.

| Bagian | Panjang | Wajib ada |
|---|---|---|
| C1. Kebutuhan data | 150 sampai 200 kata | |
| C2. Pipeline pengumpulan data | 200 sampai 250 kata | Diagram pipeline beserta teknologinya |
| C3. Metode pengumpulan data | 200 sampai 250 kata | Tautan repositori <https://github.com/flihid/maganghub-pipeline> |
| C4. Implementasi pipeline | 200 sampai 250 kata | |
| C5. Kualitas data dan keterbatasannya | 100 sampai 150 kata | |
| C6. Pertimbangan etika | 100 sampai 150 kata | |
| C7. Ringkasan | 100 sampai 150 kata | |

Tiga aturan yang berlaku di semua subbagian:

1. Angka hanya boleh berasal dari `data/processed/preprocess_20261026_3067bfd95e/`. Jalankan
   `python cek_angka_readme.py`; kalau lolos, angka di README cocok dengan *snapshot*.
2. Jangan menulis nama akun pribadi dan jangan mengutip unggahan persis. Akun lembaga
   (Kemnaker, media, `meta.ai`) boleh disebut. Contoh unggahan diparafrasekan.
3. Istilah asing dicetak miring. Kalimat aktif. Tanpa kalimat pembuka basa-basi.

### Isi C1. Kebutuhan data

Tulis: dua platform dengan peran berbeda, X sebagai korpus utama dan Threads sebagai pelengkap;
periode 1 Juli sampai 25 Oktober 2026 yang dibagi tiga fase; lima kata kunci yang sama di kedua
platform; atribut yang diambil (teks, waktu unggah, bahasa, jenis unggahan, metrik keterlibatan)
beserta kaitannya dengan ketiga pertanyaan penelitian; kriteria inklusi dan eksklusi.

Angka: 11.285 unggahan mentah unik, 7.453 *model-ready*.

Jangan menulis bahwa korpus ini mewakili seluruh percakapan tentang program. Ini hasil pencarian
dengan batas kolektor, bukan sensus.

### Isi C2. Pipeline pengumpulan data

Pakai diagram di bagian "Alur pipeline" di awal README ini. Gambar ulang rapi, jangan menempel
teks ASCII-nya.

Teknologi yang perlu muncul di diagram: Python 3.12 sampai 3.13; `twscrape` 0.20.1 yang memakai
*endpoint* internal X dengan sesi akun, bukan API resmi berbayar; Playwright (Chromium) untuk
pembacaan DOM X dan untuk Threads yang mewajibkan login; pandas dan scikit-learn (TF-IDF
`char_wb` 3-5) di tahap *preprocessing*; JSONL sebagai penyimpanan mentah; CSV dan JSONL sebagai
keluaran.

Jelaskan empat tahap: pengambilan per platform, pembekuan *snapshot* dengan `sha256`,
*preprocessing* bersama untuk kedua platform, lalu peninjauan manusia yang keputusannya
dimasukkan kembali dan menang atas aturan.

Satu hal yang membedakan pipeline ini dan layak ditonjolkan: *snapshot* dibekukan sebelum
diolah, sehingga angka yang dilaporkan dapat diverifikasi ulang tanpa mengumpulkan data lagi.

### Isi C3. Metode pengumpulan data

Tautan repositori: <https://github.com/flihid/maganghub-pipeline>

Tulis: satu kueri gabungan lima kata kunci dengan `OR` dan filter `lang:in` di X, dijalankan per
hari kalender atas seluruh 117 hari; Threads tidak mendukung frasa persis, filter bahasa, maupun
filter tanggal, sehingga penyaringan dipindahkan ke tahap *preprocessing*; jeda minimum 5 detik
antar-halaman dan 25 detik antar-kueri yang dipaksakan di tingkat validasi argumen; penanganan
status 429 dengan berhenti, bukan dengan mengakalinya.

Angka per platform: X 5.257 unggahan mentah unik dari 3 berkas, Threads 6.028 dari 5 berkas.

Sebutkan juga filter bahasa yang salah di awal pengambilan: `lang:id` mengembalikan nol hasil
untuk rentang yang `lang:in` mengembalikan unggahan Indonesia, sehingga hari yang kosong dengan
filter lama diambil ulang. Ini contoh keputusan metodologis yang terdokumentasi, bukan kelemahan
yang disembunyikan.

### Isi C4. Implementasi pipeline

Tulis urutan yang benar-benar dijalankan, bukan rencana: `twscrape_pipeline.py plan` sampai
`collect`, lalu `02_scrape_threads.py`, lalu `preprocess_tk2.py snapshot` dan `run`, lalu
`import-review` dan `run` sekali lagi, lalu `audit`.

Jelaskan tiga mekanisme yang membuat hasilnya dapat diperiksa:

- Setiap unggahan mendapat tepat satu `status_final` dan satu `alasan_utama`, dan
  `keep + pending + exclude` selalu sama dengan jumlah unggahan unik. Rekonsiliasi berstatus OK
  di kedua korpus.
- Keputusan manusia disimpan *append-only* di `data/annotations/review_decisions_log.csv`, di
  luar folder keluaran, sehingga menjalankan ulang *preprocessing* tidak menghapusnya.
- Sampel berstrata dibekukan, sehingga bobot dan baris kalibrasinya tetap sah meski
  *preprocessing* dijalankan berkali-kali.

Angka tahapan X: mentah 5.257, karantina 0, unik 5.257, dikeluarkan 974, menunggu peninjau 20,
*model-ready* 4.263. Threads: 6.028, 0, 6.028, 2.838, 0, 3.190.

### Isi C5. Kualitas data dan keterbatasannya

Batas katanya paling ketat, jadi ambil empat hal ini dan tinggalkan sisanya ke README:

1. **Presisi aturan terukur untuk korpus X.** Dari sampel berstrata 200 unggahan, status `keep`
   disetujui peninjau pada 91,5% ± 5,0 populasi *model-ready*, dengan batas bawah pesimistis
   80,0% bila 17 baris `ragu` dianggap salah. Status `exclude` disetujui 98,6% ± 1,6.
2. **Kesepakatan antarpeninjau tidak ada.** Baru satu peninjau mengisi baris kalibrasi, sehingga
   Cohen's kappa antarpeninjau tidak dapat dilaporkan. Yang tersedia hanya konsistensi satu
   peninjau pada dua kesempatan, relevansi kappa 0,51 dan promosi kappa 0,71 atas 20 unggahan
   tersulit. Tulis sebagai keterbatasan, bukan sebagai pengganti.
3. **Presisi korpus Threads belum terukur**, dan kriteria inklusinya berbeda dari X karena jalur
   relevansi konteks tidak dipakai. Angka 91,5% tidak berlaku untuk Threads.
4. **Konten kampanye terkoordinasi**, 0,8% di korpus X dan 6,8% di korpus Threads, menggeser
   distribusi sentimen ke arah positif tepat pada variabel yang diukur RQ2.

Kalau masih ada ruang, tambahkan satu kalimat bahwa tidak satu pun dari 117 hari berstatus
lengkap, sehingga volume per tanggal tidak boleh dibaca sebagai volume percakapan sebenarnya.

### Isi C6. Pertimbangan etika

Ambil empat ini:

1. **Tidak menembus pembatasan platform.** Pipeline tidak menyamarkan otomatisasi, tidak
   menyalin *cookie*, dan tidak mengakali status 429. Ketika platform menolak, pengumpulan
   berhenti dan dicatat sebagai keterbatasan.
2. **Minimalisasi dan pseudonimisasi.** Nama tampilan, foto profil, bio, dan jumlah pengikut
   tidak diambil. *Username* diganti hash SHA-256 bergaram di seluruh keluaran olahan.
   Pseudonimisasi bukan anonimisasi, karena teks unggahan publik tetap dapat dicari.
3. **Data mentah berada di repositori publik atas keputusan tim**, dan masih memuat *username*.
   Nyatakan ini terbuka sebagai konsekuensi yang diterima demi reproduktibilitas. Jangan
   dilewati, karena repositorinya memang dapat dibuka siapa saja.
4. **Ketentuan layanan.** Rujuk langsung ketentuan X dan Meta/Threads tentang pengumpulan data
   otomatis. Tautannya belum ada di README, jadi cari sendiri dan cantumkan di daftar pustaka.

### Isi C7. Ringkasan

Satu paragraf: apa yang terkumpul, dengan apa, seberapa dapat dipercaya, dan apa yang belum.

Angka inti: 11.285 unggahan mentah unik menjadi 7.453 *model-ready* dari dua platform; fase 1
3.074 unggahan (41,2%), fase 2 1.538 (20,6%), fase 3 2.841 (38,1%); presisi aturan korpus X
91,5% ± 5,0.

Tutup dengan dua kekurangan yang jujur: kesepakatan antarpeninjau belum terukur, dan presisi
korpus Threads belum terukur.

### Yang tidak boleh ditulis

- Jangan menulis bahwa data sudah divalidasi dua peninjau. Belum.
- Jangan memakai 91,5% untuk korpus Threads atau untuk korpus gabungan. Itu angka korpus X.
- Jangan menyebut kappa 0,51 sebagai kesepakatan antarpeninjau. Itu satu orang, dua kesempatan.
- Jangan memakai angka validasi 76,7% dari putaran pertama. Itu berasal dari korpus lama.
- Jangan menulis bahwa 1.089 unggahan Threads dikeluarkan setelah pembacaan manusia. Dasarnya
  pemeriksaan kata kunci otomatis.
- Jangan mengambil angka dari `preprocess_20261026_d11a2b74c6/`, `maganghub_bersih.csv`, atau
  `ringkasan_per_fase.csv`. Semuanya keluaran lama dengan aturan yang berbeda.
