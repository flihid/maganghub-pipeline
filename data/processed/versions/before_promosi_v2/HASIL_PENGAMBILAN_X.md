# Hasil pengambilan X

Diperbarui: 2026-10-25T22:59:05+07:00

- Unggahan mentah unik: 242.
- Kandidat sesudah pembersihan otomatis: 187.
- Interval diperiksa sampai kondisi berhenti yang tercatat: 0/17.
- Teks yang diketahui terpotong dalam data mentah: 9.
- Rentang penelitian: 1 Juli sampai 25 Oktober 2026; batas akhir eksklusif 26 Oktober.
- Metode: lihat collector pada record; DOM browser dan/atau twscrape (pencarian internal X, bukan API resmi berbayar), tab Latest.
- Lima kata kunci digabung dengan OR per interval; bukan lima pencarian terpisah.
- Koreksi filter bahasa: lang:id pada pengambilan awal keliru; uji pembanding membuktikan lang:in mengembalikan unggahan Indonesia. Hasil kosong dengan filter lama tidak dihitung sebagai interval selesai.
- Ada pengambilan tambahan kata kunci maganghub untuk seluruh periode. Parameter aktual tercatat di setiap record.

## Batas interpretasi

- empty_search berarti halaman pencarian menampilkan tidak ada hasil, bukan bukti tidak ada percakapan.
- exhausted_visible_results berarti enam putaran tanpa ID baru pada hasil yang terlihat, bukan sensus X.
- Semua kandidat masih memerlukan pemeriksaan relevansi, privasi, serta jenis akun secara manual.
- Daftar jenis akun bawaan tidak mencakup semua akun organisasi; label publik perlu diperiksa.
- Sampel tidak dapat dipakai membandingkan fase yang tidak memiliki data.
- Sesi twscrape dimasukkan pengguna secara lokal dan tidak dimasukkan ke dataset atau Git.
- Status twscrape berakhiran partial/unverified tidak dihitung sebagai bukti cakupan lengkap.

## Berkas

- Data mentah: ../raw/x_*.jsonl
- Log pengambilan: ../raw/browser_collection_log.jsonl
- Cakupan: cakupan_interval_x.csv
- Kandidat analisis: maganghub_bersih.csv
- Penyaringan: log_preprocessing.csv
- Tinjauan manusia: review_manual_x.csv (keputusan belum diisi otomatis)
