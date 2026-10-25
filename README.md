# MagangHub Data Collection Pipeline

Pipeline pengumpulan dan *preprocessing* data media sosial X dan Threads untuk penelitian
**"Analisis Pro Kontra Publik terhadap Program Magang Nasional MagangHub pada Media Sosial X"**
(Tugas Kelompok 2, CSIE604284 Analitika Media Sosial, Fasilkom UI, Gasal 2026/2027).

Pipeline ini mengumpulkan unggahan publik berbahasa Indonesia yang menyebut Program Magang
Nasional/MagangHub dalam tiga jendela waktu penyelenggaraan program, dari X (korpus utama) dan
Threads (korpus pelengkap), lalu membersihkannya menjadi satu dataset siap analisis untuk
pemodelan topik (BERTopic) dan klasifikasi sentimen (IndoBERT).

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
7. Tandai jenis akun (resmi/media/publik) — tidak dibuang
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
