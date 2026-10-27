"""Hitung kesepakatan (Cohen's kappa) antarpeninjau, atau satu peninjau pada dua kesempatan.

    python alat_review/kappa_kalibrasi.py                 # snapshot terbaru, X dan Threads
    python alat_review/kappa_kalibrasi.py --snapshot ID
    python alat_review/kappa_kalibrasi.py A.csv B.csv     # bandingkan dua berkas ekspor

Tanpa argumen berkas: membaca data/annotations/review_decisions_log.csv (hasil import-review)
dan baris `kalibrasi_dua_peninjau=1` dari sampel_review_<platform>.csv. Per peninjau dipakai
nilai tidak kosong terakhir per kolom, sama seperti tk2prep.review.keputusan_berlaku.

Dengan dua berkas: membandingkan baris yang post_id-nya ada di keduanya. Bila nama peninjaunya
sama, yang terukur adalah konsistensi satu orang pada dua kesempatan (test-retest), BUKAN
kesepakatan antarpeninjau, dan tidak boleh dilaporkan sebagai penggantinya.
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


def bandingkan_berkas(a_path: Path, b_path: Path):
    """Kesepakatan pada post_id yang ada di kedua berkas ekspor."""
    a = {r["post_id"]: r for r in baca(a_path) if (r.get("reviewer") or "").strip()}
    b = {r["post_id"]: r for r in baca(b_path) if (r.get("reviewer") or "").strip()}
    ov = sorted(set(a) & set(b))
    nama_a = sorted({a[p]["reviewer"].strip() for p in ov})
    nama_b = sorted({b[p]["reviewer"].strip() for p in ov})
    print(f"{a_path.name} ({', '.join(nama_a) or '-'}) vs {b_path.name} ({', '.join(nama_b) or '-'})")
    print(f"  post_id yang ada di keduanya: {len(ov)}")
    if nama_a == nama_b:
        print("  PERINGATAN: peninjau sama. Ini konsistensi satu orang (test-retest),")
        print("  bukan kesepakatan antarpeninjau.")
    if not ov:
        return
    for k in KOLOM:
        pasang = [(a[p][k].strip(), b[p][k].strip()) for p in ov
                  if a[p].get(k, "").strip() and b[p].get(k, "").strip()]
        if not pasang:
            continue
        x, y = zip(*pasang)
        setuju = sum(i == j for i, j in pasang) / len(pasang)
        kappa = cohen_kappa_score(x, y) if len(set(x) | set(y)) > 1 else float("nan")
        print(f"  {k}: n={len(pasang)}, setuju={setuju:.0%}, kappa={kappa:.2f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--snapshot")
    ap.add_argument("berkas", nargs="*", help="dua CSV ekspor untuk dibandingkan langsung")
    args = ap.parse_args()
    if args.berkas:
        if len(args.berkas) != 2:
            sys.exit("Beri tepat dua berkas, atau tidak sama sekali.")
        return bandingkan_berkas(Path(args.berkas[0]), Path(args.berkas[1]))
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
