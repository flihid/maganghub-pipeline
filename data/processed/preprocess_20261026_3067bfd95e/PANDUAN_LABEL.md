# Panduan label review (TK2 MagangHub)

Status: panduan operasional untuk peninjau manusia. Label dari aturan, script, atau agent AI
**bukan** keputusan manusia dan tidak boleh diisi sebagai reviewer.

## Berkas
- `antrean_review_<platform>.csv`: semua post berstatus *pending* (wajib ditinjau sebelum masuk model-ready).
- `sampel_review_<platform>.csv`: sampel diagnostik berstrata (status x fase x kolektor, seed tetap).
  Kolom `bobot` = N_strata / n_strata. Untuk estimasi presisi keseluruhan gunakan bobot; per strata boleh tanpa bobot.
  Baris `kalibrasi_dua_peninjau=1` diberi label oleh **dua peninjau secara independen** (jangan saling melihat)
  untuk menghitung kesepakatan (mis. Cohen's kappa).

## Cara mengisi
1. Salin berkas, isi kolom `reviewer` (inisial/nama, bukan "auto"/"agent").
2. Isi hanya kolom yang Anda putuskan; sel kosong berarti "tidak memberi keputusan" dan tidak menghapus keputusan lama.
3. Simpan sebagai CSV UTF-8. Jangan biarkan spreadsheet mengubah `post_id` menjadi angka ilmiah (set kolom ke Teks).
4. Jalankan `python preprocess_tk2.py import-review <berkas.csv>` lalu `python preprocess_tk2.py run`.

## Nilai yang diterima
| Kolom | Nilai | Definisi |
|---|---|---|
| keputusan_relevansi | relevan / tidak_relevan / ragu | Relevan = membahas Program Magang Nasional/MagangHub (pengalaman, opini positif/negatif/netral, pertanyaan, berita, pengumuman). Tidak perlu bernada negatif. Tidak relevan = topik lain atau hanya kebetulan memuat kata. |
| keputusan_promosi | bukan_iklan / iklan / ragu | Iklan = **menawarkan** jasa/produk (CV, joki, referal) dengan maksud jual. Kritik terhadap iklan, permintaan jasa, atau diskusi uang saku bukan iklan. |
| jenis_akun_manual | publik / resmi / media / organisasi_lain / ragu | Berdasarkan isi dan, bila perlu, profil publik akun. Jangan menyalin username ke berkas. |
| privasi_ok | ya / tidak | "tidak" bila teks masih memuat nama orang, nomor, alamat, atau detail yang membuat orang mudah dikenali. |
| sentimen_manual (opsional) | positif / negatif / netral / campuran / ragu | Polaritas ekspresi penulis. |
| stance_manual (opsional) | mendukung / menolak / netral_tidak_jelas / tidak_berlaku | Sikap terhadap **program/kebijakan**. Keluhan teknis (mis. "uang saku telat cair") bernada negatif tetapi belum tentu menolak program. |
| aspek_manual (opsional) | teks pendek, pisah `;` | Sasaran ekspresi, mis. `uang_saku;pencairan`, `seleksi;status`, `mentor;tempat_magang`, `substitusi_kerja`, `syarat_kepesertaan`, `sistem_web`, `informasi`. |
| catatan | bebas | Alasan singkat, terutama untuk `ragu`. |

## Contoh (disamarkan)
- "[USER] uang saku batch 2 kok belum cair juga ya 😭" -> relevan, bukan_iklan, negatif, stance netral_tidak_jelas, aspek uang_saku;pencairan.
- "Aku open review CV ATS buat MagangHub, WA di bio" -> relevan (menyebut program), **iklan**.
- "Search MagangHub isinya iklan joki CV doang, muak" -> relevan, bukan_iklan (kritik), negatif.
- "MagangHub mengecewakan 😭" -> relevan; post pendek tetap informatif.
- "Program ini cuma bikin perusahaan nggak buka lowongan tetap" -> relevan, negatif, menolak, aspek substitusi_kerja.
  Ini **persepsi** substitusi, bukan bukti kausal substitusi tenaga kerja.

## Konteks yang tidak dikumpulkan
Teks yang dikutip (quote) dan post induk (reply) tidak tersimpan. Jangan menebak isinya; beri `ragu` bila
keputusan bergantung pada konteks tersebut.
