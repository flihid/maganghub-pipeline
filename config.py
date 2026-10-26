"""
Konfigurasi pipeline pengumpulan data MagangHub.

Semua parameter yang menentukan DATA APA yang dikumpulkan ada di file ini,
supaya pipeline bisa diulang (reproducible) cukup dengan membaca satu file.
Setiap nilai di sini harus sama dengan yang ditulis di laporan bagian C1 dan C3.
"""

# ---------------------------------------------------------------------------
# 1. KATA KUNCI (jangkar wajib)
# ---------------------------------------------------------------------------
# Sesuai TK1 bagian 1.6: hanya nama program yang dipakai sebagai kueri.
# Istilah isu (uang saku, full-time, eksploitasi, ...) TIDAK dipakai sebagai
# kueri berdiri sendiri karena akan menjaring unggahan di luar konteks program.
# Tanda kutip = frasa persis di pencarian X.
KATA_KUNCI = [
    "maganghub",
    '"magang hub"',
    '"magang nasional"',
    '"magang kemnaker"',
    '"pemagangan nasional"',
]

# Aturan relevansi dua jalur (dipakai di cek_cakupan.py dan 03_preprocess.py):
#
#  Jalur 1 - "eksplisit": teks menyebut nama program (POLA_RELEVAN).
#
#  Jalur 2 - "konteks"  : teks tidak menyebut nama program, TETAPI
#                         (a) post itu terjaring oleh salah satu KUERI_JANGKAR_KONTEKS, dan
#                         (b) teksnya memuat istilah yang khas program (POLA_KONTEKS).
#     Alasannya: Threads menampilkan post yang ditandai topik MagangHub walaupun kata
#     "maganghub" tidak ada di teksnya, misalnya "batch 2 siapa yang mau gajian" atau
#     "mentor lupa acc absen, apakah uang sakunya dipotong". Pemeriksaan manual atas
#     10 sampel post yang dibuang menunjukkan sebagian besar sebenarnya membahas program.
#     Jalur ini TIDAK berlaku untuk kata kunci generik ("magang nasional",
#     "pemagangan nasional") karena hasil pencariannya tidak spesifik ke program.
POLA_RELEVAN = (
    r"magang\s*hub|magang\s+nasional|magang\s+kemnaker|"
    r"magang\s+kemenaker|pemagangan\s+nasional"
)
KUERI_JANGKAR_KONTEKS = ["maganghub", "magang hub", "magang kemnaker"]
POLA_KONTEKS = (
    r"batch\s*\d|uang\s*saku|mentor|absen|presensi|pencairan|\bcair\b|"
    r"pemagang|peserta\s+magang|kemnaker|kemenaker|laporan\s+harian|logbook"
)

# ---------------------------------------------------------------------------
# 2. JENDELA WAKTU (mengikuti TK1 bagian 1.6, Batch 2 Angkatan II)
# ---------------------------------------------------------------------------
# Format (since, until). PENTING: "until" di pencarian X bersifat EKSKLUSIF,
# jadi until 2026-09-01 berarti data sampai 31 Agustus 2026.
JENDELA_WAKTU = {
    "fase1_pengumuman": ("2026-07-01", "2026-09-01"),  # Juli - 31 Agustus
    "fase2_seleksi":    ("2026-09-01", "2026-09-21"),  # 1 - 20 September
    "fase3_penempatan": ("2026-09-21", "2026-10-26"),  # 21 September - 25 Oktober
}

# Setiap fase dipecah per N hari. Rentang pendek membuat X mengembalikan
# lebih banyak hasil dibanding satu rentang panjang.
PANJANG_SUBJENDELA_HARI = 7

# Verified against X web search on 25 Oct 2026: Indonesian posts use `in`.
# `lang:id` returned no results for a week where `lang:in` returned posts.
BAHASA = "in"

# ---------------------------------------------------------------------------
# 3. BATAS & KESOPANAN CRAWLING (rate limiting)
# ---------------------------------------------------------------------------
MAKS_POST_PER_KUERI = 400          # per kombinasi (kata kunci x subjendela)
MAKS_SCROLL_TANPA_BARU = 6         # berhenti jika N scroll berturut-turut tanpa post baru
JEDA_SCROLL_DETIK = (5.0, 9.0)     # jeda acak antar-scroll (diperlambat setelah kena 429 di Threads)
JEDA_ANTAR_KUERI_DETIK = (25, 50)  # jeda acak antar-kueri
TIMEOUT_MUAT_MS = 25_000

