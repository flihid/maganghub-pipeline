# Laporan kualitas preprocessing — snapshot 20261026_3067bfd95e

Dibuat otomatis oleh `preprocess_tk2.py run`. Semua angka dihitung dari snapshot ini.

## Status validasi
- Keputusan manusia yang tersedia: **252 post**.
- Presisi aturan: `python alat_review/presisi_aturan.py <sampel_terisi>.csv` (berbobot strata). Kesepakatan antarpeninjau: `python alat_review/kappa_kalibrasi.py`, yang menuntut dua peninjau pada baris kalibrasi yang sama.
- `model_ready_*` = lolos aturan otomatis (dan review bila ada). Bukan gold standard.
- Korpus adalah hasil pencarian X/Threads dengan batas kolektor, **bukan sensus** percakapan.

## Snapshot
- Dibuat (WIB): 2026-10-26T23:05:08.308864+07:00; metode: Per-file sequential read of bytes up to size at read time, truncated at the last physical newline. NOT atomic across files. Raw files were not modified.

- `x_fase1_pengumuman.jsonl`: 2473 record, 2248061 byte, sisa tidak lengkap 0 byte, sha256 `f1c6eb6100001a0c…`
- `x_fase2_seleksi.jsonl`: 936 record, 803043 byte, sisa tidak lengkap 0 byte, sha256 `7b2b543eb122bdcd…`
- `x_fase3_penempatan.jsonl`: 1848 record, 1645626 byte, sisa tidak lengkap 0 byte, sha256 `3884d5c9cddd39e0…`
- `threads_magang-hub.jsonl`: 899 record, 529104 byte, sisa tidak lengkap 0 byte, sha256 `dc5b804462a19f25…`
- `threads_magang-kemnaker.jsonl`: 2684 record, 1717559 byte, sisa tidak lengkap 0 byte, sha256 `f334c010d607d7c8…`
- `threads_magang-nasional.jsonl`: 262 record, 189120 byte, sisa tidak lengkap 0 byte, sha256 `bb78e208f3bbbde6…`
- `threads_maganghub.jsonl`: 1416 record, 737094 byte, sisa tidak lengkap 0 byte, sha256 `bd96fbe3d1960330…`
- `threads_pemagangan-nasional.jsonl`: 767 record, 477521 byte, sisa tidak lengkap 0 byte, sha256 `f27e79e4a3fcf874…`

## Platform: x

- Raw 5257 -> karantina 0 -> valid 5257 -> post unik 5257.
- Status akhir: keep **4263**, pending **20**, exclude **974** (rekonsiliasi OK).
- Model-ready: 4263 (tanpa akun resmi/media terdaftar: 4162; satu wakil per teks identik: 4234).
- Sampel review berstrata: 200 post.

### Tahapan (tiap post tepat satu status/alasan utama)

| tahap | jumlah | keterangan |
|---|---|---|
| 1_record_raw_snapshot | 5257 |  |
| 2_karantina_invalid | 0 | lihat karantina.csv |
| 3_record_valid | 5257 | raw - karantina |
| 4_versi_id_sama_digabung | 0 | dedup (platform, post_id) |
| 5_post_unik | 5257 | basis keputusan |
| 6_exclude_total | 974 | status akhir (tiap post tepat satu) |
| 6.exclude:relevansi_otomatis_tanpa_bukti_teks | 478 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_penawaran_eksplisit_jasa_atau_joki | 129 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_penawaran_layanan_dengan_kontak_harga_atau_testimoni | 115 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_paket_layanan_dengan_ajakan_kontak | 64 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_manusia_iklan | 61 | alasan utama; tidak tumpang tindih |
| 6.exclude:relevansi_manusia_tidak_relevan | 39 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_layanan_dengan_kontak_dan_bukti_jual | 30 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_layanan_berharga_dengan_bukti_jual | 27 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_pengumuman_lowongan_mitra | 17 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_promosi_komersial_kode_referal | 14 | alasan utama; tidak tumpang tindih |
| 7_pending_total | 20 | status akhir (tiap post tepat satu) |
| 7.pending:relevansi_manusia_ragu | 19 | alasan utama; tidak tumpang tindih |
| 7.pending:promosi_manusia_ragu | 1 | alasan utama; tidak tumpang tindih |
| 8_keep_total | 4263 | status akhir (tiap post tepat satu) |
| 8.keep:lolos | 4263 | alasan utama; tidak tumpang tindih |

### Fase x status

| fase | exclude | keep | pending | total |
|---|---|---|---|---|
| fase1_pengumuman | 122 | 2345 | 6 | 2473 |
| fase2_seleksi | 36 | 895 | 5 | 936 |
| fase3_penempatan | 816 | 1023 | 9 | 1848 |

