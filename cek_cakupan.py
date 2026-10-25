"""
Cek cakupan data mentah per platform dan kata kunci, SEBELUM preprocessing.

Menjawab tiga pertanyaan untuk laporan bagian C4 dan C5:
  - Berapa post yang terkumpul per kata kunci?
  - Apakah rentang tanggalnya mencakup seluruh jendela penelitian?
    (kolom `tertua` harus <= awal fase 1; jika tidak, fase awal kurang terwakili)
  - Berapa persen yang relevan menurut aturan dua jalur di relevansi.py (presisi kata kunci)?

Cara pakai (PowerShell):
    python cek_cakupan.py
    python cek_cakupan.py --contoh maganghub     # tampilkan 10 post TIDAK relevan dari kata kunci itu
"""

import argparse
import glob
import json
import sys

import pandas as pd

import config
from relevansi import tandai_relevansi

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def muat() -> pd.DataFrame:
    rows = []
    for pola, platform in [("data/raw/x_*.jsonl", "x"), ("data/raw/threads_*.jsonl", "threads")]:
        for f in glob.glob(pola):
            with open(f, encoding="utf-8") as fh:
                for baris in fh:
                    if baris.strip():
                        r = json.loads(baris)
                        r["platform"] = platform
                        rows.append(r)
    if not rows:
        sys.exit("Belum ada data di data/raw/.")
    # Dedup hanya di dalam kata kunci yang sama, supaya statistik per kata kunci
    # menghitung semua post yang dijaring kata kunci itu.
    d = pd.DataFrame(rows).drop_duplicates(["platform", "tweet_id", "kueri"])
    d["tgl"] = pd.to_datetime(d["created_at"], utc=True, format="ISO8601").dt.tz_convert("Asia/Jakarta").dt.strftime("%Y-%m-%d")
    d["dasar"] = tandai_relevansi(d)
    d["relevan"] = d["dasar"] != ""
    d["eksplisit"] = d["dasar"] == "eksplisit"
    awal = min(s for s, _ in config.JENDELA_WAKTU.values())
    akhir = max(u for _, u in config.JENDELA_WAKTU.values())
    d["di_jendela"] = (d["tgl"] >= awal) & (d["tgl"] < akhir)
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contoh", help="kata kunci yang ingin dilihat contoh post tidak relevannya")
    args = ap.parse_args()
    d = muat()
    awal = min(s for s, _ in config.JENDELA_WAKTU.values())

    g = d.groupby(["platform", "kueri"]).agg(
        jumlah=("tweet_id", "size"), tertua=("tgl", "min"), terbaru=("tgl", "max"),
        pct_eksplisit=("eksplisit", "mean"), pct_relevan_total=("relevan", "mean"),
        pct_di_jendela=("di_jendela", "mean"),
    )
    g["cakup_fase1"] = (g["tertua"] <= awal).map({True: "ya", False: "TIDAK"})
    for k in ["pct_eksplisit", "pct_relevan_total", "pct_di_jendela"]:
        g[k] = (g[k] * 100).round().astype(int).astype(str) + "%"
    print(g.to_string())
    print("(pct_eksplisit = menyebut nama program; pct_relevan_total = eksplisit + jalur konteks)")
    print()

    unik = d.drop_duplicates(["platform", "tweet_id"])
    pakai = unik[unik["relevan"] & unik["di_jendela"]]
    jalur = pakai["dasar"].value_counts().to_dict()
    print(f"Total unik: {len(unik)} | relevan DAN di jendela penelitian: {len(pakai)} "
          f"(eksplisit {jalur.get('eksplisit', 0)}, konteks {jalur.get('konteks', 0)})")
    print()
    print("Sebaran post yang relevan per fase:")
    def fase(t):
        for nama, (s, u) in config.JENDELA_WAKTU.items():
            if s <= t < u:
                return nama
    print(pakai.assign(fase=pakai["tgl"].map(fase)).groupby(["platform", "fase"]).size().to_string())

    if args.contoh:
        sampel = d[(d["kueri"] == args.contoh) & ~d["relevan"]]
        print(f"\n10 contoh post TIDAK relevan dari kata kunci '{args.contoh}' (dari {len(sampel)}):")
        for _, r in sampel.sample(min(10, len(sampel)), random_state=1).iterrows():
            print(f"- [{r['tgl']}] {r['text'][:200].replace(chr(10), ' ')}")


if __name__ == "__main__":
    main()
