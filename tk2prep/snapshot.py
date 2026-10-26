"""Bekukan input raw JSONL tanpa mengubah file raw.

Cara kerja: setiap file dibaca SEKALI sebagai bytes sampai ukuran saat dibaca, lalu
dipotong pada newline fisik terakhir (b"\\n"). Potongan akhir yang belum lengkap
(kolektor sedang menulis) tidak diambil; jumlah byte-nya dicatat agar run berikutnya
tahu batasnya. Salinan byte yang diambil disimpan di data/interim/snapshots/<id>/raw/
(diabaikan Git karena masih memuat username), sedangkan manifest mencatat batas byte
dan SHA-256 sehingga snapshot bisa direkonstruksi dari raw yang bersifat append-only.

Pembacaan antarfile berurutan, BUKAN atomic: file yang dibaca belakangan bisa memuat
record yang ditulis sesudah file pertama dibaca. Manifest menyebut ini apa adanya.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from zoneinfo import ZoneInfo

from . import VERSION

WIB = ZoneInfo("Asia/Jakarta")
POLA_FILE = {"x": "x_*.jsonl", "threads": "threads_*.jsonl"}
# Metadata kolektor yang ikut dibekukan untuk audit cakupan (tanpa kredensial).
FILE_PENDUKUNG = ["browser_collection_log.jsonl", "browser_jobs.json", "twscrape_state_*.json",
                  "log_scraping_threads.csv", "progres_threads.json"]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def potong_record_lengkap(data: bytes) -> tuple[bytes, int]:
    """Kembalikan (bytes sampai newline terakhir, jumlah byte sisa yang belum lengkap)."""
    akhir = data.rfind(b"\n")
    if akhir < 0:
        return b"", len(data)
    return data[: akhir + 1], len(data) - akhir - 1


def hitung_record(data: bytes) -> int:
    return sum(1 for baris in data.split(b"\n") if baris.strip())


def versi_dependensi() -> dict:
    hasil = {"python": sys.version.split()[0], "platform": platform.platform()}
    for paket in ("pandas", "numpy", "scikit-learn", "twscrape"):
        try:
            hasil[paket] = metadata.version(paket)
        except metadata.PackageNotFoundError:
            hasil[paket] = None
    return hasil


def versi_kode(root: Path) -> dict:
    """Commit Git (dibaca dari .git tanpa menjalankan git) + hash file kode preprocessing."""
    info = {"tk2prep": VERSION, "git_head": None, "git_dirty_unknown": True}
    head = root / ".git" / "HEAD"
    try:
        ref = head.read_text(encoding="utf-8").strip()
        if ref.startswith("ref: "):
            ref_file = root / ".git" / ref[5:]
            if ref_file.exists():
                info["git_head"] = ref_file.read_text(encoding="utf-8").strip()
            else:
                packed = (root / ".git" / "packed-refs")
                for line in packed.read_text(encoding="utf-8").splitlines() if packed.exists() else []:
                    if line.endswith(ref[5:]):
                        info["git_head"] = line.split()[0]
        else:
            info["git_head"] = ref
    except OSError:
        pass
    kode = sorted([*root.glob("tk2prep/*.py"), root / "preprocess_tk2.py", root / "promosi.py",
                   root / "relevansi.py", root / "config.py"])
    info["file_hash"] = {p.relative_to(root).as_posix(): sha256(p.read_bytes())[:16]
                         for p in kode if p.exists()}
    return info


def buat_snapshot(root: Path, raw_dir: Path, out_root: Path, platforms=("x", "threads")) -> dict:
    """Bekukan raw, tulis salinan + manifest, kembalikan manifest. Idempoten untuk input sama."""
    waktu = datetime.now(timezone.utc)
    files = []
    potongan = {}
    for plat in platforms:
        for f in sorted(raw_dir.glob(POLA_FILE[plat])):
            data = f.read_bytes()  # satu kali baca; ukuran saat itu = batas atas
            lengkap, sisa = potong_record_lengkap(data)
            potongan[f.name] = lengkap
            files.append(dict(platform=plat, file=f.name, size_at_read=len(data), byte_limit=len(lengkap),
                              incomplete_tail_bytes=sisa, n_records=hitung_record(lengkap),
                              sha256=sha256(lengkap)))
    pendukung = []
    for pola in FILE_PENDUKUNG:
        for f in sorted(raw_dir.glob(pola)):
            data = f.read_bytes()
            potongan["_meta/" + f.name] = data
            pendukung.append(dict(file=f.name, size_at_read=len(data), sha256=sha256(data)))
    # ID snapshot hanya bergantung pada isi data yang dibekukan, sehingga input yang sama
    # menghasilkan ID dan output yang sama (idempoten).
    kunci = json.dumps([(f["file"], f["sha256"]) for f in files], sort_keys=True).encode()
    snapshot_id = waktu.astimezone(WIB).strftime("%Y%m%d") + "_" + sha256(kunci)[:10]
    # Jika isi identik dengan snapshot yang sudah ada (tanggal berbeda), pakai yang lama.
    for lama in sorted(out_root.glob("*_" + sha256(kunci)[:10])):
        snapshot_id = lama.name
    folder = out_root / snapshot_id
    (folder / "raw" / "_meta").mkdir(parents=True, exist_ok=True)
    for nama, data in potongan.items():
        tujuan = folder / "raw" / nama
        if not tujuan.exists() or tujuan.read_bytes() != data:
            tujuan.write_bytes(data)
    manifest_path = folder / "snapshot_manifest.json"
    if manifest_path.exists():
        # Isi sama -> manifest lama dipakai apa adanya (tidak ditulis ulang).
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = dict(
        snapshot_id=snapshot_id,
        created_utc=waktu.isoformat(),
        created_wib=waktu.astimezone(WIB).isoformat(),
        method=("Per-file sequential read of bytes up to size at read time, truncated at the last "
                "physical newline. NOT atomic across files. Raw files were not modified."),
        raw_dir=raw_dir.relative_to(root).as_posix() if raw_dir.is_relative_to(root) else str(raw_dir),
        files=files,
        supporting_files=pendukung,
        totals={p: dict(files=sum(f["platform"] == p for f in files),
                        records=sum(f["n_records"] for f in files if f["platform"] == p))
                for p in platforms},
        code=versi_kode(root),
        dependencies=versi_dependensi(),
        note="No environment variables, cookies, or session databases are read or stored.",
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def verifikasi_snapshot(folder: Path) -> dict:
    """Pastikan salinan snapshot cocok dengan hash di manifest sebelum diproses."""
    manifest = json.loads((folder / "snapshot_manifest.json").read_text(encoding="utf-8"))
    for f in manifest["files"]:
        data = (folder / "raw" / f["file"]).read_bytes()
        if sha256(data) != f["sha256"] or len(data) != f["byte_limit"]:
            raise ValueError(f"Snapshot {f['file']} tidak cocok dengan manifest")
    return manifest


def rekonstruksi_dari_raw(manifest: dict, raw_dir: Path, folder: Path) -> None:
    """Bangun ulang salinan snapshot dari raw append-only memakai batas byte + hash."""
    (folder / "raw").mkdir(parents=True, exist_ok=True)
    for f in manifest["files"]:
        with (raw_dir / f["file"]).open("rb") as stream:
            data = stream.read(f["byte_limit"])
        if sha256(data) != f["sha256"]:
            raise ValueError(f"{f['file']}: raw sudah berubah sebelum batas byte; tidak bisa direkonstruksi")
        (folder / "raw" / f["file"]).write_bytes(data)
