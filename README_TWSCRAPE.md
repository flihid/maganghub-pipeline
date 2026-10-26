# Koleksi X mandiri untuk TK2

Mesin pengambil data memakai [twscrape](https://github.com/vladkens/twscrape), dipin pada 0.20.1. `twscrape_pipeline.py` hanya adapter untuk kueri penelitian, penyimpanan, batas pilot, dan checkpoint proyek ini. Paket memakai endpoint internal X dengan sesi akun, bukan API resmi berbayar. Gratis untuk dijalankan lokal, tetapi keberhasilan dan kelengkapan pencarian tetap bergantung pada X. Pengujian offline tidak membuktikan akses akun berhasil.

## Jalankan

Klik dua kali `START_TWSCRAPE.cmd`. Saat pertama kali, isi nilai cookie `auth_token` dan `ct0` dari akun X milikmu yang sudah login di Brave: F12 > Application > Cookies > https://x.com > kolom Value. Masukkan hanya di terminal lokal yang dibuka launcher, bukan di chat. Input tersembunyi. Jika muncul peringatan bahwa input tidak dapat disembunyikan, batalkan dengan Ctrl+C dan gunakan terminal Windows biasa.

Cookie memberi akses sesi akun. Database `.twscrape/accounts.db` hanya disimpan lokal, dikecualikan dari Git; jangan bagikan database atau folder sesi. Telemetry SDK dinonaktifkan oleh adapter. Tidak ada pembelian akun, rotasi akun, atau proxy.

Launcher mengambil **maksimal 50 post baru per fase (150 total)**, lalu menjalankan preprocessing dan audit bila kolektor selesai tanpa galat. Komputer harus tetap menyala dan terhubung internet. Tidak perlu membuka chat selama berjalan. Ctrl+C menghentikan proses; klik launcher lagi untuk melanjutkan. Jangan menjalankan dua kolektor sekaligus.

Alternatif PowerShell dari folder proyek:

```powershell
.\.venv\Scripts\python.exe twscrape_pipeline.py plan
.\.venv\Scripts\python.exe twscrape_pipeline.py setup
.\.venv\Scripts\python.exe twscrape_pipeline.py collect --mode pilot
```

`setup` juga memperbarui sesi kedaluwarsa. Jika environment perlu dibuat ulang:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-twscrape.txt
```

## Setelah pilot diperiksa

### Pengawas lokal tanpa pemantauan chat

Jalankan `PENGAWAS_TWSCRAPE.cmd` untuk mengawasi kolektor full yang sudah aktif atau menjalankan full jika belum ada checkpoint. Tidak perlu model AI atau polling dari chat. Pengawas memeriksa proses setiap 10 detik, dan tidak memulai salinan kedua jika proses yang tercatat masih aktif.

Jika kolektor berhenti dengan `NoAccountError`/peringatan rate limit dan satu sesi akun masih aktif, pengawas menunggu paling sedikit 15 menit serta menghormati waktu lock SDK yang lebih lama. Maksimal tiga kali resume per sesi pengawas. Sesi tidak aktif, lock lebih dari satu jam, timeout/galat lain, proses yang tidak bisa diperiksa, dan run selesai tidak dicoba ulang otomatis. Tidak ada penghapusan lock/rotasi akun. Kredensial tidak dikirim ke model; metadata ketersediaan lokal yang diperiksa hanya `active` dan `locks`.

Saat meluncurkan kolektor sendiri, pengawas juga menjalankan preprocessing/audit setelah child berhenti. Bila mengambil alih kolektor dari launcher lama, launcher lama tetap mengurus preprocessing. Komputer harus menyala dan tidak sleep; menutup chat tidak diperlukan. Status pengawas tersimpan lokal di `.twscrape/supervisor_status.json`. Hindari menjalankan launcher lain bersamaan. Ctrl+C pada jendela pengawas menghentikan pengawas; bila child aktif di konsol yang sama, child juga menerima interupsi dan menyimpan progres.

### Lokasi data mentah

`data/raw/x_fase1_pengumuman.jsonl`, `x_fase2_seleksi.jsonl`, dan `x_fase3_penempatan.jsonl` adalah observasi paling mentah yang disimpan proyek (satu JSON per baris). Teks belum dibersihkan/disaring promosi, tetapi SDK dan adapter sudah mengekstrak field, menyaring tanggal dan repost murni, serta membuang ID berulang. Respons HTTP/GraphQL lengkap tidak disimpan. Kueri aktual dan status pengambilan ada pada checkpoint/log di folder yang sama. CSV analisis berasal dari preprocessing terhadap file JSONL tersebut.

Untuk melanjutkan ke seluruh rentang, klik dua kali **`LANJUT_TWSCRAPE.cmd`**. Ini berbeda dari launcher pilot: tidak berhenti pada 50 post per fase. Pengambilan mendahulukan tanggal yang belum dicoba, menyebarkan urutan tanggal ke bagian awal/tengah/akhir fase, dan tetap bergiliran antar fase. Tanggal yang sudah dicoba di pilot tetap akan dicoba lagi di bagian akhir pass full. Menjalankan launcher yang sama melanjutkan checkpoint full tanpa menulis ulang ID yang sudah ada. Jangan menjalankan dua launcher bersamaan.

Jika muncul `NoAccountError`, akun belum tersedia untuk pencarian, termasuk kemungkinan cooldown. Tunggu sebelum mencoba lagi; jangan menghapus database/reset lock untuk memaksa akses. `setup` ulang hanya bila kolektor menyatakan sesi tidak aktif atau sesi memang kedaluwarsa. Launcher full tetap memperbarui preprocessing dan audit dari hasil parsial.

SDK sekarang menunggu ketersediaan akun hingga 900 detik per pengambilan akun, dengan batas keseluruhan kueri default 1.200 detik. Akun tidak aktif tetap gagal; pembatasan tidak dihapus. Selama menunggu, jumlah post bisa tidak berubah. Pemantau memakai PID dan waktu mulai dari checkpoint, tanpa WMI/CIM. Tutup lalu buka kembali pemantau setelah memperbarui script; pesan gagal memeriksa proses berarti status tidak diketahui, bukan bukti proses berhenti.

Volume harian hasil pilot tidak mengukur volume percakapan sebenarnya: hari yang belum diambil tidak muncul pada CSV; hari yang terkena batas bisa kurang terwakili. Utamakan cakupan semua tanggal, lalu tinjau hari yang menyentuh batas. Tidak perlu memaksa jumlah post sama setiap hari atau membuang hari ramai untuk meratakan grafik.

Periksa hasil tiap fase, teks lengkap, iklan, dan relevansi. Jika akses berhasil dan hasil pilot memadai, ambil lebih banyak dengan:

```powershell
.\.venv\Scripts\python.exe twscrape_pipeline.py collect --mode full --per-day 300 --max-raw 10000
.\.venv\Scripts\python.exe 03_preprocess.py
.\.venv\Scripts\python.exe 04_audit_collection.py
```

Target kerja 3.000–5.000 post bersih bukan jaminan volume yang tersedia. Batas 10.000 adalah jumlah ID mentah unik seluruh koleksi X termasuk data browser lama. Batas harian full sekarang 300 ID unik layak dalam tanggal WIB, termasuk ID yang sudah tersimpan. Juga ada batas 30 halaman per tanggal. Ini batas maksimum, bukan jumlah yang pasti tersedia atau lolos pembersihan. Jangan menyebut output otomatis sebagai sentimen publik tervalidasi sebelum review.

## Desain dan keterbatasan

- Lima variasi kata kunci digabung OR, `lang:in`, tab Latest. Top dapat dipakai sebagai sampel pembanding terpisah; menggabungkannya tanpa mencatat sumber menambah bias popularitas.
- Ada 117 jendela harian dalam tiga fase sesuai `config.py`, dijalankan bergiliran antar fase. Pilot berjalan dari hari terbaru; full menyebarkan tanggal dan memprioritaskan tanggal yang sebelumnya menyentuh batas, kemudian tanggal belum dicoba. Ini sampel pencarian, bukan sampel acak atau representatif. Tahun dan batas fase masih perlu dicocokkan dengan rancangan penelitian tim.
- Adapter v3 memakai `since_time`/`until_time` Unix seconds untuk batas tepat 00:00–00:00 WIB. Timestamp tetap diperiksa lokal. Format operator mengacu pada [referensi operator pencarian](https://github.com/igorbrigadir/twitter-advanced-search#readme), lalu diuji langsung pada akun penelitian. Versi lama memperlebar kueri dua tanggal UTC dan membatasi sekitar 60 hasil SDK, sehingga banyak hasil di luar hari sasaran menghabiskan kuota. Batas itu sudah diganti: SDK dipaginasi tanpa limit hitungan mentah, sampai stream habis, 300 ID layak unik, 30 halaman, timeout, atau kendala akses.
- Respons SDK bisa memuat tweet konteks/kutipan di luar tanggal. Log memisahkan `seen`, `eligible_unique`, `duplicates_existing`, `excluded_outside_window`, `excluded_retweet`, `excluded_empty_text`, dan `added`. `+N` berarti ID baru yang ditulis, bukan jumlah seluruh hasil SDK. Setelan tanggal dan basis kuota baru membuat checkpoint baru; data serta checkpoint v2 tetap ada, ID global tidak diduplikasi. Seluruh hari dapat diperiksa ulang karena hasil lama belum membuktikan kelengkapan.
- Data langsung ditambahkan ke `data/raw/x_<fase>.jsonl`; ID yang sudah tersimpan tidak ditulis lagi. File ini observasi yang dinormalisasi dari SDK, bukan salinan lengkap respons HTTP. Repost murni dikecualikan; reply dan quote dipertahankan.
- Checkpoint `data/raw/twscrape_state_*.json` menyimpan konfigurasi, versi, status, serta jumlah per fase. Log per kueri di `browser_collection_log.jsonl` memuat kueri aktual, waktu, halaman, jumlah, dan galat tanpa isi kredensial.
- Jeda halaman minimum 5 detik, antar kueri minimum 25 detik (default 35). Satu sesi akun saja. Galat, timeout, dan peringatan SDK menghentikan run untuk diperiksa. Tidak mengulang tanpa batas.
- `no_rows_unverified` berarti SDK tidak mengembalikan baris, bukan bukti tidak ada percakapan. `stream_ended_unverified` berarti stream SDK selesai, bukan sensus. `eligible_day_limit_partial`/`page_budget_partial`/`quota_partial` berarti pengambilan dibatasi (`daily_limit_partial` adalah status versi lama). Hari yang diproses sekali dilewati saat resume pada checkpoint yang sama; hari yang masih menyentuh batas perlu dipecah lagi/diambil ulang dalam pass lanjutan. Berhasil menjalankan semua job tidak menjamin semua tweet ditemukan.
- Preprocessing menyimpan versi minimal yang mempertahankan emoji, negasi, kapitalisasi, dan intensitas, di samping versi normalisasi/token. Teks identik dengan ID berbeda dan teks pendek ditandai untuk review; tidak langsung dibuang. Heuristik spam yang ada masih dapat melewatkan iklan CV/joki atau membuang kritik yang menyebut promosi. Review diperlukan.
- Untuk pembagian train/test nanti, kelompokkan post duplikat/dekat, repost, atau penulis sesuai tujuan evaluasi agar tidak bocor antar split. Fase tanpa data tidak dapat dipakai menyimpulkan perubahan sentimen.

## Dasar materi kuliah

### Penyaringan promosi (promosi_v2)

`promosi.py` menggabungkan penawaran layanan dengan sinyal kontak, paket CV, harga, dan bukti jual. Penyebutan CV/joki/DM saja tidak cukup untuk otomatis mengecualikan post. Permintaan bantuan, kritik, kutipan, dan bantuan gratis yang ambigu ditahan untuk review. Ini heuristik, belum pengukuran precision/recall dengan label independen; contoh yang dilaporkan pengguna dipakai untuk memperbaiki aturan dan tes regresi.

- `maganghub_bersih.csv`: hanya status `keep`, tanpa indikasi promosi menurut aturan. Tetap perlu review relevansi/sentimen/privasi; nama file bukan jaminan label bersih manual.
- `maganghub_kandidat.csv`: seluruh post yang tidak otomatis dikecualikan, termasuk yang menunggu review.
- `review_promosi.csv`: kasus ambigu, jangan dianggap spam secara otomatis. Kritik yang sah bisa dikembalikan ke korpus analisis setelah peninjauan.
- `audit_penyaringan_promosi.csv`: keputusan exclude/review, alasan, sinyal, versi aturan, dan teks minimal; raw tidak dihapus.

Volume harian dan ringkasan fase mengacu pada `maganghub_bersih.csv`, sehingga belum menghitung kasus yang ditahan. Simpan hasil review terpisah; file audit/review promosi ini merupakan keluaran script yang dibuat ulang saat preprocessing. Hasil sebelum perubahan aturan pertama disimpan di `data/processed/versions/before_promosi_v2/`.

Keputusan ini mengacu pada materi lokal di `../materi/`:

| Materi | Halaman | Penerapan |
|---|---|---|
| 02 Data Collection Using APIs | 59, 61 | Laporkan bias kata kunci, bahasa, waktu, popularitas; checkpoint dan resume. |
| 03 Web Scraping for Data Collection | 13–15, 19 | Batasi data pribadi, jeda permintaan, berhenti pada galat/pembatasan, dokumentasikan metode. |
| 04 Data Storage and Reproducible Pipeline | 24–26, 31–32 | Pisahkan mentah/hasil, simpan provenance, konfigurasi dan versi; langkah pengolahan lewat script. |
| 05 Social Media Data Quality | 9, 15, 22, 24–26 | Nol berbeda dari missing; perbaiki kegagalan koleksi; teks sama tidak selalu duplikat; audit sebelum analisis. |
| 06 Social Media Data Preprocessing | 7–15, 29–38 | Pertahankan informasi sentimen, sediakan baseline minimal, hindari leakage. |

Materi tidak menyatakan twscrape sebagai tool wajib atau terbaik. Pemilihan paket adalah keputusan implementasi proyek; perlu pilot live untuk menilai kecocokannya.

Uji offline: `.\.venv\Scripts\python.exe -m unittest test_twscrape_pipeline.py`.
