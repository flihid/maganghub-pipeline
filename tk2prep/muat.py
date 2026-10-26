"""Parse JSONL snapshot, validasi per record, karantina, dan dedup (platform, post_id).

Prinsip (Modul 05 hlm. 9, 24-26):
- missing != nol: engagement yang tidak ada tetap None, tidak diisi 0.
- ID selalu string (ID X 19 digit tidak boleh lewat float).
- Record invalid dikarantina dengan alasan, bukan dibuang diam-diam.
- Author kosong boleh dipertahankan, tetapi tidak diberi satu identitas palsu bersama.
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

METRIK = ("n_reply", "n_repost", "n_like", "n_quote")


def pisah_baris_jsonl(data: bytes):
    """Pisah HANYA pada newline fisik b'\\n' (bukan str.splitlines, yang ikut memecah U+2028/U+2029)."""
    for nomor, baris in enumerate(data.split(b"\n"), start=1):
        if baris.strip():
            yield nomor, baris


def normalisasi_bool(nilai):
    """True/False/None dari flag lama bool/string/float/null. None = tidak diketahui."""
    if nilai is None:
        return None
    if isinstance(nilai, bool):
        return nilai
    if isinstance(nilai, (int, float)):
        if isinstance(nilai, float) and math.isnan(nilai):
            return None
        return bool(nilai)
    teks = str(nilai).strip().lower()
    if teks in ("true", "1", "1.0", "yes", "ya"):
        return True
    if teks in ("false", "0", "0.0", "no", "tidak"):
        return False
    return None  # "", "null", "none", "nan", nilai aneh -> unknown


def normalisasi_metrik(nilai):
    """Kembalikan (angka|None, flag_masalah|None). Missing tetap None; negatif/aneh -> None + flag."""
    if nilai is None:
        return None, None
    if isinstance(nilai, bool):
        return None, "metrik_bertipe_bool"
    if isinstance(nilai, (int, float)):
        if isinstance(nilai, float) and (math.isnan(nilai) or not nilai.is_integer()):
            return None, "metrik_bukan_bilangan_bulat"
        angka = int(nilai)
    else:
        teks = str(nilai).strip().replace(",", "")
        if teks == "" or teks.lower() in ("null", "none", "nan"):
            return None, None
        if not teks.lstrip("-").isdigit():
            return None, "metrik_tidak_numerik"
        angka = int(teks)
    if angka < 0:
        return None, "metrik_negatif"
    return angka, None


def parse_waktu(nilai):
    """datetime timezone-aware atau (None, alasan)."""
    if not isinstance(nilai, str) or not nilai.strip():
        return None, "timestamp_kosong"
    teks = nilai.strip()
    if teks.endswith("Z"):
        teks = teks[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(teks)
    except ValueError:
        return None, "timestamp_tidak_valid"
    if dt.tzinfo is None or dt.utcoffset() is None:
        return None, "timestamp_tanpa_zona_waktu"
    return dt, None


def validasi_record(obj: dict, platform: str, file: str, nomor: int):
    """Kembalikan (record_normal, None) atau (None, alasan_karantina)."""
    if not isinstance(obj, dict):
        return None, "bukan_objek_json"
    flags = []
    pid = obj.get("tweet_id", obj.get("post_id"))
    if isinstance(pid, bool) or pid is None or str(pid).strip() == "":
        return None, "post_id_kosong"
    if isinstance(pid, float):
        return None, "post_id_float_presisi_hilang"
    if isinstance(pid, int):
        flags.append("post_id_numerik_dikonversi_string")
    pid = str(pid).strip()
    teks = obj.get("text")
    if not isinstance(teks, str) or not teks.strip():
        return None, "teks_kosong"
    dt, alasan = parse_waktu(obj.get("created_at"))
    if dt is None:
        return None, alasan
    plat_rec = obj.get("platform")
    if plat_rec not in (None, platform):
        return None, f"platform_tidak_konsisten_{plat_rec}"
    rec = dict(
        platform=platform, post_id=pid, created_at_asal=obj.get("created_at"), created_at=dt,
        username=(obj.get("username") or None), text=teks,
        post_lang=obj.get("post_lang") or None, conversation_id=(str(obj["conversation_id"])
                                                                if obj.get("conversation_id") not in (None, "") else None),
        content_type=obj.get("content_type") or None,
        kueri=obj.get("kueri") or None, language_filter=obj.get("language_filter") or None,
        job_since=obj.get("since"), job_until=obj.get("until"), fase_raw=obj.get("fase"),
        scraped_at=obj.get("scraped_at"), collector=obj.get("collector") or ("threads_playwright"
                                                                              if platform == "threads" else None),
        adapter_version=obj.get("adapter_version"), query_window=obj.get("query_window"),
        text_truncated=normalisasi_bool(obj.get("text_truncated")),
        text_truncated_asal=repr(obj.get("text_truncated")),
        source_file=file, source_line=nomor,
    )
    if rec["username"] is None:
        flags.append("author_missing")
    am = normalisasi_bool(obj.get("author_missing"))
    if am and rec["username"] is not None:
        flags.append("author_missing_flag_tidak_konsisten")
    for m in METRIK:
        if m not in obj:
            rec[m] = None
            flags.append(f"{m}_tidak_dikumpulkan")
            continue
        angka, masalah = normalisasi_metrik(obj.get(m))
        rec[m] = angka
        if masalah:
            flags.append(f"{m}_{masalah}")
    rec["flags_validasi"] = flags
    return rec, None


def muat_snapshot(folder: Path, files: list[dict]):
    """Baca file snapshot. Kembalikan (records_valid, karantina, hitung_per_file)."""
    valid, karantina, hitung = [], [], []
    for f in files:
        data = (folder / "raw" / f["file"]).read_bytes()
        n_ok = n_bad = 0
        for nomor, baris in pisah_baris_jsonl(data):
            try:
                obj = json.loads(baris.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                karantina.append(dict(platform=f["platform"], source_file=f["file"], source_line=nomor,
                                      post_id=None, alasan="json_tidak_valid", detail=type(exc).__name__))
                n_bad += 1
                continue
            rec, alasan = validasi_record(obj, f["platform"], f["file"], nomor)
            if rec is None:
                pid = obj.get("tweet_id") if isinstance(obj, dict) else None
                karantina.append(dict(platform=f["platform"], source_file=f["file"], source_line=nomor,
                                      post_id=None if pid is None else str(pid), alasan=alasan, detail=""))
                n_bad += 1
            else:
                valid.append(rec)
                n_ok += 1
        hitung.append(dict(platform=f["platform"], file=f["file"], records=f["n_records"], valid=n_ok,
                           karantina=n_bad))
    return valid, karantina, hitung


def _peringkat_versi(rec):
    """Urutan pemilihan teks: bukan terpotong-pasti > lebih panjang > lebih baru diambil.

    text_truncated=None berarti TIDAK DIKETAHUI, jadi tidak dianggap bukti teks lengkap;
    hanya False yang diberi prioritas di atas None.
    """
    status = {False: 2, None: 1, True: 0}[rec["text_truncated"]]
    return (status, len(rec["text"].strip()), rec.get("scraped_at") or "")


def dedup(records: list[dict]):
    """Satu baris per (platform, post_id). Simpan konflik teks/metrik dan provenance versi."""
    grup: dict[tuple, list] = {}
    for r in records:
        grup.setdefault((r["platform"], r["post_id"]), []).append(r)
    hasil, konflik = [], []
    for kunci, versi in grup.items():
        terpilih = dict(max(versi, key=_peringkat_versi))
        terbaru = max(versi, key=lambda r: r.get("scraped_at") or "")
        # Engagement berubah antarwaktu: pakai pengambilan terbaru dan catat waktunya.
        for m in METRIK:
            terpilih[m] = terbaru[m]
        terpilih["metrik_scraped_at"] = terbaru.get("scraped_at")
        teks_unik = {v["text"].strip() for v in versi}
        terpilih["n_versi"] = len(versi)
        terpilih["konflik_teks"] = len(teks_unik) > 1
        terpilih["konflik_metrik"] = len({tuple(v[m] for m in METRIK) for v in versi}) > 1
        terpilih["sumber_versi"] = ";".join(sorted({f"{v['source_file']}:{v['source_line']}|{v['collector']}"
                                                    for v in versi}))
        terpilih["kueri_semua"] = sorted({v["kueri"] for v in versi if v["kueri"]})
        terpilih["flags_validasi"] = sorted({f for v in versi for f in v["flags_validasi"]})
        if len(versi) > 1:
            for v in versi:
                konflik.append(dict(platform=kunci[0], post_id=kunci[1], source_file=v["source_file"],
                                    source_line=v["source_line"], collector=v["collector"],
                                    scraped_at=v.get("scraped_at"), panjang_teks=len(v["text"]),
                                    text_truncated=v["text_truncated"],
                                    dipilih_sebagai_teks=(v["source_file"], v["source_line"]) ==
                                    (terpilih["source_file"], terpilih["source_line"]),
                                    **{m: v[m] for m in METRIK}))
        hasil.append(terpilih)
    hasil.sort(key=lambda r: (r["platform"], r["created_at"], r["post_id"]))
    return hasil, konflik
