# Laporan kualitas preprocessing — snapshot 20261026_d11a2b74c6

Dibuat otomatis oleh `preprocess_tk2.py run`. Semua angka dihitung dari snapshot ini.

## Status validasi
- Keputusan manusia yang tersedia: **0 post**.
- Tanpa label manusia, precision/recall aturan dan kesepakatan antarpeninjau **belum dapat dihitung**.
- `model_ready_*` = lolos aturan otomatis (dan review bila ada). Bukan gold standard.
- Korpus adalah hasil pencarian X/Threads dengan batas kolektor, **bukan sensus** percakapan.

## Snapshot
- Dibuat (WIB): 2026-10-26T14:43:19.399371+07:00; metode: Per-file sequential read of bytes up to size at read time, truncated at the last physical newline. NOT atomic across files. Raw files were not modified.

- `x_fase1_pengumuman.jsonl`: 2473 record, 2250534 byte, sisa tidak lengkap 0 byte, sha256 `74db1daba0a1ee21…`
- `x_fase2_seleksi.jsonl`: 936 record, 803979 byte, sisa tidak lengkap 0 byte, sha256 `1bedc78341afdc27…`
- `x_fase3_penempatan.jsonl`: 1848 record, 1647474 byte, sisa tidak lengkap 0 byte, sha256 `0b7ed2960face962…`
- `threads_magang-hub.jsonl`: 899 record, 530003 byte, sisa tidak lengkap 0 byte, sha256 `93f418f2dbad84cb…`
- `threads_magang-kemnaker.jsonl`: 2684 record, 1720243 byte, sisa tidak lengkap 0 byte, sha256 `c83e02e858724aea…`
- `threads_magang-nasional.jsonl`: 262 record, 189382 byte, sisa tidak lengkap 0 byte, sha256 `7e48ea86c6daa920…`
- `threads_maganghub.jsonl`: 1416 record, 738510 byte, sisa tidak lengkap 0 byte, sha256 `c8d4afc4e21b5876…`
- `threads_pemagangan-nasional.jsonl`: 767 record, 478288 byte, sisa tidak lengkap 0 byte, sha256 `8ba43a440bed87a7…`

## Platform: x

- Raw 5257 -> karantina 0 -> valid 5257 -> post unik 5257.
- Status akhir: keep **4306**, pending **60**, exclude **891** (rekonsiliasi OK).
- Model-ready: 4306 (tanpa akun resmi/media terdaftar: 4205; satu wakil per teks identik: 4277).
- Sampel review berstrata: 200 post.

### Tahapan (tiap post tepat satu status/alasan utama)

| tahap | jumlah | keterangan |
|---|---|---|
| 1_record_raw_snapshot | 5257 |  |
| 2_karantina_invalid | 0 | lihat karantina.csv |
| 3_record_valid | 5257 | raw - karantina |
| 4_versi_id_sama_digabung | 0 | dedup (platform, post_id) |
| 5_post_unik | 5257 | basis keputusan |
| 6_exclude_total | 891 | status akhir (tiap post tepat satu) |
| 6.exclude:relevansi_otomatis_tanpa_bukti_teks | 504 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_penawaran_layanan_dengan_kontak_harga_atau_testimoni | 142 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_penawaran_eksplisit_jasa_atau_joki | 134 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_paket_layanan_dengan_ajakan_kontak | 69 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_layanan_berharga_dengan_bukti_jual | 28 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_promosi_komersial_kode_referal | 14 | alasan utama; tidak tumpang tindih |
| 7_pending_total | 60 | status akhir (tiap post tepat satu) |
| 7.pending:relevansi_konteks_or | 21 | alasan utama; tidak tumpang tindih |
| 7.pending:promosi_indikasi_penawaran_belum_pasti | 18 | alasan utama; tidak tumpang tindih |
| 7.pending:promosi_layanan_dengan_ajakan_kontak | 12 | alasan utama; tidak tumpang tindih |
| 7.pending:promosi_kritik_atau_kutipan_layanan | 4 | alasan utama; tidak tumpang tindih |
| 7.pending:promosi_tagar_banyak_dengan_sinyal_komersial | 3 | alasan utama; tidak tumpang tindih |
| 7.pending:promosi_bantuan_gratis_perlu_konteks | 1 | alasan utama; tidak tumpang tindih |
| 7.pending:relevansi_konteks_jangkar | 1 | alasan utama; tidak tumpang tindih |
| 8_keep_total | 4306 | status akhir (tiap post tepat satu) |
| 8.keep:lolos | 4306 | alasan utama; tidak tumpang tindih |

### Fase x status

| fase | exclude | keep | pending | total |
|---|---|---|---|---|
| fase1_pengumuman | 85 | 2362 | 26 | 2473 |
| fase2_seleksi | 31 | 899 | 6 | 936 |
| fase3_penempatan | 775 | 1045 | 28 | 1848 |

### Pergeseran distribusi fase akibat penyaringan

| fase | post_unik_dalam_jendela | model_ready | proporsi_unik | proporsi_model_ready | retensi |
|---|---|---|---|---|---|
| fase1_pengumuman | 2473 | 2362 | 0.4704 | 0.5485 | 0.9551 |
| fase2_seleksi | 936 | 899 | 0.178 | 0.2088 | 0.9605 |
| fase3_penempatan | 1848 | 1045 | 0.3515 | 0.2427 | 0.5655 |

### Kolektor x status

