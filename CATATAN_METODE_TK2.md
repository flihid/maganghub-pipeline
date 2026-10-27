# Catatan metode preprocessing TK2

Bahan internal tim untuk laporan TK2. Dokumen ini tidak menggantikan draf laporan rekan. Angka
berasal dari run `preprocess_20261026_d11a2b74c6` (snapshot 26 Okt 2026 14:43 WIB). Jika snapshot
berubah, ambil angka terbaru dari `LAPORAN_KUALITAS.md`. Belum ada hasil sentimen/topik; tahap ini
hanya persiapan data.

Status sumber:
- **[Tugas]** persyaratan dokumen TK2.
- **[Materi]** rekomendasi slide kuliah.
- **[Implementasi]** pilihan tim yang belum dievaluasi sebagai "paling optimal".

## 1. Pertanyaan penelitian (TK1 §1.5) dan kebutuhan data

| RQ | Isi (TK1) | Yang dibutuhkan dari preprocessing |
|---|---|---|
| RQ1 | Topik utama dukungan/keberatan publik terhadap MagangHub di X, termasuk klaim substitusi tenaga kerja, eksploitasi lulusan, dan menyusutnya pekerjaan penuh waktu | `text_embedding` (konteks utuh) + `text_topic_repr`/vectorizer untuk kata topik. Teks berulang ditandai agar template iklan/pengumuman tidak menjadi klaster semu |
| RQ2 | Distribusi sentimen (positif/negatif/netral) per topik; klaster dengan resistensi paling tajam | `text_sentiment` yang mempertahankan negasi, emoji, dan intensitas. Iklan dikeluarkan, sedangkan kritik/keluhan tetap ada |
| RQ3 | Perubahan komposisi topik dan sentimen antarperiode; puncak resistensi | Fase dari waktu WIB aktual, distribusi per tanggal/fase, laporan cakupan dan pergeseran distribusi akibat filter |

Catatan penting:
- Di TK1, RQ2 dioperasionalkan sebagai "dukungan, keberatan, netral", padahal yang diukur polaritas
  sentimen. Sentimen dan stance terhadap program **berbeda**: keluhan "uang saku telat cair" bernada
  negatif tetapi belum tentu menolak program. Panduan label menyediakan `stance_manual` dan
  `aspek_manual` terpisah dari `sentimen_manual` untuk anotasi lanjutan.
- Klaim substitusi tenaga kerja dalam data adalah **persepsi** publik, bukan bukti kausal substitusi.

## 2. Keputusan → RQ → alasan → bukti → sumber