### Pergeseran distribusi fase akibat penyaringan

| fase | post_unik_dalam_jendela | model_ready | proporsi_unik | proporsi_model_ready | retensi |
|---|---|---|---|---|---|
| fase1_pengumuman | 2473 | 2345 | 0.4704 | 0.5501 | 0.9482 |
| fase2_seleksi | 936 | 895 | 0.178 | 0.2099 | 0.9562 |
| fase3_penempatan | 1848 | 1023 | 0.3515 | 0.24 | 0.5536 |

### Kolektor x status

| collector | exclude | keep | pending | total |
|---|---|---|---|---|
| connected_brave_dom_v1 | 2 | 10 | 0 | 12 |
| connected_brave_dom_v2 | 72 | 43 | 2 | 117 |
| twscrape_0.20.1 | 900 | 4210 | 18 | 5128 |

### Tumpang tindih relevansi x promosi (bukan untuk dijumlahkan)

| relevansi_jalur | exclude | keep | review | All |
|---|---|---|---|---|
| eksplisit | 406 | 4032 | 29 | 4467 |
| eksplisit_generik | 7 | 221 | 1 | 229 |
| eksplisit_handle | 0 | 33 | 0 | 33 |
| konteks_jangkar | 2 | 0 | 1 | 3 |
| konteks_or | 0 | 19 | 2 | 21 |
| tanpa_bukti | 11 | 478 | 15 | 504 |
| All | 426 | 4783 | 48 | 5257 |

### Missingness (missing ≠ nol)

| kolom | n | missing | nol | pct_missing |
|---|---|---|---|---|
| n_reply | 5257 | 0 | 1928 | 0.0 |
| n_repost | 5257 | 0 | 3578 | 0.0 |
| n_like | 5257 | 0 | 1123 | 0.0 |
| n_quote | 5257 | 129 | 3574 | 0.0245 |
| post_lang | 5257 | 12 | - | 0.0023 |
| conversation_id | 5257 | 129 | - | 0.0245 |
| content_type | 5257 | 129 | - | 0.0245 |
| user_hash | 5257 | 0 | - | 0.0 |
| text_truncated | 5257 | 5128 | - | 0.9755 |

- text_truncated: {'unknown': 5128, 'false': 120, 'true': 9} (unknown = tidak diketahui, bukan bukti lengkap).
- post_lang: {'in': 5202, 'en': 25, '(missing)': 12, 'lv': 4, 'tl': 2, 'qme': 2, 'und': 1, 'th': 1, 'tr': 1, 'zxx': 1, 'es': 1, 'ja': 1, 'lt': 1, 'da': 1, 'fi': 1, 'fr': 1}.
- Penulis unik (hash): 2651; author missing: 0.
- Duplikasi/pengulangan: {'post_dalam_grup_teks_identik': 287, 'grup_teks_identik': 47, 'post_dalam_grup_near_dup': 344, 'grup_near_dup': 44, 'post_dengan_split_group_lebih_dari_1': 437, 'teks_identik_max': 85}.
- Post dengan indikasi PII di teks asli: 33; post pendek (<4 token): 95.

### Cakupan pengambilan per tanggal (status percobaan terakhir)

| fase | kena_batas | stream_habis_unverified |
|---|---|---|
| fase1_pengumuman | 0 | 62 |
| fase2_seleksi | 0 | 20 |
| fase3_penempatan | 3 | 32 |

- Tanggal yang pernah kena batas (bisa kurang terwakili): 50 dari 117.
- Tidak ada status yang berarti lengkap; `stream_habis_unverified` bukan sensus.
- Volume per tanggal tidak boleh dibaca sebagai volume percakapan sebenarnya.

## Platform: threads

- Raw 6028 -> karantina 0 -> valid 6028 -> post unik 6028.
- Status akhir: keep **3190**, pending **0**, exclude **2838** (rekonsiliasi OK).
- Model-ready: 3190 (tanpa akun resmi/media terdaftar: 2992; satu wakil per teks identik: 3090).
- Sampel review berstrata: 200 post.

### Tahapan (tiap post tepat satu status/alasan utama)

