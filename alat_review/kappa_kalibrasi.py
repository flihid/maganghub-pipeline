"""Hitung kesepakatan dua peninjau (Cohen's kappa) pada baris kalibrasi sampel review.

    python alat_review/kappa_kalibrasi.py                 # snapshot terbaru, X dan Threads
    python alat_review/kappa_kalibrasi.py --snapshot ID

Membaca data/annotations/review_decisions_log.csv (hasil import-review) dan baris
`kalibrasi_dua_peninjau=1` dari sampel_review_<platform>.csv. Per peninjau dipakai nilai
tidak kosong terakhir per kolom, sama seperti tk2prep.review.keputusan_berlaku.
"""
import argparse
import csv
import json
import sys
from itertools import combinations
from pathlib import Path

from sklearn.metrics import cohen_kappa_score

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tk2prep import review  # noqa: E402

KOLOM = ["keputusan_relevansi", "keputusan_promosi", "sentimen_manual", "stance_manual"]


def baca(path):
    with path.open(encoding="utf-8-sig", newline="") as s:
        return list(csv.DictReader(s))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--snapshot")
    args = ap.parse_args()
    out = ROOT / "data/processed"
    # Nama folder memuat tanggal + hash isi, sehingga urutan abjad bukan urutan waktu.
    folder = (out / f"preprocess_{args.snapshot}" if args.snapshot else
              max(out.glob("preprocess_*/snapshot_manifest.json"),
                  key=lambda f: json.loads(f.read_text(encoding="utf-8"))["created_utc"]).parent)
    log = review.baca_log(ROOT / "data/annotations")
    if not log:
        sys.exit("Belum ada keputusan. Jalankan dulu: python preprocess_tk2.py import-review <file>")

    nilai = {}  # (platform, post_id) -> reviewer -> kolom -> nilai
    for r in log:
        cur = nilai.setdefault((r["platform"], r["post_id"]), {}).setdefault(r["reviewer"], {})
        for k in KOLOM:
            if (r.get(k) or "").strip():
                cur[k] = r[k].strip()

    print(f"Snapshot: {folder.name}")
    for platform, sampel in [("x", folder / "sampel_review_x.csv"),
                             ("threads", folder / "threads/sampel_review_threads.csv")]:
        kal = [r["post_id"] for r in baca(sampel) if r.get("kalibrasi_dua_peninjau") == "1"]
        reviewers = sorted({rv for pid in kal for rv in nilai.get((platform, pid), {})})
        print(f"\n== {platform}: {len(kal)} baris kalibrasi, peninjau: {', '.join(reviewers) or '-'}")
        if len(reviewers) < 2:
            print("   Butuh label dari dua peninjau.")
            continue
        for a, b in combinations(reviewers, 2):
            for k in KOLOM:
                pasang = [(nilai[(platform, pid)][a][k], nilai[(platform, pid)][b][k]) for pid in kal
                          if k in nilai.get((platform, pid), {}).get(a, {})
                          and k in nilai.get((platform, pid), {}).get(b, {})]
                if not pasang:
                    continue
                x, y = zip(*pasang)
                setuju = sum(i == j for i, j in pasang) / len(pasang)
                kappa = cohen_kappa_score(x, y) if len(set(x) | set(y)) > 1 else float("nan")
                print(f"   {a} vs {b} | {k}: n={len(pasang)}, setuju={setuju:.0%}, kappa={kappa:.2f}")


if __name__ == "__main__":
    main()