| # | Keputusan | RQ | Alasan | Bukti dari data/run | Sumber |
|---|---|---|---|---|---|
| 1 | Mulai dari raw JSONL, bekukan snapshot (batas byte + SHA-256), raw tidak diubah | semua | Reproducibility, pemisahan raw/interim/processed, provenance | 8 file, 11.285 record, sisa tak lengkap 0 byte; rerun pada snapshot sama menghasilkan 46 file identik | [Materi] 04 hlm. 24–26, 31–32 |
| 2 | Pisah JSONL pada `b"\n"` saja | semua | `splitlines()` ikut memecah U+2028/U+2029 | 48 teks X memuat U+2028/U+2029 | [Implementasi]; tes `test_u2028_tidak_memecah_record` |
| 3 | ID sebagai string; ID float dikarantina | semua | ID X 19 digit rusak jika lewat float/Excel | 5.257/5.257 ID X berupa string 19 digit; tidak ada ID duplikat | [Materi] 05 hlm. 24–26 (validasi record) |
| 4 | Missing ≠ 0; engagement kosong tetap `null` | RQ3 (deskriptif) | Nol berarti "tidak ada like", missing berarti "tidak dikumpulkan" | `n_quote`, `conversation_id`, dan `content_type` missing pada 129 record kolektor browser lama; `n_quote` bernilai 0 pada 3.574 record | [Materi] 05 hlm. 9 |
| 5 | `text_truncated=None` = tidak diketahui | semua | twscrape tidak memberi flag; tidak boleh dianggap lengkap | unknown 5.128, false 120, true 9 (X) | [Implementasi]; 05 hlm. 15 (masalah koleksi tidak diselesaikan cleaning) |
| 6 | Relevansi wajib punya bukti teks; hasil OR tidak dianggap relevan otomatis | RQ1–3 | Kueri gabungan OR tidak bisa diatribusikan ke satu istilah. Pencarian X juga mencocokkan nama/handle, kutipan, dan tautan yang tidak tersimpan | 504 post X tanpa nama program/istilah program (mis. curhat umum). 400 di antaranya dari tanggal 18–25 Okt (pengambilan ulang per-day 600). 21 post konteks OR dikirim ke review | [Tugas] C1 (kriteria inklusi/eksklusi), C5 (noise); audit `relevansi.py` |
| 7 | Inklusi tidak mensyaratkan nada negatif | RQ2 | Opini positif/netral, pertanyaan, dan berita adalah bagian distribusi | Aturan hanya memeriksa rujukan ke program | TK1 RQ2 |
| 8 | Promosi: exclude hanya bila ada penawaran + layanan + sinyal komersial | RQ1–2 | Kata CV/joki/DM, "katanya", angka uang, dan tagar juga muncul pada kritik atau diskusi uang saku | Dari 401 post yang dulu ditahan v2: 219 kini keep, 160 exclude, 22 pending. Contoh false positive v2: "46 Ribu Lulusan…" (angka), permintaan "yg pernah make jasa bikin CV" | [Implementasi]; 05 hlm. 22 |
| 9 | Teks berulang/near-duplicate ditandai, tidak dihapus | RQ1–2 | Teks sama dari ID berbeda bukan duplikasi observasi. Definisi near-dup mempertahankan negasi/emoji | X: 287 post dalam 47 grup teks identik (maks. 85 salinan satu template iklan); 344 post dalam 44 grup near-dup | [Materi] 05 hlm. 22 |
| 10 | Bot tidak disimpulkan dari pengulangan/frekuensi | RQ1–2 | Pengulangan bukan bukti otomatisasi | Hanya flag; `akun_otomatis` terbatas pada `meta.ai` (36 post Threads) | [Implementasi] |
| 11 | Versi teks berbeda per tujuan | RQ1, RQ2 | Noise bergantung tugas; transformer butuh konteks; stopword/stemming dapat menghapus negasi | Lihat README tabel versi teks | [Materi] 06 hlm. 7–15, 29–32 |
| 12 | Tanpa stemming dan stopword removal pada teks sentimen/embedding | RQ1, RQ2 | Negasi dan intensifier membawa polaritas; embedding perlu kalimat utuh | Contoh: "BELUM cair bangeeettt 😡😡" dipertahankan | [Materi] 06 hlm. 13–14, 30; BERTopic tips "Removing stop words" (buang stopword di vectorizer, bukan sebelum embedding) |
| 13 | Normalisasi slang hanya varian opsional dan reversible | RQ2 | Normalisasi menghilangkan intensitas. Kata ambigu (`u`, `sm`, `kl`) dan code-mixing rawan salah | 22 entri tak ambigu. Leksikon Colloquial Indonesian (15.006 entri) tidak diterapkan | [Materi] 06 hlm. 21–24; kamus-alay (Salsabila dkk., IALP 2018) |
| 14 | Masking `[URL]`/`[USER]`/`[EMAIL]`/`[PHONE]`; username/URL tidak keluar | C6 | Minimalisasi data; placeholder mempertahankan fakta adanya URL/mention | 33 post X memuat indikasi PII di teks asli (email/telepon/16 digit/"nama saya") | [Materi] 06 hlm. 20; [Tugas] C6 |
| 15 | Fase dihitung ulang dari waktu WIB, interval `[awal, akhir)` | RQ3 | Tahun/fase cocok dengan TK1 (2026), tetapi batas berasal dari berita (TK1 ref. [24]), bukan tanggal resmi terverifikasi | Fase1 2.473, fase2 936, fase3 1.848 post unik X; 0 beda dengan `fase` tulisan kolektor | TK1 §1.6; asumsi dicatat di laporan |
| 16 | Cakupan dibangun dari log/checkpoint twscrape per tanggal | RQ3, C5 | Audit lama memakai interval browser sehingga menampilkan 0/17 | 117/117 tanggal pernah dicoba; status terakhir: 114 stream habis (unverified), 3 kena batas; 50 tanggal pernah kena batas | [Materi] 05 hlm. 15, 24–26 |
| 17 | Keputusan manusia append-only, merge `(platform, post_id)` | semua | Rerun tidak boleh menghapus anotasi; label agent bukan validasi | 0 keputusan manusia saat ini | [Implementasi] |
| 18 | `split_group_id` disiapkan, belum ada split | RQ2 (bila fine-tune) | Duplikat/near-dup/penulis yang sama di train & test membuat evaluasi terlalu mudah | 437 post X berada di grup berukuran > 1 | [Materi] 06 hlm. 35–37; scikit-learn "Common pitfalls: data leakage" |
| 19 | Threads diproses terpisah, tidak dicampur dengan X | semua | X korpus utama; Threads berbeda mekanisme pencarian, tanpa filter tanggal/bahasa | Threads: 6.028 raw, 139 di luar jendela, 1.109 pending | Prompt kerja; [Tugas] C5 (cakupan platform) |
| 20 | Threads hanya memakai post yang menyebut nama program; jalur konteks di-exclude (`config.RELEVANSI_KONTEKS_DIABAIKAN`) | RQ1–3 | Pencarian Threads longgar: 2.615 dari 6.028 post tidak menyebut nama program. Sampel acak 20 post konteks berisi campuran MagangHub dan magang umum (tips interview, magang Jepang, BPJS); bukti terbanyak hanya "magang" (367) dan "kemnaker" (251). Review 1.089 post tidak sebanding untuk korpus pelengkap. Keputusan reviewer manusia tetap menang | Snapshot `20261026_3067bfd95e`: 1.089 post `relevansi_konteks_tidak_dipakai` (973 kueri jangkar + 116 kueri generik); keep tetap 3.309; pending Threads 1.109 → 22 (promosi). X tidak berubah | Keputusan tim 26 Okt 2026; [Tugas] C1, C5 |
| 21 | `promosi_v4`: exclude pengumuman lowongan mitra, iklan jasa titipan, dan ajakan webinar/pelatihan | RQ1–2 | Pengumuman lowongan ("X membuka kesempatan magang melalui MagangHub … kirim lamaran melalui …") relevan dengan program tetapi bukan opini publik dan berbentuk template siaran yang dapat membentuk klaster semu. Syarat: suara pengumuman + instruksi melamar/detail lowongan; klausa relatif/pertanyaan ("yang buka lowongan", "ga open recruitment", "ada ga rekomendasi") dikecualikan | Dari keep sebelumnya: X −20 (18 lowongan, 2 iklan titipan), Threads −126 (122 lowongan, 4 webinar/pelatihan). Pemeriksaan sampel saat pengembangan: ±90–95% tepat; kasus perbatasan berupa judul berita/info program. Belum divalidasi label manusia; tercakup sampel review berikutnya | Keputusan tim 26 Okt 2026; [Implementasi]; tes `test_pengumuman_lowongan_mitra`, `test_iklan_titipan_order_dan_acara` |

