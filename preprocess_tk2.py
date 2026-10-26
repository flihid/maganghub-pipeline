"""Entry point preprocessing TK2 (terpisah dari kolektor dan 03_preprocess.py lama).

    python preprocess_tk2.py snapshot                 # bekukan raw -> data/interim/snapshots/<id>/
    python preprocess_tk2.py run [--snapshot ID]      # proses snapshot -> data/processed/preprocess_<id>/
    python preprocess_tk2.py import-review FILE.csv   # tambah keputusan manusia (append-only)
    python preprocess_tk2.py audit [--snapshot ID]    # cek rekonsiliasi & integritas output
    python preprocess_tk2.py all                      # snapshot + run + audit

Tidak menghentikan/menjalankan kolektor, tidak membaca kredensial, tidak mengubah data/raw.
"""
import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from tk2prep import pipeline, review, snapshot  # noqa: E402

RAW = ROOT / config.DIR_RAW
SNAP = ROOT / "data/interim/snapshots"
OUT = ROOT / config.DIR_PROCESSED
ANN = ROOT / "data/annotations"


def pilih_snapshot(sid):
    if sid:
        return SNAP / sid
    semua = sorted(SNAP.glob("*/snapshot_manifest.json"), key=lambda p: json.loads(
        p.read_text(encoding="utf-8"))["created_utc"])
    if not semua:
        sys.exit("Belum ada snapshot. Jalankan: python preprocess_tk2.py snapshot")
    return semua[-1].parent


def cmd_snapshot(_):
    m = snapshot.buat_snapshot(ROOT, RAW, SNAP)
    print(f"Snapshot {m['snapshot_id']}")
    for f in m["files"]:
        tail = f" (sisa belum lengkap {f['incomplete_tail_bytes']} byte, tidak diambil)" if f["incomplete_tail_bytes"] else ""
        print(f"  {f['file']}: {f['n_records']} record{tail}")
    return m["snapshot_id"]


def cmd_run(args):
    folder = pilih_snapshot(args.snapshot)
    hasil = pipeline.proses(ROOT, folder, OUT, ANN)
    print(f"Output: {hasil['out'].relative_to(ROOT)}")
    for plat, s in hasil["ringkas"]["platform"].items():
        print(f"  {plat}: raw={s['n_raw']} karantina={s['karantina']} unik={s['unik']} "
              f"keep={s['status']['keep']} pending={s['status']['pending']} exclude={s['status']['exclude']} "
              f"rekonsiliasi={'OK' if s['rekonsiliasi_ok'] else 'GAGAL'}")
    return hasil


def cmd_import(args):
    r = review.impor(Path(args.file), ANN)
    print(f"Diterima {r['diterima']} baris keputusan; ditolak {r['ditolak']}"
          + (f" (lihat {ANN.relative_to(ROOT)}/impor_ditolak_*.csv)" if r["ditolak"] else ""))
    print("Jalankan ulang: python preprocess_tk2.py run")


def cmd_audit(args):
    import pandas as pd
    folder = pilih_snapshot(args.snapshot)
    m = snapshot.verifikasi_snapshot(folder)
    out = OUT / f"preprocess_{m['snapshot_id']}"
    masalah = []
    for plat in ("x", "threads"):
        base = out if plat == "x" else out / "threads"
        f = base / f"dataset_{plat}_semua_keputusan.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f, dtype={"post_id": str}, keep_default_na=False)
        n_raw = sum(x["n_records"] for x in m["files"] if x["platform"] == plat)
        kar = pd.read_csv(out / "karantina.csv", dtype=str, keep_default_na=False)
        kar = kar[kar.platform == plat]
        hit = pd.read_csv(out / "hitung_per_file.csv")
        valid = int(hit[hit.platform == plat].valid.sum())
        if n_raw != valid + len(kar):
            masalah.append(f"{plat}: raw {n_raw} != valid {valid} + karantina {len(kar)}")
        if df.duplicated(["platform", "post_id"]).any():
            masalah.append(f"{plat}: (platform, post_id) duplikat di output")
        if plat == "x" and not df.post_id.str.fullmatch(r"\d+").all():
            masalah.append("x: post_id bukan string digit (kemungkinan rusak)")
        mr = pd.read_csv(base / f"model_ready_{plat}.csv", dtype={"post_id": str})
        if len(mr) != (df.status_final == "keep").sum():
            masalah.append(f"{plat}: model_ready tidak sama dengan status keep")
        for kol in ("username", "url"):
            if kol in df.columns:
                masalah.append(f"{plat}: kolom identitas {kol} ikut keluar")
        print(f"{plat}: raw={n_raw} valid={valid} karantina={len(kar)} unik={len(df)} "
              f"status={df.status_final.value_counts().to_dict()}")
    print("Audit OK" if not masalah else "MASALAH:\n  " + "\n  ".join(masalah))
    return masalah


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("snapshot")
    for n in ("run", "audit"):
        p = sub.add_parser(n)
        p.add_argument("--snapshot", help="ID snapshot (default: terbaru)")
    p = sub.add_parser("import-review")
    p.add_argument("file")
    sub.add_parser("all")
    args = ap.parse_args()
    if args.cmd == "snapshot":
        cmd_snapshot(args)
    elif args.cmd == "run":
        cmd_run(args)
    elif args.cmd == "import-review":
        cmd_import(args)
    elif args.cmd == "audit":
        sys.exit(1 if cmd_audit(args) else 0)
    else:
        args.snapshot = cmd_snapshot(args)
        cmd_run(args)
        sys.exit(1 if cmd_audit(args) else 0)


if __name__ == "__main__":
    main()
