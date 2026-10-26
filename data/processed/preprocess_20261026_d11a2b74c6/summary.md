Preprocessing berhasil dijalankan dari raw sampai akhir dan semua deliverable sudah dibuat. Belum ada commit apa pun. Saat ini X punya **4.306 post model-ready**, 60 post menunggu review manusia, dan 891 post dikeluarkan. Semua status ini masih hasil aturan otomatis, karena belum ada satu pun label manusia.

**Angka aktual (snapshot `20261026_d11a2b74c6`)**

| | Raw | Keep | Pending | Exclude |
|---|---|---|---|---|
| X (korpus utama) | 5.257 | 4.306 | 60 | 891 |
| Threads (diproses terpisah) | 6.028 | 3.309 | 1.109 | 1.610 |

- Tidak ada record invalid dan tidak ada ID ganda. Semua ID X berupa string 19 digit. Hitungan tiap tahap cocok dengan snapshot.
- Alasan exclude X: 504 post tidak menyebut program sama sekali (pencarian OR X juga mencocokkan nama/handle akun), 373 iklan CV/joki, dan 14 kode referal.
- Retensi fase 3 hanya 57%, karena 375 dari 387 iklan dan 400 dari 504 post tanpa bukti teks ada di fase 3. Ini noise pengambilan, bukan tanda percakapan menurun.
- Cakupan: 117 dari 117 tanggal pernah diambil, tetapi 50 tanggal pernah kena batas harian. Status "stream habis" juga bukan bukti datanya lengkap.
- Status `text_truncated` tidak diketahui untuk 97,6% record.

**Contoh transformasi (disamarkan)**
- Teks asli: `@akun1 @akun2 saranku tetep daftar MagangHub!!! gak bisa pake SKL….? ☹️ https://t.co/…`
  - `text_minimal`: `[USER] [USER] saranku tetep daftar MagangHub!!! gak bisa pake SKL….? ☹️ [URL]`
  - `text_embedding`: `saranku tetep daftar MagangHub!!! gak bisa pake SKL….? ☹️`
  - `text_topic_repr`: `saranku tetep daftar maganghub gak pake skl`
- `uang saku BELUM cair bangeeettt 😡😡`: negasi, kapital, dan emoji tetap ada di versi sentimen.

**Perubahan dari implementasi lama**
- **`relevansi.py`**: aturan konteks lama tidak pernah berlaku untuk X, karena kueri gabungan OR dibandingkan string persis dengan satu kata kunci. Sekarang relevansi harus punya bukti di teks.
- **`promosi.py` v3**:
  - Satu sinyal saja (angka uang, "katanya", tagar, CV/DM) tidak lagi membuat post ditahan. Contohnya "46 Ribu Lulusan…" dulu ditahan karena angkanya.
  - Permintaan jasa seperti "ada yg buka jasa review cv?" tidak lagi dianggap iklan.
  - Iklan yang dulu lolos kini tertangkap, misalnya "JASA JOKI… CUMA 30K" dan "aku bantu… klik link di bio".
  - Dari 401 post yang dulu ditahan review: 219 kini keep, 160 exclude, 22 pending.
- **Entry point baru**: `preprocess_tk2.py` dan paket `tk2prep/`. Output ditulis ke `data/processed/preprocess_<id>/`, jadi file lama dan launcher kolektor tidak tersentuh.
- **`.gitignore`**: saya menambahkan `data/interim/`. Salinan snapshot di sana masih memuat username dan bisa dibangun ulang dari manifest.

**Tes**: 26 tes lulus, termasuk 19 tes baru untuk semua kasus yang diminta di prompt. Menjalankan ulang pada snapshot yang sama menghasilkan 46 file yang identik byte-per-byte. `test_twscrape_pipeline` dan `test_supervise_twscrape` gagal, tapi itu sudah ada sebelumnya: keduanya butuh paket `twscrape`, yang tidak terpasang di Python 3.13 ini.

**Catatan**
- Repo tidak punya `.venv`, jadi saya memakai Python 3.13 sistem (pandas 3.0).
- File `.salt` baru otomatis dibuat. Akibatnya `user_hash` berbeda dari output lama, tetapi review digabung berdasarkan platform + post_id, jadi tidak terpengaruh.
- Precision, recall, dan kesepakatan antarpeninjau belum bisa dihitung karena belum ada label manusia.

**Langkah berikutnya**
1. Dua peninjau melabeli 40 baris kalibrasi di `sampel_review_x.csv` secara independen.
2. Tinjau 60 post di antrean X, lalu impor dengan `python preprocess_tk2.py import-review <file>` dan jalankan `run` lagi.
3. Putuskan apakah Threads dipakai. Kalau ya, ada 971 post jalur konteks yang perlu ditinjau.
4. Cocokkan batas fase dengan sumber resmi Kemnaker. Saat ini batasnya mengikuti berita yang dikutip TK1.

Cara menjalankan ada di [README_PREPROCESSING.md](maganghub-pipeline/README_PREPROCESSING.md). Bahan C2, C4, C5, dan C6 beserta tabel keputusan → RQ → sumber ada di [CATATAN_METODE_TK2.md](maganghub-pipeline/CATATAN_METODE_TK2.md). Laporan angka lengkap ada di [LAPORAN_KUALITAS.md](maganghub-pipeline/data/processed/preprocess_20261026_d11a2b74c6/LAPORAN_KUALITAS.md).