IndoBERT dasar (IndoNLU) adalah model bahasa pralatih, bukan classifier sentimen siap pakai. Pemilihan
atau fine-tuning model sentimen berada di luar tahap ini.

## 3. Angka run (X, korpus utama)

- Raw 5.257 → karantina 0 → unik 5.257 → **keep 4.306**, pending 60, exclude 891.
  - Exclude: tanpa bukti teks program 504; penawaran jasa/joki/CV 373; kode referal 14.
  - Pending: konteks OR 21; indikasi promosi ambigu 39.
- Model-ready tanpa akun resmi/media terdaftar: 4.205. Satu wakil per teks identik: 4.277.
- Retensi per fase: fase1 95,5%, fase2 96,1%, fase3 56,6%. Proporsi fase3 turun dari 35,2% menjadi
  24,3% korpus model-ready. Penyebabnya: 375 dari 387 eksklusi promosi dan 400 dari 504 post
  tanpa bukti teks berada di fase3. **Jangan** membaca penurunan ini sebagai turunnya percakapan.
- Dibanding `maganghub_bersih.csv` lama (4.073 post): 4.062 tetap keep, 10 menjadi pending, 1 exclude.
  Ada 244 keep baru (219 dari antrean review promosi lama + 25 dari raw yang lebih baru).

Threads (pelengkap, terpisah): raw 6.028 → keep 3.309, pending 1.109 (971 konteks kueri jangkar
tanpa nama program, 116 konteks kueri generik), exclude 1.610 (1.421 tanpa bukti, 139 di luar
jendela, 36 `meta.ai`, 14 promosi). Kueri `maganghub` dan `magang kemnaker` berhenti karena batas
maksimal/429. Tanggal tertua yang terlihat untuk kueri tersebut adalah 10 Sep 2026 dan 23 Des 2025,
sehingga cakupan fase awal Threads tidak merata antarkata kunci.

