# MagangHub Data Collection Pipeline

Pipeline pengumpulan dan *preprocessing* data media sosial X dan Threads untuk penelitian
**"Analisis Pro Kontra Publik terhadap Program Magang Nasional MagangHub pada Media Sosial X"**
(Tugas Kelompok 2, CSIE604284 Analitika Media Sosial, Fasilkom UI, Gasal 2026/2027).

Pipeline ini mengumpulkan unggahan publik berbahasa Indonesia yang menyebut Program Magang
Nasional/MagangHub dalam tiga jendela waktu penyelenggaraan program, dari X (korpus utama) dan
Threads (korpus pelengkap), lalu membersihkannya menjadi satu dataset siap analisis untuk
pemodelan topik (BERTopic) dan klasifikasi sentimen (IndoBERT).

Ringkasan hasil pengumpulan data untuk laporan bagian C ada di
[Temuan pengumpulan data Threads](#temuan-pengumpulan-data-threads).

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
# X
python 01_simpan_sesi.py
python 02_scrape_x.py --uji
python 02_scrape_x.py

# Threads
python 01_simpan_sesi_threads.py
python 02_scrape_threads.py --uji
python 02_scrape_threads.py

# Gabungan
python cek_cakupan.py
python 03_preprocess.py
```

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

## Temuan pengumpulan data Threads

Bagian ini merangkum hasil nyata pengumpulan data Threads sebagai bahan laporan bagian C.
Semua angka berasal dari keluaran `02_scrape_threads.py`, `cek_cakupan.py`, dan
`03_preprocess.py`. Waktu persis setiap putaran tercatat di `data/raw/log_scraping_threads.csv`.
Sesuai prinsip privasi di bagian C6, nama akun pribadi tidak dicantumkan dan contoh post
diparafrasekan.

### C1. Kebutuhan data

| Aspek | Spesifikasi |
|---|---|
| Platform | Threads (korpus pelengkap); X sebagai korpus utama |
| Sasaran konten | Post publik berbahasa Indonesia tentang Program Magang Nasional/MagangHub |
| Kata kunci | `maganghub`, `magang hub`, `magang nasional`, `magang kemnaker`, `pemagangan nasional` |
| Periode | 1 Juli–25 Oktober 2026, dibagi tiga fase: pengumuman (1 Juli–31 Agustus), seleksi (1–20 September), penempatan (21 September–25 Oktober) |
| Lingkup geografis | Tidak dibatasi secara eksplisit; dibatasi secara tidak langsung oleh bahasa dan topik program nasional |
| Atribut konten | Teks post, waktu unggah, jumlah balasan, *repost*, dan suka |
| Metadata | ID post, kata kunci yang menjaring, waktu pengambilan data |
| Volume terkumpul | 3.862 post mentah unik → 2.166 post bersih |
| Kriteria inklusi | (1) Teks menyebut nama program, **atau** (2) post terjaring kata kunci jangkar dan memuat istilah khas program; (3) diunggah di dalam periode penelitian |
| Kriteria eksklusi | Duplikat dan salin-tempel, spam/promosi, akun otomatis (`meta.ai`), teks kurang dari 4 kata bermakna, post di luar periode |

Tabel kebutuhan data per pertanyaan penelitian:

| Pertanyaan penelitian | Kebutuhan data | Atribut utama | Alasan |
|---|---|---|---|
| RQ1: topik yang membentuk dukungan dan keberatan | Teks post publik tentang program | `teks_model`, `teks_token` | Bahan pemodelan topik |
| RQ2: polaritas penilaian per topik | Teks post yang sama | `teks_model` | Bahan klasifikasi sentimen; kata negasi dipertahankan |
| RQ3: pergeseran antarfase | Waktu unggah | `waktu_wib`, `fase` | Mengelompokkan post ke tiga fase penyelenggaraan |
| Pemisahan opini publik dari narasi resmi | Jenis akun | `jenis_akun` | Post media dan akun resmi bukan opini publik |
| Resonansi argumen (pelengkap) | Metrik keterlibatan | `n_reply`, `n_repost`, `n_like` | Menandai post yang paling banyak ditanggapi |

### C2. Pipeline pengumpulan data

```
config.py ─► 01_simpan_sesi_threads.py ─► 02_scrape_threads.py ─► cek_cakupan.py ─► 03_preprocess.py
 parameter     login manual (Instagram),    Playwright: cari,        cek rentang          gabung, relevansi,
               simpan cookie sesi           scroll, baca JSON        tanggal & presisi    dedup, spam, akun,
                                            → data/raw/*.jsonl                            anonimisasi, normalisasi
                                                                                          → maganghub_bersih.csv
```

Teknologi: Python 3, Playwright (Chromium) untuk halaman dinamis, pandas untuk pengolahan,
SHA-256 bergaram untuk pseudonimisasi, *Colloquial Indonesian Lexicon* (4.349 entri setelah
digabung dengan kamus bawaan) untuk normalisasi kata tidak baku.

### C3. Metode pengumpulan data

| Aspek | Implementasi |
|---|---|
| Pendekatan | *Web scraping* dengan Playwright. API resmi Threads punya pencarian kata kunci, tetapi tanpa izin `threads_keyword_search` melalui *App Review* Meta, pencarian hanya mencakup post milik akun sendiri |
| Otentikasi | Login manual sekali dengan akun Instagram; cookie sesi disimpan di `sesi_threads.json`. Keabsahan sesi diverifikasi dengan membuka halaman pencarian, karena login Instagram terjadi di tab baru |
| Kueri | `https://www.threads.com/search?q=<kata kunci>&serp_type=default&filter=recent` (tab *Terbaru*) |
| Ekstraksi | Tidak memakai selector HTML, karena Threads memakai nama class yang diacak. Data diambil dari JSON yang tertanam di halaman (`<script type="application/json" data-sjs>`) dan dari respons jaringan yang dimuat saat halaman di-scroll. Objek post dikenali dari kombinasi field `code`, `taken_at`, `caption.text`, dan `user.username` |
| *Pagination* | *Infinite scroll*. Pencarian Threads tidak punya filter tanggal, sehingga hasil diurutkan dari yang terbaru |
| Kondisi berhenti | (1) Batas post per kata kunci tercapai; (2) 6 kali scroll tanpa post baru terlihat; (3) 3 putaran berturut-turut hanya berisi post sebelum 1 Juli 2026; (4) status HTTP 429 |
| *Rate limiting* | Jeda acak 5–9 detik antar-scroll (awalnya 2,5–5 detik, diperlambat setelah menerima status 429) dan 25–50 detik antar-kata kunci |
| Deteksi duplikat | Per ID post saat pengumpulan; duplikat-dekat (teks identik setelah dinormalisasi) saat *preprocessing* |
| Penanganan kegagalan | Status setiap kata kunci dicatat di log. Skrip berhenti otomatis ketika sesi kedaluwarsa atau menerima 429, menyimpan progres, dan dapat dilanjutkan tanpa mengulang kata kunci yang selesai |
| Format luaran | JSON Lines (`data/raw/threads_<kata-kunci>.jsonl`), satu post per baris |
| Penyimpanan | Lokal di laptop pengumpul data; tidak di-commit ke repository publik |

Contoh struktur satu record mentah (nilai diganti contoh):

```json
{"tweet_id": "th_1234567890", "platform": "threads",
 "url": "https://www.threads.com/@<username>/post/<kode>",
 "username": "<username>", "created_at": "2026-10-20T05:00:00+00:00",
 "text": "<isi post>", "n_reply": 3, "n_repost": 0, "n_like": 12,
 "kueri": "maganghub", "scraped_at": "2026-10-25T07:12:03+00:00"}
```

### C4. Implementasi pipeline

Pengumpulan dilakukan dalam tiga putaran:

| Putaran | Perintah | Hasil |
|---|---|---|
| Uji coba | `--uji` | 20 post dari kata kunci `maganghub`, memastikan ekstraksi berjalan |
| 1 | semua kata kunci, batas 800 per kata kunci | `maganghub` 800 (batas), `magang hub` 312 (hasil habis), `magang nasional` 800 (batas), `magang kemnaker` 800 (batas), `pemagangan nasional` 800 (batas). Total 3.532 |
| 2 | `--kata maganghub --kata "magang kemnaker" --maks 4000` | `maganghub` +201, lalu dihentikan oleh status 429 sebelum `magang kemnaker` dijalankan. Total 3.733 |
| 3 | sama, setelah jeda beberapa jam dan scroll diperlambat | `magang kemnaker` +73, `maganghub` +56; keduanya berhenti karena hasil pencarian habis. Total 3.862 |

Cakupan akhir per kata kunci (`cek_cakupan.py`):

| Kata kunci | Jumlah | Tertua | Terbaru | Menyebut nama program | Relevan total | Menjangkau fase 1 |
|---|---:|---|---|---:|---:|---|
| `maganghub` | 1.077 | 19 Sep | 25 Okt | 51% | 66% | Tidak |
| `magang hub` | 312 | 10 Sep | 25 Okt | 80% | 81% | Tidak |
| `magang kemnaker` | 873 | 7 Sep | 25 Okt | 55% | 75% | Tidak |
| `magang nasional` | 800 | 29 Jun | 25 Okt | 92% | 92% | Ya |
| `pemagangan nasional` | 800 | 15 Jun | 25 Okt | 6% | 6% | Ya |
| **Total unik** | **3.862** | | | | | |

Tahapan *preprocessing* (`log_preprocessing.csv`):

| No. | Tahap | Sebelum | Sesudah | Dibuang | Keterangan |
|---:|---|---:|---:|---:|---|
| 1 | Gabung data mentah | 3.862 | 3.862 | 0 | 5 file |
| 2 | Deduplikasi ID post | 3.862 | 3.862 | 0 | |
| 3 | Teks kosong | 3.862 | 3.862 | 0 | |
| 4 | Saring relevansi | 3.862 | 2.406 | 1.456 | Lolos eksplisit 2.066, lolos konteks 340 |
| 5 | Duplikat-dekat | 2.406 | 2.291 | 115 | Teks identik; disimpan yang paling awal |
| 6 | Spam | 2.291 | 2.259 | 32 | Pola promosi/joki atau lebih dari 5 tagar |
| 7 | Akun otomatis | 2.259 | 2.234 | 25 | `meta.ai` |
| 8 | Teks terlalu pendek | 2.234 | 2.170 | 64 | Kurang dari 4 kata bermakna |
| 9 | Di luar periode | 2.170 | 2.166 | 4 | |

Komposisi dataset akhir:

| Fase | Media | Publik | Resmi | Total | % dataset | Post per hari |
|---|---:|---:|---:|---:|---:|---:|
| Fase 1: pengumuman (62 hari) | 2 | 140 | 1 | 143 | 6,6% | 2,3 |
| Fase 2: seleksi (20 hari) | 19 | 517 | 16 | 552 | 25,5% | 27,6 |
| Fase 3: penempatan (35 hari) | 71 | 1.353 | 47 | 1.471 | 67,9% | 42,0 |
| **Total** | **92** | **2.010** | **64** | **2.166** | | |

Akun resmi yang teridentifikasi: `kemnaker`, `maganghub.kemnaker`. Akun media dan informasi
karier: `viralyn.daily`, `mcinews.id`, `titik_temu.news`, `satu_meja.id`,
`temankarirofficial`, `internship.career`.

### C5. Kualitas data dan keterbatasannya

| Isu | Temuan | Dampak | Mitigasi |
|---|---|---|---|
| Kedalaman pencarian terbatas | Kata kunci utama tidak menjangkau sebelum September (`maganghub` berhenti di 19 Sep, `magang kemnaker` 7 Sep) walau dijalankan ulang dengan batas 4.000; status akhirnya "hasil habis", bukan batas skrip | Fase 1 kurang terwakili (6,6% dataset, 2,3 post/hari) | Fase 1 diisi kata kunci `magang nasional` yang menjangkau 29 Juni; korpus X dapat diarahkan langsung ke Juli–Agustus; RQ3 membandingkan **proporsi** topik per fase, bukan jumlah post; temuan fase 1 dilaporkan sebagai indikatif |
| Bias volume antarfase | Jumlah post per hari naik dari 2,3 (fase 1) ke 42,0 (fase 3) | Tidak dapat dipisahkan apakah ini peningkatan diskusi yang nyata atau efek kedalaman pencarian | Dinyatakan sebagai keterbatasan; perbandingan memakai proporsi |
| Presisi kata kunci rendah | Pencarian Threads tidak mendukung frasa persis; `pemagangan nasional` hanya 6% relevan | 37,7% data mentah tidak relevan | Saring relevansi; presisi per kata kunci dilaporkan |
| Post relevan tanpa nama program | Pemeriksaan 10 sampel post yang terbuang menunjukkan sebagian besar membahas program tanpa menyebut namanya (misalnya soal *batch*, pencairan uang saku, atau absen yang harus disetujui mentor) | Saringan eksplisit saja akan membuang data relevan | Jalur relevansi konteks: menyelamatkan 340 post |
| Validitas jalur konteks | 23 dari 30 sampel acak dinilai relevan secara manual (**presisi 76,7%**). Post dinilai relevan bila memuat setidaknya satu penanda khas program | Jalur konteks menyumbang ±14% post relevan, sehingga perkiraan *noise* di dataset akhir sekitar **3%** | Diterima sebagai kompromi; kolom `dasar_relevansi` memungkinkan analisis ulang tanpa jalur konteks |
| Duplikasi | 115 post salin-tempel | Menggelembungkan frekuensi topik | Dibuang; disimpan versi paling awal |
| Spam dan akun otomatis | 32 post promosi/joki; 25 jawaban asisten AI `meta.ai` | Bukan opini publik | Dibuang |
| Dominasi akun | Satu akun pribadi menyumbang 33 post mentah | Opini segelintir akun sangat aktif dapat ikut membentuk gambaran | Dinyatakan sebagai keterbatasan; `user_hash` memungkinkan analisis per akun |
| Pembatasan platform | Status 429 diterima pada putaran 2 | Pengumpulan terhenti sebagian | Skrip berhenti otomatis, jeda scroll diperlambat, pengambilan diulang setelah beberapa jam |
| Bahasa tidak baku | Singkatan, *slang*, dan *code-mixing* | Mengganggu analisis berbasis kata | Normalisasi dengan leksikon 4.349 entri; dua versi teks untuk model dan untuk analisis kata |
| Metrik keterlibatan | Bergantung pada field yang tersedia di respons JSON | Nilai bisa kosong | Dipakai sebagai pelengkap, bukan variabel utama |
| Keterwakilan populasi | Pengguna Threads tidak mewakili seluruh lulusan baru Indonesia; post terhapus atau dari akun privat tidak terjaring | Temuan bersifat indikatif atas wacana daring | Tidak digeneralisasi sebagai opini nasional |

### C6. Pertimbangan etika

- **Konten publik dan login.** Data yang diambil hanya post yang tampil di hasil pencarian publik,
  tetapi pencarian Threads mensyaratkan login. Ketentuan layanan Meta/Threads tentang pengumpulan
  data otomatis perlu dirujuk langsung dalam laporan.
- **Tidak menembus pembatasan.** Ketika platform menolak akses (login yang diblokir saat mencoba
  X, status 429 di Threads), pengumpulan dihentikan. Pipeline tidak menyamarkan otomatisasi atau
  menembus pembatasan login.
- **Crawling yang sopan.** Jeda acak antar-scroll dan antar-kata kunci, diperlambat setelah
  menerima 429.
- **Minimalisasi data.** Nama tampilan, foto profil, bio, jumlah pengikut, dan media tidak diambil.
  Username dan URL hanya ada di data mentah lokal dan dihapus di dataset bersih.
- **Pseudonimisasi.** Username diganti hash SHA-256 bergaram (`user_hash`); garam disimpan lokal
  dan tidak dipublikasikan. Pseudonimisasi tidak sama dengan anonimisasi, karena teks post publik
  tetap dapat dicari, sehingga kutipan di laporan diparafrasekan.
- **Penyimpanan dan akses.** Cookie sesi, garam, data mentah, dan data bersih tercantum di
  `.gitignore` dan tidak masuk repository publik. Pertukaran data antaranggota dilakukan lewat
  penyimpanan berbagi berakses terbatas.
- **Risiko akun pengumpul.** Akun Threads terhubung ke akun Instagram pribadi pengumpul data;
  pembatasan akibat aktivitas otomatis berisiko berdampak pada akun tersebut.

### C7. Ringkasan

Korpus Threads terdiri dari 2.166 post bersih (2.010 di antaranya dari akun publik) yang
dikumpulkan dari lima kata kunci melalui *scraping* berbasis JSON dengan Playwright, lalu
disaring dengan aturan relevansi dua jalur yang telah divalidasi (presisi 76,7%). Korpus ini
menyediakan teks untuk RQ1 dan RQ2 serta penanda waktu dan fase untuk RQ3. Keterbatasan
utamanya adalah kedalaman pencarian Threads yang tidak menjangkau fase 1 untuk kata kunci
utama; kekurangan ini dikompensasi oleh korpus X dan perbandingan berbasis proporsi.

> **Status korpus X:** menunggu data dari anggota tim yang menjalankan `02_scrape_x.py`.
> Setelah file `data/raw/x_*.jsonl` digabung, jalankan ulang `03_preprocess.py` dan perbarui
> angka di bagian ini.
