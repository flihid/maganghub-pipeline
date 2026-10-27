"""Proses snapshot menjadi dataset kandidat, subset model-ready, log, antrean, dan audit.

Status akhir per post (satu status, satu alasan utama; flag lain disimpan terpisah):
  exclude  alasan utama mengikuti urutan: di_luar_jendela > akun_otomatis > relevansi > promosi
  pending  menunggu/konflik review (relevansi konteks, indikasi promosi, reviewer tidak sepakat)
  keep     lolos aturan otomatis dan/atau keputusan manusia
Keputusan manusia (data/annotations) selalu mengalahkan aturan untuk field yang diputuskan.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import secrets
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

import config
import promosi
import relevansi
from . import VERSION, cakupan, duplikat, laporan, muat, review, teks

WIB = ZoneInfo("Asia/Jakarta")
SEED = 20261026
MAKS_SAMPEL = 200
N_KALIBRASI = 40
MIN_TOKEN_PENDEK = 4

KOLOM_DATASET = [
    "platform", "post_id", "user_hash", "author_missing", "jenis_akun_otomatis", "jenis_akun_manual",
    "created_at_asal", "created_at_utc", "waktu_wib", "tanggal_wib", "fase", "fase_raw", "fase_raw_berbeda",
    "content_type", "post_lang", "n_reply", "n_repost", "n_like", "n_quote", "metrik_scraped_at",
    "text_truncated", "text_truncated_asal", "panjang_teks",
    "text_minimal", "text_sentiment", "text_sentiment_slang_v1", "slang_v1_ganti", "text_embedding", "text_topic_repr",
    "relevansi_jalur", "relevansi_bukti", "relevansi_otomatis", "relevansi_manual",
    "promosi_keputusan_otomatis", "promosi_alasan", "promosi_sinyal", "promosi_manual",
    "status_final", "alasan_utama", "sumber_keputusan", "reviewers",
    "sentimen_manual", "stance_manual", "aspek_manual",
    "teks_berulang_grup", "teks_berulang_n", "near_dup_grup", "split_group_id", "split_group_n",
    "teks_pendek", "pii_flags", "flags",
    "collector", "adapter_version", "query_window", "kueri_semua", "language_filter", "job_since", "job_until",
    "scraped_at", "n_versi", "konflik_teks", "konflik_metrik", "sumber_versi", "conversation_id",
]


# ---------------------------------------------------------------------------
def muat_salt(path: Path) -> str:
    if not path.exists():
        path.write_text(secrets.token_hex(16), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


def hash_user(username, salt):
    if not username:
        return None  # missing author tidak diberi identitas bersama
    return hashlib.sha256((salt + username.lower()).encode("utf-8")).hexdigest()[:16]


def tentukan_fase(ts: datetime, jendela: dict):
    """Interval [awal, akhir) pada pukul 00:00 WIB."""
    lokal = ts.astimezone(WIB)
    for nama, (since, until) in jendela.items():
        awal = datetime.combine(datetime.fromisoformat(since).date(), time(0), WIB)
        akhir = datetime.combine(datetime.fromisoformat(until).date(), time(0), WIB)
        if awal <= lokal < akhir:
            return nama
    return None


def jenis_akun(username):
    u = (username or "").lower()
    if u in config.AKUN_DIBUANG:
        return "akun_otomatis"
    if u in config.AKUN_RESMI:
        return "resmi"
    if u in config.AKUN_MEDIA:
        return "media"
    return "tidak_terdaftar"  # BUKAN bukti akun publik; perlu tinjauan


def keluarga_kolektor(c):
    c = c or ""
    return "browser_dom" if "brave" in c else "twscrape" if "twscrape" in c else c or "tidak_diketahui"


# ---------------------------------------------------------------------------
def perkaya(rec: dict, salt: str) -> dict:
    r = dict(rec)
    ts = r.pop("created_at")
    r["created_at_utc"] = ts.astimezone(ZoneInfo("UTC")).isoformat()
    r["waktu_wib"] = ts.astimezone(WIB).isoformat(timespec="seconds")
    r["tanggal_wib"] = ts.astimezone(WIB).date().isoformat()
    r["fase"] = tentukan_fase(ts, config.JENDELA_WAKTU)
    r["fase_raw_berbeda"] = bool(r.get("fase_raw")) and r["fase_raw"] != r["fase"]
    r["user_hash"] = hash_user(r.get("username"), salt)
    r["author_missing"] = r.get("username") is None
    r["jenis_akun_otomatis"] = jenis_akun(r.get("username"))
    r["panjang_teks"] = len(r["text"])
    r["text_minimal"] = teks.teks_minimal(r["text"])
    r["text_sentiment"] = teks.teks_sentimen(r["text_minimal"])
    slang, ganti = teks.teks_sentimen_slang(r["text_sentiment"])
    r["text_sentiment_slang_v1"] = slang
    r["slang_v1_ganti"] = json.dumps(ganti, ensure_ascii=False) if ganti else ""
    r["text_embedding"] = teks.teks_embedding(r["text_minimal"])
    r["text_topic_repr"] = teks.teks_topik(r["text_minimal"])
    r["pii_flags"] = teks.audit_pii(r["text"])
    jalur, bukti = relevansi.nilai_relevansi(r["text"], r.get("kueri_semua") or [])
    r["relevansi_jalur"], r["relevansi_bukti"] = jalur, bukti
    if jalur.startswith("konteks") and r["platform"] in config.RELEVANSI_KONTEKS_DIABAIKAN:
        r["relevansi_otomatis"] = "konteks_tidak_dipakai"
    else:
        r["relevansi_otomatis"] = ("relevan" if jalur.startswith("eksplisit") else
                                   "pending" if jalur.startswith("konteks") else "tidak_relevan")
    p = promosi.klasifikasi_promosi(r["text"], config.MAKS_HASHTAG)
    r["promosi_keputusan_otomatis"], r["promosi_alasan"], r["promosi_sinyal"] = (
        p["keputusan"], p["alasan"], p["sinyal"])
    r["teks_pendek"] = teks.jumlah_token(r["text_embedding"]) < MIN_TOKEN_PENDEK
    flags = list(r.get("flags_validasi") or [])
    if r["text_truncated"] is None:
        flags.append("text_truncated_unknown")
    elif r["text_truncated"]:
        flags.append("text_truncated_true")
    if r.get("post_lang") not in (None, "in", "id"):
        flags.append(f"post_lang_{r['post_lang']}")
    if r.get("post_lang") is None:
        flags.append("post_lang_missing")
    if r["fase_raw_berbeda"]:
        flags.append("fase_raw_berbeda")
    if jalur in ("eksplisit_generik", "eksplisit_handle"):
        flags.append("relevansi_" + jalur)
    if r["teks_pendek"]:
        flags.append("teks_pendek")
    r["flags"] = sorted(set(flags))
    return r


def putuskan(r: dict, manusia: dict | None) -> None:
    """Gabungkan keputusan otomatis dan manusia menjadi status_final + alasan_utama."""
    m = manusia or {}
    r["reviewers"] = ";".join(m.get("reviewers", []))
    for k in ("sentimen_manual", "stance_manual", "aspek_manual", "jenis_akun_manual"):
        r[k] = m.get(k)
    r["relevansi_manual"] = m.get("keputusan_relevansi")
    r["promosi_manual"] = m.get("keputusan_promosi")
    sumber = set()
    exclude, pending = [], []

    if r["fase"] is None:
        exclude.append("di_luar_jendela")
    if r["jenis_akun_otomatis"] == "akun_otomatis" and r["jenis_akun_manual"] in (None, "ragu"):
        exclude.append("akun_otomatis_config")

    rel = r["relevansi_manual"]
    if rel in ("relevan", "tidak_relevan"):
        sumber.add("manusia")
        if rel == "tidak_relevan":
            exclude.append("relevansi_manusia_tidak_relevan")
    elif rel in ("ragu", "konflik"):
        sumber.add("manusia")
        pending.append(f"relevansi_manusia_{rel}")
    else:
        sumber.add("otomatis")
        if r["relevansi_otomatis"] == "tidak_relevan":
            exclude.append("relevansi_otomatis_tanpa_bukti_teks")
        elif r["relevansi_otomatis"] == "konteks_tidak_dipakai":
            exclude.append("relevansi_konteks_tidak_dipakai")
        elif r["relevansi_otomatis"] == "pending":
            pending.append("relevansi_" + r["relevansi_jalur"])

    pro = r["promosi_manual"]
    if pro in ("iklan", "bukan_iklan"):
        sumber.add("manusia")
        if pro == "iklan":
            exclude.append("promosi_manusia_iklan")
    elif pro in ("ragu", "konflik"):
        sumber.add("manusia")
        pending.append(f"promosi_manusia_{pro}")
    else:
        sumber.add("otomatis")
        if r["promosi_keputusan_otomatis"] == "exclude":
            exclude.append("promosi_otomatis_" + r["promosi_alasan"])
        elif r["promosi_keputusan_otomatis"] == "review":
            pending.append("promosi_" + r["promosi_alasan"])

    if exclude:
        r["status_final"], r["alasan_utama"] = "exclude", exclude[0]
    elif pending:
        r["status_final"], r["alasan_utama"] = "pending", pending[0]
    else:
        r["status_final"], r["alasan_utama"] = "keep", "lolos"
    r["alasan_lain"] = ";".join(exclude[1:] + pending if exclude else pending[1:])
    r["sumber_keputusan"] = "+".join(sorted(sumber))


# ---------------------------------------------------------------------------
def ke_frame(records: list[dict], kolom: list[str]) -> pd.DataFrame:
    baris = []
    for r in records:
        b = {}
        for k in kolom:
            v = r.get(k)
            if isinstance(v, (list, tuple, set)):
                v = ";".join(map(str, v))
            b[k] = v
        baris.append(b)
    return pd.DataFrame(baris, columns=kolom, dtype=object)


def tulis_csv(df: pd.DataFrame, path: Path):
    df.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\n")


def tulis_jsonl(records: list[dict], kolom: list[str], path: Path):
    with path.open("w", encoding="utf-8", newline="\n") as s:
        for r in records:
            s.write(json.dumps({k: (";".join(map(str, r[k])) if isinstance(r.get(k), (list, set, tuple))
                                    else r.get(k)) for k in kolom}, ensure_ascii=False) + "\n")


def tabel_tahapan(n_raw, karantina, valid, unik):
    rows = [("1_record_raw_snapshot", n_raw, ""), ("2_karantina_invalid", len(karantina), "lihat karantina.csv"),
            ("3_record_valid", len(valid), "raw - karantina"),
            ("4_versi_id_sama_digabung", len(valid) - len(unik), "dedup (platform, post_id)"),
            ("5_post_unik", len(unik), "basis keputusan")]
    tahap = 6
    for status in ("exclude", "pending", "keep"):
        sub = [r for r in unik if r["status_final"] == status]
        rows.append((f"{tahap}_{status}_total", len(sub), "status akhir (tiap post tepat satu)"))
        alasan = {}
        for r in sub:
            alasan[r["alasan_utama"]] = alasan.get(r["alasan_utama"], 0) + 1
        for a, n in sorted(alasan.items(), key=lambda x: (-x[1], x[0])):
            rows.append((f"{tahap}.{status}:{a}", n, "alasan utama; tidak tumpang tindih"))
        tahap += 1
    df = pd.DataFrame(rows, columns=["tahap", "jumlah", "keterangan"])
    cek = (n_raw == len(karantina) + len(valid)
           and len(unik) == sum(r["status_final"] in ("exclude", "pending", "keep") for r in unik))
    return df, cek


def sampel_review(records: list[dict], seed=SEED, maks=MAKS_SAMPEL, n_kal=N_KALIBRASI):
    """Sampel diagnostik berstrata (status x fase x kolektor). Bobot = N_h / n_h.

    Bukan sampel acak sederhana: alokasi minimum per strata membuat strata kecil terwakili
    berlebih. Estimasi presisi keseluruhan harus memakai bobot; per strata boleh tanpa bobot.
    """
    strata = {}
    for r in records:
        if r["fase"] is None:
            continue
        kunci = (r["status_final"], r["fase"], keluarga_kolektor(r["collector"]))
        strata.setdefault(kunci, []).append(r)
    total = sum(len(v) for v in strata.values())
    if total == 0:
        return []
    alok = {k: min(len(v), 5) for k, v in strata.items()}
    sisa = max(0, maks - sum(alok.values()))
    for k, v in sorted(strata.items()):
        tambahan = int(round(sisa * len(v) / total))
        alok[k] = min(len(v), alok[k] + tambahan)
    while sum(alok.values()) > maks:  # koreksi pembulatan, potong dari strata terbesar
        k = max(alok, key=lambda x: (alok[x], x))
        alok[k] -= 1
    rng = random.Random(seed)
    hasil = []
    for k in sorted(strata):
        populasi = sorted(strata[k], key=lambda r: r["post_id"])
        pilih = rng.sample(populasi, alok[k]) if alok[k] else []
        for r in pilih:
            hasil.append(dict(r, strata="|".join(k), N_strata=len(populasi), n_strata=alok[k],
                              bobot=len(populasi) / alok[k]))
    urut = list(range(len(hasil)))
    rng.shuffle(urut)
    kal = set(urut[:n_kal])
    for i, r in enumerate(hasil):
        r["kalibrasi_dua_peninjau"] = int(i in kal)
    return hasil


KOLOM_ISIAN = ["reviewer", "keputusan_relevansi", "keputusan_promosi", "jenis_akun_manual", "privasi_ok",
               "sentimen_manual", "stance_manual", "aspek_manual", "catatan"]
KOLOM_REVIEW_INFO = ["platform", "post_id", "fase", "tanggal_wib", "status_final", "alasan_utama", "alasan_lain",
                     "relevansi_jalur", "relevansi_bukti", "promosi_keputusan_otomatis", "promosi_alasan",
                     "promosi_sinyal", "jenis_akun_otomatis", "content_type", "teks_berulang_n", "pii_flags",
                     "reviewers", "text_minimal"]


def lembar_review(records, kolom_tambahan=()):
    df = ke_frame(records, KOLOM_REVIEW_INFO + list(kolom_tambahan))
    for k in KOLOM_ISIAN:
        df[k] = ""
    return df


# ---------------------------------------------------------------------------
def proses(root: Path, snapshot_folder: Path, out_root: Path, annotations: Path) -> dict:
    from .snapshot import verifikasi_snapshot

    manifest = verifikasi_snapshot(snapshot_folder)
    sid = manifest["snapshot_id"]
    out = out_root / f"preprocess_{sid}"
    out.mkdir(parents=True, exist_ok=True)
    salt = muat_salt(root / config.FILE_SALT)
    manusia = review.keputusan_berlaku(review.baca_log(annotations))
    ringkas = {"snapshot_id": sid, "platform": {}}
    cfg = dict(
        tk2prep=VERSION, promosi=promosi.VERSION, relevansi=relevansi.VERSION, teks=teks.VERSI_TEKS,
        seed=SEED, maks_sampel=MAKS_SAMPEL, n_kalibrasi=N_KALIBRASI, min_token_pendek=MIN_TOKEN_PENDEK,
        near_dup=dict(ambang=duplikat.AMBANG_NEAR, min_chars=duplikat.MIN_CHARS, fitur="tfidf char_wb 3-5"),
        jendela_waktu=config.JENDELA_WAKTU, interval="[awal 00:00 WIB, akhir 00:00 WIB)",
        pola_relevan_khas=relevansi.POLA_PROGRAM_KHAS.pattern, pola_relevan_generik=relevansi.POLA_PROGRAM_GENERIK.pattern,
        pola_konteks=config.POLA_KONTEKS, kueri_jangkar_tunggal=config.KUERI_JANGKAR_KONTEKS,
        relevansi_konteks_diabaikan=config.RELEVANSI_KONTEKS_DIABAIKAN,
        akun_resmi=config.AKUN_RESMI, akun_media=config.AKUN_MEDIA, akun_dibuang=config.AKUN_DIBUANG,
        maks_hashtag=config.MAKS_HASHTAG, slang_v1=teks.SLANG_V1,
        leksikon_colloquial=dict(file=config.FILE_LEKSIKON, dipakai=False,
                                 alasan="banyak entri ambigu/konteks; hanya dicatat sebagai opsi"),
        salt="file lokal .salt (tidak disalin ke output)",
        annotations_dir=annotations.relative_to(root).as_posix() if annotations.is_relative_to(root) else str(annotations),
        n_keputusan_manusia=len(manusia),
    )
    (out / "config_preprocess.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    (out / "stopword_topik.txt").write_text("\n".join(teks.STOPWORD_TOPIK) + "\n", encoding="utf-8", newline="\n")
    vect = dict(
        tujuan="CountVectorizer untuk representasi topik BERTopic SETELAH embedding/clustering",
        input_kolom="text_topic_repr (atau text_embedding + parameter di bawah)",
        ngram_range=[1, 2], min_df=2, max_df=0.95, lowercase=True,
        token_pattern=r"(?u)\b[a-z][a-z]+\b", stop_words_file="stopword_topik.txt",
        stop_words_domain_opsional=["maganghub", "magang", "hub"],
        catatan=("Kata domain/negasi tidak dibuang secara default. Uji coba membuang istilah kueri "
                 "(stop_words_domain_opsional) perlu dibandingkan lewat koherensi/keterbacaan topik; "
                 "jangan dianggap otomatis lebih baik. Sumber: BERTopic tips 'Removing stop words' & "
                 "halaman Vectorizers."),
        embedding_input="text_embedding (konteks utuh, stopword tidak dibuang)",
    )
    (out / "vectorizer_config.json").write_text(json.dumps(vect, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")

    karantina_all, hitung_all, konflik_all = [], [], []
    for plat in ("x", "threads"):
        files = [f for f in manifest["files"] if f["platform"] == plat]
        if not files:
            continue
        valid, karantina, hitung = muat.muat_snapshot(snapshot_folder, files)
        karantina_all += karantina
        hitung_all += hitung
        unik, konflik = muat.dedup(valid)
        konflik_all += konflik
        recs = [perkaya(r, salt) for r in unik]
        duplikat.kelompokkan(recs)
        for r in recs:
            putuskan(r, manusia.get((r["platform"], r["post_id"])))
        recs.sort(key=lambda r: (r["created_at_utc"], r["post_id"]))
        tujuan = out if plat == "x" else out / "threads"
        tujuan.mkdir(exist_ok=True)
        ringkas["platform"][plat] = tulis_platform(tujuan, plat, recs, valid, karantina, files, snapshot_folder)

    tulis_csv(pd.DataFrame(karantina_all, columns=["platform", "source_file", "source_line", "post_id", "alasan",
                                                   "detail"]), out / "karantina.csv")
    tulis_csv(pd.DataFrame(hitung_all), out / "hitung_per_file.csv")
    tulis_csv(pd.DataFrame(konflik_all, columns=["platform", "post_id", "source_file", "source_line", "collector",
                                                 "scraped_at", "panjang_teks", "text_truncated",
                                                 "dipilih_sebagai_teks", *muat.METRIK]), out / "konflik_versi_id.csv")
    tulis_csv(laporan.kamus_data(), out / "kamus_data.csv")
    (out / "snapshot_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    laporan.tulis_panduan_label(out / "PANDUAN_LABEL.md")
    laporan.tulis_laporan(out, manifest, cfg, ringkas)
    return dict(out=out, ringkas=ringkas)


def tulis_platform(out: Path, plat: str, recs, valid, karantina, files, snapshot_folder) -> dict:
    n_raw = sum(f["n_records"] for f in files)
    df = ke_frame(recs, KOLOM_DATASET + ["alasan_lain"])
    tulis_csv(df, out / f"dataset_{plat}_semua_keputusan.csv")
    keep = [r for r in recs if r["status_final"] == "keep"]
    kol_model = [k for k in KOLOM_DATASET if k not in ("text_truncated_asal", "sumber_versi")]
    tulis_csv(ke_frame(keep, kol_model), out / f"model_ready_{plat}.csv")
    tulis_jsonl(keep, kol_model, out / f"model_ready_{plat}.jsonl")
    publik = [r for r in keep if (r.get("jenis_akun_manual") or r["jenis_akun_otomatis"])
              not in ("resmi", "media", "organisasi_lain")]
    tulis_csv(ke_frame(publik, kol_model), out / f"model_ready_{plat}_tanpa_resmi_media.csv")
    # Subset satu wakil per teks identik: opsional untuk BERTopic agar teks yang diunggah
    # berulang (mis. template iklan/pengumuman) tidak membentuk klaster semu. Bukan pengganti
    # korpus utama; frekuensi pengulangan tetap ada di teks_berulang_n.
    terlihat, unik = set(), []
    for r in keep:
        g = r.get("teks_berulang_grup")
        if g and g in terlihat:
            continue
        if g:
            terlihat.add(g)
        unik.append(r)
    tulis_csv(ke_frame(unik, kol_model), out / f"model_ready_{plat}_satu_per_teks_identik.csv")

    excl = [r for r in recs if r["status_final"] == "exclude"]
    tulis_csv(ke_frame(excl, ["platform", "post_id", "fase", "tanggal_wib", "alasan_utama", "alasan_lain",
                              "sumber_keputusan", "relevansi_jalur", "promosi_alasan", "promosi_sinyal",
                              "collector", "text_minimal"]), out / f"exclusion_log_{plat}.csv")
    pend = [r for r in recs if r["status_final"] == "pending"]
    tulis_csv(lembar_review(pend), out / f"antrean_review_{plat}.csv")
    # Sampel berstrata DIBEKUKAN sekali per folder output. Strata-nya memakai status_final, yang
    # bergeser setiap kali keputusan peninjau masuk; menggambar ulang akan membuat label yang
    # sudah diisi kehilangan populasi acuannya (bobot, N_strata, baris kalibrasi), sehingga
    # presisi dan kappa tidak lagi dapat dihitung. Hapus berkasnya bila memang ingin diundi ulang.
    berkas_sampel = out / f"sampel_review_{plat}.csv"
    if berkas_sampel.exists():
        with berkas_sampel.open(encoding="utf-8-sig", newline="") as s:
            n_sampel = sum(1 for _ in csv.DictReader(s))
    else:
        sampel = sampel_review(recs)
        tulis_csv(lembar_review(sampel, ["strata", "N_strata", "n_strata", "bobot",
                                         "kalibrasi_dua_peninjau"]), berkas_sampel)
        n_sampel = len(sampel)

    tahapan, cocok = tabel_tahapan(n_raw, karantina, valid, recs)
    tulis_csv(tahapan, out / f"tahapan_{plat}.csv")
    statistik = laporan.distribusi(out, plat, recs)
    if plat == "x":
        harian = pd.DataFrame(cakupan.cakupan_harian_x(snapshot_folder / "raw" / "_meta", config.JENDELA_WAKTU))
        hit = df.groupby(["tanggal_wib", "status_final"]).size().unstack(fill_value=0)
        harian = harian.merge(hit, how="left", left_on="tanggal", right_index=True).fillna(
            {k: 0 for k in ("exclude", "pending", "keep")})
        raw_per_hari = df.groupby("tanggal_wib").size().rename("post_unik")
        harian = harian.merge(raw_per_hari, how="left", left_on="tanggal", right_index=True)
        harian["post_unik"] = harian["post_unik"].fillna(0).astype(int)
        tulis_csv(harian, out / "cakupan_harian_x.csv")
        statistik["cakupan"] = harian
    else:
        tulis_csv(pd.DataFrame(cakupan.cakupan_threads(snapshot_folder / "raw" / "_meta")),
                  out / "cakupan_threads_log.csv")
    return dict(n_raw=n_raw, karantina=len(karantina), valid=len(valid), unik=len(recs),
                status={s: sum(r["status_final"] == s for r in recs) for s in ("keep", "pending", "exclude")},
                n_model_ready=len(keep), n_tanpa_resmi_media=len(publik), n_satu_per_teks=len(unik),
                n_sampel=n_sampel, rekonsiliasi_ok=cocok, tahapan=tahapan, statistik=statistik)