| collector | exclude | keep | pending | total |
|---|---|---|---|---|
| connected_brave_dom_v1 | 2 | 10 | 0 | 12 |
| connected_brave_dom_v2 | 67 | 47 | 3 | 117 |
| twscrape_0.20.1 | 822 | 4249 | 57 | 5128 |

### Tumpang tindih relevansi x promosi (bukan untuk dijumlahkan)

| relevansi_jalur | exclude | keep | review | All |
|---|---|---|---|---|
| eksplisit | 385 | 4045 | 37 | 4467 |
| eksplisit_generik | 0 | 228 | 1 | 229 |
| eksplisit_handle | 0 | 33 | 0 | 33 |
| konteks_jangkar | 2 | 0 | 1 | 3 |
| konteks_or | 0 | 19 | 2 | 21 |
| tanpa_bukti | 11 | 478 | 15 | 504 |
| All | 398 | 4803 | 56 | 5257 |

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
- post_lang: {'in': 5202, 'en': 25, '(missing)': 12, 'lv': 4, 'qme': 2, 'tl': 2, 'und': 1, 'th': 1, 'zxx': 1, 'tr': 1, 'ja': 1, 'es': 1, 'lt': 1, 'da': 1, 'fi': 1, 'fr': 1}.
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
- Status akhir: keep **3309**, pending **1109**, exclude **1610** (rekonsiliasi OK).
- Model-ready: 3309 (tanpa akun resmi/media terdaftar: 3104; satu wakil per teks identik: 3203).
- Sampel review berstrata: 200 post.

### Tahapan (tiap post tepat satu status/alasan utama)

| tahap | jumlah | keterangan |
|---|---|---|
| 1_record_raw_snapshot | 6028 |  |
| 2_karantina_invalid | 0 | lihat karantina.csv |
| 3_record_valid | 6028 | raw - karantina |
| 4_versi_id_sama_digabung | 0 | dedup (platform, post_id) |
| 5_post_unik | 6028 | basis keputusan |
| 6_exclude_total | 1610 | status akhir (tiap post tepat satu) |
| 6.exclude:relevansi_otomatis_tanpa_bukti_teks | 1421 | alasan utama; tidak tumpang tindih |
| 6.exclude:di_luar_jendela | 139 | alasan utama; tidak tumpang tindih |
| 6.exclude:akun_otomatis_config | 36 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_penawaran_eksplisit_jasa_atau_joki | 6 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_penawaran_layanan_dengan_kontak_harga_atau_testimoni | 4 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_paket_layanan_dengan_ajakan_kontak | 2 | alasan utama; tidak tumpang tindih |
| 6.exclude:promosi_otomatis_promosi_komersial_kode_referal | 2 | alasan utama; tidak tumpang tindih |
| 7_pending_total | 1109 | status akhir (tiap post tepat satu) |
| 7.pending:relevansi_konteks_jangkar | 971 | alasan utama; tidak tumpang tindih |
| 7.pending:relevansi_konteks_kueri_generik | 116 | alasan utama; tidak tumpang tindih |
| 7.pending:promosi_indikasi_penawaran_belum_pasti | 6 | alasan utama; tidak tumpang tindih |
| 7.pending:promosi_layanan_dengan_ajakan_kontak | 6 | alasan utama; tidak tumpang tindih |
| 7.pending:promosi_kritik_atau_kutipan_layanan | 4 | alasan utama; tidak tumpang tindih |
| 7.pending:promosi_bantuan_gratis_perlu_konteks | 3 | alasan utama; tidak tumpang tindih |
| 7.pending:promosi_tagar_banyak_dengan_sinyal_komersial | 3 | alasan utama; tidak tumpang tindih |
| 8_keep_total | 3309 | status akhir (tiap post tepat satu) |
| 8.keep:lolos | 3309 | alasan utama; tidak tumpang tindih |

### Fase x status

| fase | exclude | keep | pending | total |
|---|---|---|---|---|
| di_luar_jendela | 139 | 0 | 0 | 139 |
| fase1_pengumuman | 115 | 779 | 279 | 1173 |
| fase2_seleksi | 106 | 699 | 251 | 1056 |
| fase3_penempatan | 1250 | 1831 | 579 | 3660 |

### Pergeseran distribusi fase akibat penyaringan

| fase | post_unik_dalam_jendela | model_ready | proporsi_unik | proporsi_model_ready | retensi |
|---|---|---|---|---|---|
| fase1_pengumuman | 1173 | 779 | 0.1992 | 0.2354 | 0.6641 |
| fase2_seleksi | 1056 | 699 | 0.1793 | 0.2112 | 0.6619 |
| fase3_penempatan | 3660 | 1831 | 0.6215 | 0.5533 | 0.5003 |

### Kolektor x status

| collector | exclude | keep | pending | total |
|---|---|---|---|---|
| threads_playwright | 1610 | 3309 | 1109 | 6028 |

### Tumpang tindih relevansi x promosi (bukan untuk dijumlahkan)

| relevansi_jalur | exclude | keep | review | All |
|---|---|---|---|---|
| eksplisit | 12 | 2895 | 19 | 2926 |
| eksplisit_generik | 0 | 376 | 2 | 378 |
| eksplisit_handle | 0 | 107 | 2 | 109 |
| konteks_jangkar | 2 | 986 | 9 | 997 |
| konteks_kueri_generik | 0 | 120 | 1 | 121 |
| tanpa_bukti | 1 | 1490 | 6 | 1497 |
| All | 15 | 5974 | 39 | 6028 |

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