# ---------------------------------------------------------------------------
# 4. LOKASI FILE
# ---------------------------------------------------------------------------
FILE_SESI = "sesi_x.json"                       # cookie login - JANGAN di-commit
DIR_RAW = "data/raw"
DIR_PROCESSED = "data/processed"
FILE_LEKSIKON = "data/lexicon/colloquial-indonesian-lexicon.csv"
FILE_SALT = ".salt"                              # untuk hashing username - JANGAN di-commit

# ---------------------------------------------------------------------------
# 5. KLASIFIKASI AKUN (diisi/diperiksa manual oleh tim)
# ---------------------------------------------------------------------------
# Akun resmi dan media TIDAK dibuang, tetapi ditandai di kolom `jenis_akun`,
# supaya analisis opini publik bisa memisahkan pernyataan resmi dan berita.
# Periksa ulang handle ini di X sebelum dipakai; tulis huruf kecil tanpa '@'.
AKUN_RESMI = [
    # X
    "kemnakerri",
    # Threads (diperiksa dari 15 akun paling aktif di data mentah)
    "kemnaker", "maganghub.kemnaker",
]
AKUN_MEDIA = [
    # X
    "kompascom", "detikcom", "cnnindonesia", "tempodotco",
    "cnbcindonesia", "kumparan", "liputan6dotcom", "tribunnews",
    # Threads: media/berita
    "viralyn.daily", "mcinews.id", "titik_temu.news", "satu_meja.id",
    # Threads: akun informasi karier/lowongan (informasi, bukan opini pribadi)
    "temankarirofficial", "internship.career",
]
# Akun otomatis yang DIBUANG karena isinya bukan ekspresi manusia,
# misalnya jawaban asisten AI yang dipanggil pengguna di kolom balasan.
AKUN_DIBUANG = [
    "meta.ai",
]

# ---------------------------------------------------------------------------
# 6. HEURISTIK SPAM / BOT
# ---------------------------------------------------------------------------
# Legacy reference only. Active preprocessing uses explainable rules in promosi.py.
POLA_SPAM = (
    r"link\s*di\s*bio|klik\s*link|cek\s*bio|dm\s*(?:aja|untuk|utk)|"
    r"jasa\s+(?:joki|pembuatan|daftar)|joki\s+(?:cv|maganghub|magang)|"
    r"open\s*(?:order|jasa)|promo\b|diskon\b|wa\.me|bit\.ly|"
    r"slot\s*gacor|judi|togel"
)
MAKS_HASHTAG = 5        # lebih dari ini dianggap spam tagar
MIN_KATA = 4            # hanya menandai teks pendek untuk review; tidak otomatis dibuang

# Kata yang muncul di hampir semua dokumen karena memang menjadi kueri.
# Hanya dibuang dari kolom `teks_token`, tidak dari `teks_model`.
STOPWORD_DOMAIN = ["maganghub", "hub"]

# ---------------------------------------------------------------------------
# 7. THREADS (korpus pelengkap)
# ---------------------------------------------------------------------------
FILE_SESI_THREADS = "sesi_threads.json"          # cookie login - JANGAN di-commit

# Pencarian Threads tidak mendukung tanda kutip maupun filter tanggal seperti X,
# jadi kata kunci ditulis biasa dan penyaringan tanggal dilakukan di preprocessing.
KATA_KUNCI_THREADS = [
    "maganghub",
    "magang hub",
    "magang nasional",
    "magang kemnaker",
    "pemagangan nasional",
]

# URL pencarian tab "Terbaru". CARA MEMASTIKAN: buka threads.com di browser biasa,
# cari "maganghub", klik tab Terbaru/Recent, lalu salin URL dari address bar.
# Jika berbeda dengan di bawah, tempel di sini dan ganti kata kuncinya dengan {q}.
URL_PENCARIAN_THREADS = "https://www.threads.com/search?q={q}&serp_type=default&filter=recent"

MAKS_POST_THREADS_PER_KUERI = 3000
# Hasil diurutkan dari yang terbaru. Scroll dihentikan jika N putaran berturut-turut
# hanya berisi post yang lebih tua dari awal jendela penelitian.
MAKS_SCROLL_TERLALU_LAMA = 3