## 4. Bahan ringkas laporan

**C2 (pipeline).** Kolektor twscrape (pencarian internal X, `lang:in`, lima kata kunci OR, jendela
harian WIB) menulis raw JSONL append-only beserta log/checkpoint. `preprocess_tk2.py snapshot`
membekukan raw (batas byte + SHA-256). `run` memvalidasi, mengarantina, men-dedup ID, menilai
relevansi dari bukti teks, menyaring penawaran promosi, menghitung fase WIB, membuat empat versi
teks, dan menandai teks berulang/near-dup. Hasilnya dataset kandidat, subset model-ready, log
eksklusi, antrean review, dan audit cakupan. Keputusan peninjau diimpor append-only lalu diterapkan
pada rerun. Komponen: Python 3.13, pandas, scikit-learn (TF-IDF karakter untuk near-dup), CSV/JSONL.

**C4 (implementasi nyata).** Angka bagian 3, `tahapan_x.csv` (dapat direkonsiliasi dengan
snapshot), 19 tes otomatis (batas WIB, ID 19 digit, missing vs nol, Unicode/emoji/negasi,
quote, teks terpotong vs penuh, iklan vs kritik/permintaan, post pendek, review bertahan,
idempotensi), dan contoh transformasi teks yang disamarkan.

**C5 (kualitas & keterbatasan).**
- Korpus bukan sensus. 50 dari 117 tanggal pernah kena batas harian; status "stream habis" tidak
  terverifikasi lengkap.
- Hasil OR mencakup post tidak relevan (504 dikeluarkan berdasarkan bukti teks, belum divalidasi
  manusia).
- Konteks quote/reply tidak dikumpulkan, sehingga post reaksi tanpa rujukan tidak bisa dinilai.
- Truncation tidak diketahui untuk 97,6% record.
- 129 record browser lama tidak punya `content_type`/`n_quote`.
- Iklan CV/joki terkonsentrasi di fase3 dan mengubah proporsi fase.
- Bahasa: 43 post berlabel non-`in` dan 12 tanpa label bahasa (tidak ditebak); slang dan code-mixing dipertahankan, tidak diterjemahkan.
- Precision/recall aturan relevansi/promosi belum diukur (0 label manusia). Sampel 200 post berstrata
  dan subset kalibrasi dua peninjau sudah disiapkan.

**C6 (etika).**
- Hanya post publik yang diproses. Username dan URL tidak masuk output analisis; `user_hash`
  bergaram dengan salt lokal.
- Isi teks dimasking (URL/mention/email/telepon/16 digit). Ini pseudonimisasi, bukan anonimisasi:
  `post_id` dan kutipan dapat dilacak.
- Kutipan di laporan harus diparafrasakan.
- Salinan snapshot yang memuat username diabaikan Git. Sesi/cookie tidak dibaca oleh preprocessing.
- 33 post dengan indikasi PII ditandai untuk diperiksa (`privasi_ok`).

## 5. Langkah berikutnya

1. Dua peninjau melabeli 40 baris `kalibrasi_dua_peninjau` di `sampel_review_x.csv` secara
   independen; hitung kesepakatan.
2. Tinjau antrean X (60 post), lalu sisa sampel X. Hitung presisi aturan per strata dan presisi
   tertimbang (`bobot`).
3. ~~Putuskan apakah Threads dipakai.~~ Diputuskan 26 Okt 2026: Threads dipakai sebagai korpus
   pelengkap, hanya post yang menyebut nama program (keputusan #20). Tersisa 22 post pending
   promosi di `threads/antrean_review_threads.csv`. Batasan ini dicatat di C5: post Threads yang
   membahas program tanpa menyebut namanya (mis. keluhan uang saku/mentor) tidak masuk korpus.
4. Verifikasi batas fase terhadap sumber resmi Kemnaker. Jika berubah, ubah `config.JENDELA_WAKTU`
   secara eksplisit dan jalankan ulang.
5. Saat memilih model sentimen, uji `text_sentiment` vs `text_sentiment_slang_v1` sebagai variabel
   eksperimen (Modul 06 hlm. 32–33), jangan diasumsikan.
