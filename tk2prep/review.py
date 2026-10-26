"""Keputusan manusia: impor, simpan append-only, dan gabungkan berdasarkan (platform, post_id).

- Penyimpanan permanen di data/annotations/ (di luar folder output versi), sehingga rerun
  preprocessing tidak pernah menimpa keputusan lama.
- review_decisions_log.csv : append-only, setiap impor menambah baris (riwayat lengkap).
- Keputusan berlaku per (platform, post_id, reviewer) = baris terakhir reviewer tersebut.
- Sel kosong pada file impor TIDAK menghapus keputusan lama (kosong = tidak memberi keputusan).
- Bila beberapa reviewer tidak sepakat, status menjadi 'konflik' (pending), bukan dipilih otomatis.
- Label buatan aturan/agent bukan keputusan manusia; impor menolak reviewer berlabel 'auto'/'agent'.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

FIELD_KEPUTUSAN = {
    "keputusan_relevansi": {"relevan", "tidak_relevan", "ragu"},
    "keputusan_promosi": {"bukan_iklan", "iklan", "ragu"},
    "jenis_akun_manual": {"publik", "resmi", "media", "organisasi_lain", "ragu"},
    "privasi_ok": {"ya", "tidak"},
    "sentimen_manual": {"positif", "negatif", "netral", "campuran", "ragu"},
    "stance_manual": {"mendukung", "menolak", "netral_tidak_jelas", "tidak_berlaku"},
    "aspek_manual": None,  # teks bebas/terkontrol di panduan; tidak divalidasi ketat
}
KOLOM_LOG = ["platform", "post_id", "reviewer", *FIELD_KEPUTUSAN, "catatan", "imported_at", "source_file"]
REVIEWER_TERLARANG = {"auto", "otomatis", "agent", "claude", "model", "rule"}


def _baca_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as s:
        return list(csv.DictReader(s))


def baca_log(folder: Path) -> list[dict]:
    return _baca_csv(folder / "review_decisions_log.csv")


def impor(file_isi: Path, folder: Path, waktu: datetime | None = None) -> dict:
    """Tambahkan keputusan dari CSV yang sudah diisi ke log append-only. Kembalikan ringkasan."""
    folder.mkdir(parents=True, exist_ok=True)
    waktu = (waktu or datetime.now(timezone.utc)).isoformat()
    baris_baru, ditolak = [], []
    for nomor, r in enumerate(_baca_csv(file_isi), start=2):
        isi = {k: (r.get(k) or "").strip() for k in FIELD_KEPUTUSAN}
        if not any(isi.values()):
            continue  # baris belum ditinjau
        reviewer = (r.get("reviewer") or "").strip()
        pid, plat = (r.get("post_id") or "").strip(), (r.get("platform") or "").strip()
        masalah = []
        if not reviewer:
            masalah.append("reviewer_kosong")
        elif reviewer.lower() in REVIEWER_TERLARANG:
            masalah.append("reviewer_bukan_manusia")
        if not pid or not plat:
            masalah.append("post_id_atau_platform_kosong")
        if pid and ("e+" in pid.lower() or pid.endswith(".0")):
            masalah.append("post_id_rusak_format_angka_spreadsheet")
        for k, nilai in isi.items():
            boleh = FIELD_KEPUTUSAN[k]
            if nilai and boleh is not None and nilai not in boleh:
                masalah.append(f"{k}_tidak_valid:{nilai}")
        if masalah:
            ditolak.append(dict(baris=nomor, post_id=pid, masalah=";".join(masalah)))
            continue
        baris_baru.append(dict(platform=plat, post_id=pid, reviewer=reviewer, **isi,
                               catatan=(r.get("catatan") or "").strip(), imported_at=waktu,
                               source_file=file_isi.name))
    log_path = folder / "review_decisions_log.csv"
    baru = not log_path.exists()
    with log_path.open("a", encoding="utf-8-sig" if baru else "utf-8", newline="") as s:
        w = csv.DictWriter(s, fieldnames=KOLOM_LOG)
        if baru:
            w.writeheader()
        w.writerows(baris_baru)
    if ditolak:
        with (folder / f"impor_ditolak_{file_isi.stem}.csv").open("w", encoding="utf-8-sig", newline="") as s:
            w = csv.DictWriter(s, fieldnames=["baris", "post_id", "masalah"])
            w.writeheader()
            w.writerows(ditolak)
    return dict(diterima=len(baris_baru), ditolak=len(ditolak))


def keputusan_berlaku(log: list[dict]) -> dict:
    """{(platform, post_id): {field: nilai_konsensus|'konflik', 'reviewers': [...]}}.

    Per reviewer, nilai tidak kosong terakhir per field berlaku (keputusan lama tidak hilang
    hanya karena impor berikutnya mengosongkan field itu).
    """
    per_reviewer: dict[tuple, dict] = {}
    for r in log:
        kunci = (r["platform"], r["post_id"], r["reviewer"])
        cur = per_reviewer.setdefault(kunci, {})
        for k in FIELD_KEPUTUSAN:
            if (r.get(k) or "").strip():
                cur[k] = r[k].strip()
    hasil: dict[tuple, dict] = {}
    for (plat, pid, reviewer), nilai in per_reviewer.items():
        h = hasil.setdefault((plat, pid), {"reviewers": [], "_nilai": {}})
        h["reviewers"].append(reviewer)
        for k, v in nilai.items():
            h["_nilai"].setdefault(k, set()).add(v)
    for h in hasil.values():
        for k, vs in h.pop("_nilai").items():
            h[k] = next(iter(vs)) if len(vs) == 1 else "konflik"
        h["reviewers"] = sorted(h["reviewers"])
    return hasil
