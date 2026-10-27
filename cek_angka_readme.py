"""Cek bahwa angka utama di README masih sama dengan keluaran snapshot.

    python cek_angka_readme.py

Gagal keras kalau snapshot diproses ulang dan angkanya bergeser, supaya README tidak
diam-diam memuat angka lama. Perbarui DIHARAPKAN di bawah hanya setelah README diperbarui.
Hanya membaca; tidak mengubah apa pun.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / "data/processed/preprocess_20261026_3067bfd95e"
RAW = ROOT / "data/raw"

# Angka yang ditulis di README bagian "Temuan pengumpulan data".
DIHARAPKAN = {
    "x": {"unik": 5257, "keep": 4286, "pending": 52, "exclude": 919},
    "threads": {"unik": 6028, "keep": 3183, "pending": 20, "exclude": 2825},
}
GABUNGAN = {"unik": 11285, "keep": 7469, "pending": 72, "exclude": 3744}


def baca_tahapan(file):
    with open(file, encoding="utf-8-sig", newline="") as f:
        baris = {r["tahap"]: int(r["jumlah"]) for r in csv.DictReader(f)}
    return {
        "unik": baris["5_post_unik"],
        "keep": baris["8_keep_total"],
        "pending": baris["7_pending_total"],
        "exclude": baris["6_exclude_total"],
    }


def cek_sha256_raw(galat):
    manifest = json.loads((SNAPSHOT / "snapshot_manifest.json").read_text(encoding="utf-8"))
    for f in manifest["files"]:
        berkas = RAW / f["file"]
        if not berkas.exists():
            galat.append(f"{f['file']}: tidak ada di data/raw")
            continue
        h, sisa = hashlib.sha256(), f["byte_limit"]
        with open(berkas, "rb") as fh:
            while sisa > 0:
                blok = fh.read(min(1 << 20, sisa))
                if not blok:
                    break
                h.update(blok)
                sisa -= len(blok)
        if h.hexdigest() != f["sha256"]:
            galat.append(f"{f['file']}: sha256 tidak cocok dengan snapshot_manifest.json")


def main():
    galat = []
    cek_sha256_raw(galat)

    total = {k: 0 for k in GABUNGAN}
    for platform, diharapkan in DIHARAPKAN.items():
        file = SNAPSHOT / ("tahapan_x.csv" if platform == "x" else "threads/tahapan_threads.csv")
        nyata = baca_tahapan(file)
        for kunci, nilai in diharapkan.items():
            if nyata[kunci] != nilai:
                galat.append(f"{platform}.{kunci}: README {nilai}, snapshot {nyata[kunci]}")
            total[kunci] += nyata[kunci]
        # Rekonsiliasi: tiap unggahan unik tepat satu status.
        jumlah = nyata["keep"] + nyata["pending"] + nyata["exclude"]
        if jumlah != nyata["unik"]:
            galat.append(f"{platform}: keep+pending+exclude {jumlah} != unik {nyata['unik']}")

    for kunci, nilai in GABUNGAN.items():
        if total[kunci] != nilai:
            galat.append(f"gabungan.{kunci}: README {nilai}, snapshot {total[kunci]}")

    if galat:
        print("GAGAL")
        for g in galat:
            print("  -", g)
        sys.exit(1)
    print("OK: sha256 data mentah dan semua angka utama README cocok dengan snapshot.")


if __name__ == "__main__":
    main()