| tahap | jumlah | keterangan |
|---|---|---|
| 1_record_raw_snapshot | 6028 |  |
| 2_karantina_invalid | 0 | lihat karantina.csv |
| 3_record_valid | 6028 | raw - karantina |
| 4_versi_id_sama_digabung | 0 | dedup (platform, post_id) |
| 5_post_unik | 6028 | basis keputusan |
| 6_exclude_total | 2838 | status akhir (tiap post tepat satu) |
| 6.exclude:relevansi_otomatis_tanpa_bukti_teks | 1421 | alasan utama; tidak tumpang tindih |
| 6.exclude:relevansi_konteks_tidak_dipakai | 1089 | alasan utama; tidak tumpang tindih |
| 6.exclude:di_luar_jendela | 139 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_pengumuman_lowongan_mitra | 124 | alasan utama; tidak tumpang tindih |
| 6.exclude:akun_otomatis_config | 36 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_manusia_iklan | 13 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_penawaran_eksplisit_jasa_atau_joki | 5 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_promosi_acara_pelatihan | 4 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_penawaran_layanan_dengan_kontak_harga_atau_testimoni | 3 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_paket_layanan_dengan_ajakan_kontak | 2 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_promosi_komersial_kode_referal | 2 | alasan utama; tidak tumpang tindih |
| 7_pending_total | 0 | status akhir (tiap post tepat satu) |
| 8_keep_total | 3190 | status akhir (tiap post tepat satu) |
| 8.keep:lolos | 3190 | alasan utama; tidak tumpang tindih |

### Fase x status

| fase | exclude | keep | total |
|---|---|---|---|
| di_luar_jendela | 139 | 0 | 139 |
| fase1_pengumuman | 444 | 729 | 1173 |
| fase2_seleksi | 413 | 643 | 1056 |
| fase3_penempatan | 1842 | 1818 | 3660 |

### Pergeseran distribusi fase akibat penyaringan

| fase | post_unik_dalam_jendela | model_ready | proporsi_unik | proporsi_model_ready | retensi |
|---|---|---|---|---|---|
| fase1_pengumuman | 1173 | 729 | 0.1992 | 0.2285 | 0.6215 |
| fase2_seleksi | 1056 | 643 | 0.1793 | 0.2016 | 0.6089 |
| fase3_penempatan | 3660 | 1818 | 0.6215 | 0.5699 | 0.4967 |

### Kolektor x status

| collector | exclude | keep | total |
|---|---|---|---|
| threads_playwright | 2838 | 3190 | 6028 |

### Tumpang tindih relevansi x promosi (bukan untuk dijumlahkan)

| relevansi_jalur | exclude | keep | review | All |
|---|---|---|---|---|
| eksplisit | 107 | 2802 | 17 | 2926 |
| eksplisit_generik | 13 | 363 | 2 | 378 |
| eksplisit_handle | 22 | 85 | 2 | 109 |
| konteks_jangkar | 15 | 973 | 9 | 997 |
| konteks_kueri_generik | 13 | 107 | 1 | 121 |
| tanpa_bukti | 6 | 1485 | 6 | 1497 |
| All | 176 | 5815 | 37 | 6028 |

### Missingness (missing ≠ nol)

| kolom | n | missing | nol | pct_missing |
|---|---|---|---|---|
| n_reply | 6028 | 0 | 2653 | 0.0 |
| n_repost | 6028 | 0 | 5000 | 0.0 |
| n_like | 6028 | 0 | 2568 | 0.0 |
| n_quote | 6028 | 6028 | 0 | 1.0 |
| post_lang | 6028 | 6028 | - | 1.0 |
| conversation_id | 6028 | 6028 | - | 1.0 |
| content_type | 6028 | 6028 | - | 1.0 |
| user_hash | 6028 | 0 | - | 0.0 |
| text_truncated | 6028 | 6028 | - | 1.0 |

- text_truncated: {'unknown': 6028} (unknown = tidak diketahui, bukan bukti lengkap).
- post_lang: {'(missing)': 6028}.
- Penulis unik (hash): 3881; author missing: 0.
- Duplikasi/pengulangan: {'post_dalam_grup_teks_identik': 252, 'grup_teks_identik': 88, 'post_dalam_grup_near_dup': 138, 'grup_near_dup': 42, 'post_dengan_split_group_lebih_dari_1': 340, 'teks_identik_max': 17}.
- Post dengan indikasi PII di teks asli: 85; post pendek (<4 token): 97.

## Asumsi yang belum terverifikasi
- Batas fase (config.JENDELA_WAKTU) mengikuti TK1 §1.6 yang merujuk berita (Tribun Kaltim [24]); bukan tanggal resmi yang sudah diverifikasi. Fase 3 di TK1 'sesudahnya'; di sini dipotong pada batas akhir koleksi.
- Daftar akun resmi/media tidak lengkap; `tidak_terdaftar` perlu ditinjau.
- Relevansi `eksplisit_generik` ('magang nasional') diasumsikan merujuk program ini; perlu dicek di sampel.
