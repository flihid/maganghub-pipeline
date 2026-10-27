"""Estimasi presisi aturan otomatis dari sampel review berstrata.

    python alat_review/presisi_aturan.py <sampel_terisi.csv> [...]

Memakai kolom bobot/strata/N_strata/n_strata yang ditulis `preprocess_tk2.py run`, sehingga
estimasi berlaku untuk populasi status, bukan untuk sampel saja. Baris `ragu` tidak dibuang
diam-diam: dilaporkan sebagai dua batas (tanpa ragu, dan ragu dihitung salah).
Hanya membaca; tidak mengubah apa pun.
"""
import csv
import sys
from collections import defaultdict
from math import sqrt

# Status otomatis -> apa yang dianggap "benar" oleh peninjau manusia.
BENAR = {
    "keep": lambda r: r["keputusan_relevansi"] == "relevan" and r["keputusan_promosi"] == "bukan_iklan",
    "exclude": lambda r: r["keputusan_relevansi"] == "tidak_relevan" or r["keputusan_promosi"] == "iklan",
    "pending": lambda r: r["keputusan_relevansi"] == "relevan" and r["keputusan_promosi"] == "bukan_iklan",
}
TEGAS = {"keputusan_relevansi": {"relevan", "tidak_relevan"}, "keputusan_promosi": {"iklan", "bukan_iklan"}}


def tegas(r, fields=TEGAS):
    return all(r[k] in v for k, v in fields.items())


def estimasi(baris, benar, fields=TEGAS):
    """Estimator berstrata: p = sum (N_h/N) p_h, dengan koreksi populasi terbatas.

    Kembalikan (p, galat_baku, n_dipakai, n_ragu, N) dalam skala proporsi.
    """
    per_strata = defaultdict(list)
    for r in baris:
        per_strata[r["strata"]].append(r)
    N = sum(int(v[0]["N_strata"]) for v in per_strata.values())
    p = var = 0.0
    dipakai = ragu = 0
    for v in per_strata.values():
        N_h = int(v[0]["N_strata"])
        t = [r for r in v if tegas(r, fields)]
        ragu += len(v) - len(t)
        dipakai += len(t)
        if not t:  # strata tanpa baris tegas tidak bisa diestimasi; dilewati, dicatat lewat n_ragu
            continue
        n_h = len(t)
        p_h = sum(1 for r in t if benar(r)) / n_h
        W = N_h / N
        p += W * p_h
        if n_h > 1:
            var += W ** 2 * p_h * (1 - p_h) / (n_h - 1) * (1 - n_h / N_h)
    return p, sqrt(var), dipakai, ragu, N


def lapor(path):
    baris = [r for r in csv.DictReader(open(path, encoding="utf-8-sig", newline=""))
             if (r.get("reviewer") or "").strip()]
    if not baris or "strata" not in baris[0]:
        sys.exit(f"{path}: bukan sampel berstrata (kolom strata/bobot tidak ada)")
    print(f"\n# {path}  ({len(baris)} baris berpeninjau, "
          f"peninjau: {', '.join(sorted({r['reviewer'] for r in baris}))})")
    for status in ("keep", "pending", "exclude"):
        sub = [r for r in baris if r["status_final"] == status]
        if not sub:
            continue
        p, se, n, ragu, N = estimasi(sub, BENAR[status])
        # Batas bawah pesimistis: semua baris ragu dianggap keputusan aturan yang salah.
        bawah = p * n / (n + ragu) if n + ragu else 0.0
        print(f"  status otomatis '{status}' (N={N}): sesuai peninjau {p * 100:.1f}% "
              f"± {1.96 * se * 100:.1f} (95%), n_tegas={n}, ragu={ragu}, "
              f"batas bawah bila ragu dianggap salah {bawah * 100:.1f}%")
    for nama, f in (("relevansi", {"keputusan_relevansi": TEGAS["keputusan_relevansi"]}),
                    ("promosi", {"keputusan_promosi": TEGAS["keputusan_promosi"]})):
        sub = [r for r in baris if r["status_final"] == "keep"]
        kunci = "keputusan_relevansi" if nama == "relevansi" else "keputusan_promosi"
        nilai = "relevan" if nama == "relevansi" else "bukan_iklan"
        p, se, n, ragu, N = estimasi(sub, lambda r, k=kunci, v=nilai: r[k] == v, f)
        print(f"  aturan {nama} saja, pada populasi keep (N={N}): {p * 100:.1f}% "
              f"± {1.96 * se * 100:.1f} (95%), n_tegas={n}, ragu={ragu}")


def demo():
    """Dua strata seimbang, separuh benar di satu strata, semua benar di strata lain."""
    baris = ([dict(strata="a", N_strata="100", keputusan_relevansi="relevan",
                   keputusan_promosi="bukan_iklan")] * 5
             + [dict(strata="a", N_strata="100", keputusan_relevansi="tidak_relevan",
                     keputusan_promosi="bukan_iklan")] * 5
             + [dict(strata="b", N_strata="100", keputusan_relevansi="relevan",
                     keputusan_promosi="bukan_iklan")] * 10)
    p, se, n, ragu, N = estimasi(baris, BENAR["keep"])
    assert N == 200 and n == 20 and ragu == 0, (N, n, ragu)
    assert abs(p - 0.75) < 1e-9, p
    # Satu baris ragu tidak boleh ikut dihitung sebagai benar atau salah.
    p2, _, n2, ragu2, _ = estimasi(baris + [dict(strata="b", N_strata="100", keputusan_relevansi="ragu",
                                                 keputusan_promosi="ragu")], BENAR["keep"])
    assert ragu2 == 1 and n2 == 20 and abs(p2 - 0.75) < 1e-9, (ragu2, n2, p2)
    print("demo OK")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        demo()
    else:
        for p in sys.argv[1:]:
            lapor(p)
