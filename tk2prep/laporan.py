"""Distribusi, missingness, kamus data, panduan label, dan LAPORAN_KUALITAS.md (angka dihitung, bukan dikarang)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def _csv(df, path):
    df.to_csv(path, encoding="utf-8-sig", lineterminator="\n")


def distribusi(out: Path, plat: str, recs: list[dict]) -> dict:
    df = pd.DataFrame([{k: r.get(k) for k in (
        "fase", "tanggal_wib", "status_final", "alasan_utama", "collector", "content_type", "jenis_akun_otomatis",
        "relevansi_jalur", "promosi_keputusan_otomatis", "teks_berulang_grup", "teks_berulang_n", "near_dup_grup",
        "split_group_n", "text_truncated", "n_reply", "n_repost", "n_like", "n_quote", "post_lang",
        "conversation_id", "user_hash", "author_missing", "pii_flags", "teks_pendek")} for r in recs])
    df["fase"] = df["fase"].fillna("di_luar_jendela")
    hasil = {}
    for nama, kol in (("fase", "fase"), ("kolektor", "collector"), ("content_type", "content_type"),
                      ("jenis_akun", "jenis_akun_otomatis")):
        t = df.groupby([df[kol].fillna("(missing)"), "status_final"]).size().unstack(fill_value=0)
        t["total"] = t.sum(axis=1)
        _csv(t, out / f"distribusi_{nama}_{plat}.csv")
        hasil[nama] = t
    t = df.groupby(["fase", "tanggal_wib", "status_final"]).size().unstack(fill_value=0)
    _csv(t, out / f"distribusi_tanggal_{plat}.csv")
    # Tumpang tindih flag: tabulasi silang, BUKAN dijumlahkan sebagai eksklusi terpisah.
    silang = pd.crosstab(df["relevansi_jalur"], df["promosi_keputusan_otomatis"], margins=True)
    _csv(silang, out / f"tumpang_tindih_relevansi_promosi_{plat}.csv")
    hasil["silang"] = silang
    # Pergeseran distribusi fase akibat penyaringan.
    dalam = df[df["fase"] != "di_luar_jendela"]
    geser = pd.DataFrame({
        "post_unik_dalam_jendela": dalam.groupby("fase").size(),
        "model_ready": dalam[dalam.status_final == "keep"].groupby("fase").size(),
    }).fillna(0).astype(int)
    geser["proporsi_unik"] = (geser.post_unik_dalam_jendela / max(1, geser.post_unik_dalam_jendela.sum())).round(4)
    geser["proporsi_model_ready"] = (geser.model_ready / max(1, geser.model_ready.sum())).round(4)
    geser["retensi"] = (geser.model_ready / geser.post_unik_dalam_jendela.where(geser.post_unik_dalam_jendela > 0)).round(4)
    _csv(geser, out / f"pergeseran_fase_{plat}.csv")
    hasil["geser"] = geser
    # Missingness: missing berbeda dari nol.
    miss = []
    for k in ("n_reply", "n_repost", "n_like", "n_quote", "post_lang", "conversation_id", "content_type",
              "user_hash", "text_truncated"):
        s = df[k]
        miss.append(dict(kolom=k, n=len(s), missing=int(s.isna().sum()),
                         nol=str(int((s == 0).sum())) if k.startswith("n_") else "-",
                         pct_missing=round(float(s.isna().mean()), 4)))
    trunc = df["text_truncated"].map({True: "true", False: "false"}).fillna("unknown").value_counts()
    miss_df = pd.DataFrame(miss)
    miss_df.to_csv(out / f"missingness_{plat}.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    hasil["missing"] = miss_df
    hasil["truncation"] = trunc.to_dict()
    hasil["duplikasi"] = dict(
        post_dalam_grup_teks_identik=int(df["teks_berulang_grup"].notna().sum()),
        grup_teks_identik=int(df["teks_berulang_grup"].nunique()),
        post_dalam_grup_near_dup=int(df["near_dup_grup"].notna().sum()),
        grup_near_dup=int(df["near_dup_grup"].nunique()),
        post_dengan_split_group_lebih_dari_1=int((df["split_group_n"] > 1).sum()),
        teks_identik_max=int(df["teks_berulang_n"].max()) if len(df) else 0,
    )
    hasil["pii"] = int(df["pii_flags"].map(bool).sum())
    hasil["pendek"] = int(df["teks_pendek"].sum())
    hasil["lang"] = df["post_lang"].fillna("(missing)").value_counts().to_dict()
    hasil["author_missing"] = int(df["author_missing"].sum())
    hasil["penulis_unik"] = int(df["user_hash"].nunique())
    return hasil


KAMUS = [
    ("platform", "str", "x atau threads (korpus diproses terpisah)"),
    ("post_id", "str", "ID post asli sebagai STRING (ID X 19 digit). Jangan buka di spreadsheet tanpa set kolom teks"),
    ("user_hash", "str|null", "SHA-256 bergaram (16 hex) dari username; null jika author tidak ada. Pseudonim, bukan anonim"),
    ("author_missing", "bool", "username tidak tersedia di raw"),
    ("jenis_akun_otomatis", "str", "resmi/media/akun_otomatis dari daftar config; tidak_terdaftar BUKAN bukti akun publik"),
    ("jenis_akun_manual", "str|null", "keputusan reviewer (publik/resmi/media/organisasi_lain/ragu/konflik)"),
    ("created_at_asal", "str", "timestamp persis dari raw"),
    ("created_at_utc / waktu_wib / tanggal_wib", "str", "timestamp ter-normalisasi; tanggal_wib dipakai untuk fase"),
    ("fase", "str|null", "fase dari waktu aktual, interval [awal 00:00 WIB, akhir 00:00 WIB); null = di luar jendela"),
    ("fase_raw / fase_raw_berbeda", "str/bool", "fase yang ditulis kolektor dan apakah berbeda dari perhitungan ulang"),
    ("content_type", "str|null", "original/reply/quote dari adapter; null untuk kolektor browser lama"),
    ("post_lang", "str|null", "bahasa menurut X; tidak ditebak bila kosong"),
    ("n_reply, n_repost, n_like, n_quote", "int|null", "engagement pada metrik_scraped_at; null = tidak dikumpulkan (BUKAN 0)"),
    ("text_truncated", "bool|null", "true/false bila diketahui; null = tidak diketahui (twscrape tidak memberi flag)"),
    ("text_minimal", "str", "NFC, HTML unescape, whitespace, masking [URL]/[USER]/[EMAIL]/[PHONE]/[NIK]; emoji, negasi, kapital dipertahankan"),
    ("text_sentiment", "str", "baseline input transformer sentimen = text_minimal dengan deret mention pembuka diringkas"),
    ("text_sentiment_slang_v1 / slang_v1_ganti", "str/json", "VARIAN opsional normalisasi slang tak ambigu + log penggantian (reversible)"),
    ("text_embedding", "str", "konteks utuh untuk sentence embedding BERTopic (tanpa [URL], tanpa alamat reply, '#' dilepas)"),
    ("text_topic_repr", "str", "token huruf kecil untuk CountVectorizer/c-TF-IDF; stopword fungsi dibuang, negasi & kata domain dipertahankan"),
    ("relevansi_jalur / relevansi_bukti", "str", "eksplisit, eksplisit_generik, eksplisit_handle, konteks_jangkar, konteks_or, konteks_kueri_generik, tanpa_bukti + potongan bukti"),
    ("relevansi_otomatis / relevansi_manual", "str", "keputusan aturan vs reviewer (manusia menang)"),
    ("promosi_keputusan_otomatis / promosi_alasan / promosi_sinyal", "str", "keputusan promosi_v3 (keep/review/exclude), alasan, sinyal"),
    ("promosi_manual", "str|null", "iklan/bukan_iklan/ragu/konflik dari reviewer"),
    ("status_final / alasan_utama / alasan_lain", "str", "keep/pending/exclude; satu alasan utama (urutan tetap) + alasan lain"),
    ("sumber_keputusan / reviewers", "str", "otomatis, manusia, atau keduanya; daftar reviewer"),
    ("sentimen_manual / stance_manual / aspek_manual", "str|null", "anotasi lanjutan opsional (belum ada = null)"),
    ("teks_berulang_grup / teks_berulang_n", "str/int", "grup teks identik (setelah casefold & placeholder) dan ukurannya"),
    ("near_dup_grup", "str|null", "grup near-duplicate (cosine char 3-5 gram >= 0.90, negasi & emoji sama)"),
    ("split_group_id / split_group_n", "str/int", "gabungan grup identik + near-dup untuk split evaluasi tanpa bocor"),
    ("teks_pendek", "bool", "< 4 token di text_embedding; hanya flag, tidak dibuang"),
    ("pii_flags", "str", "email/telepon/angka_16_digit/nama_diri terdeteksi di teks asli (sudah dimasking kecuali nama)"),
    ("flags", "str", "flag validasi & kualitas (titik koma)"),
    ("collector / adapter_version / query_window / kueri_semua / language_filter / job_since / job_until / scraped_at", "str",
     "provenance pengambilan per record"),
    ("n_versi / konflik_teks / konflik_metrik / sumber_versi", "int/bool/str", "jumlah versi ID yang sama dan konfliknya (file:baris|kolektor)"),
    ("conversation_id", "str|null", "ID percakapan; konteks reply TIDAK dikumpulkan"),
]


def kamus_data() -> pd.DataFrame:
    return pd.DataFrame(KAMUS, columns=["kolom", "tipe", "deskripsi"])


PANDUAN = """# Panduan label review (TK2 MagangHub)

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
"""


def tulis_panduan_label(path: Path):
    path.write_text(PANDUAN, encoding="utf-8")


def _md(df: pd.DataFrame, index=True) -> str:
    d = df.reset_index() if index else df
    kol = [str(c) for c in d.columns]
    baris = ["| " + " | ".join(kol) + " |", "|" + "---|" * len(kol)]
    for _, r in d.iterrows():
        baris.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r.values) + " |")
    return "\n".join(baris)


def tulis_laporan(out: Path, manifest: dict, cfg: dict, ringkas: dict):
    L = [f"# Laporan kualitas preprocessing — snapshot {manifest['snapshot_id']}", "",
         "Dibuat otomatis oleh `preprocess_tk2.py run`. Semua angka dihitung dari snapshot ini.", "",
         "## Status validasi",
         f"- Keputusan manusia yang tersedia: **{cfg['n_keputusan_manusia']} post**.",
         "- Tanpa label manusia, precision/recall aturan dan kesepakatan antarpeninjau **belum dapat dihitung**.",
         "- `model_ready_*` = lolos aturan otomatis (dan review bila ada). Bukan gold standard.",
         "- Korpus adalah hasil pencarian X/Threads dengan batas kolektor, **bukan sensus** percakapan.", "",
         "## Snapshot",
         f"- Dibuat (WIB): {manifest['created_wib']}; metode: {manifest['method']}", ""]
    for f in manifest["files"]:
        L.append(f"- `{f['file']}`: {f['n_records']} record, {f['byte_limit']} byte, sisa tidak lengkap "
                 f"{f['incomplete_tail_bytes']} byte, sha256 `{f['sha256'][:16]}…`")
    L.append("")
    for plat, s in ringkas["platform"].items():
        st = s["statistik"]
        L += [f"## Platform: {plat}", "",
              f"- Raw {s['n_raw']} -> karantina {s['karantina']} -> valid {s['valid']} -> post unik {s['unik']}.",
              f"- Status akhir: keep **{s['status']['keep']}**, pending **{s['status']['pending']}**, "
              f"exclude **{s['status']['exclude']}** (rekonsiliasi {'OK' if s['rekonsiliasi_ok'] else 'GAGAL'}).",
              f"- Model-ready: {s['n_model_ready']} (tanpa akun resmi/media terdaftar: {s['n_tanpa_resmi_media']}; "
              f"satu wakil per teks identik: {s['n_satu_per_teks']}).",
              f"- Sampel review berstrata: {s['n_sampel']} post.", "",
              "### Tahapan (tiap post tepat satu status/alasan utama)", "", _md(s["tahapan"], index=False), "",
              "### Fase x status", "", _md(st["fase"]), "",
              "### Pergeseran distribusi fase akibat penyaringan", "", _md(st["geser"]), "",
              "### Kolektor x status", "", _md(st["kolektor"]), "",
              "### Tumpang tindih relevansi x promosi (bukan untuk dijumlahkan)", "", _md(st["silang"]), "",
              "### Missingness (missing ≠ nol)", "", _md(st["missing"], index=False), "",
              f"- text_truncated: {st['truncation']} (unknown = tidak diketahui, bukan bukti lengkap).",
              f"- post_lang: {st['lang']}.",
              f"- Penulis unik (hash): {st['penulis_unik']}; author missing: {st['author_missing']}.",
              f"- Duplikasi/pengulangan: {st['duplikasi']}.",
              f"- Post dengan indikasi PII di teks asli: {st['pii']}; post pendek (<4 token): {st['pendek']}.", ""]
        if "cakupan" in st:
            c = st["cakupan"]
            ring = c.groupby(["fase", "status_ringkas"]).size().unstack(fill_value=0)
            L += ["### Cakupan pengambilan per tanggal (status percobaan terakhir)", "", _md(ring), "",
                  f"- Tanggal yang pernah kena batas (bisa kurang terwakili): {int(c['pernah_kena_batas'].sum())} dari {len(c)}.",
                  "- Tidak ada status yang berarti lengkap; `stream_habis_unverified` bukan sensus.",
                  "- Volume per tanggal tidak boleh dibaca sebagai volume percakapan sebenarnya.", ""]
    L += ["## Asumsi yang belum terverifikasi",
          "- Batas fase (config.JENDELA_WAKTU) mengikuti TK1 §1.6 yang merujuk berita (Tribun Kaltim [24]); "
          "bukan tanggal resmi yang sudah diverifikasi. Fase 3 di TK1 'sesudahnya'; di sini dipotong pada batas akhir koleksi.",
          "- Daftar akun resmi/media tidak lengkap; `tidak_terdaftar` perlu ditinjau.",
          "- Relevansi `eksplisit_generik` ('magang nasional') diasumsikan merujuk program ini; perlu dicek di sampel.", ""]
    (out / "LAPORAN_KUALITAS.md").write_text("\n".join(L), encoding="utf-8")
