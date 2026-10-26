"""Grup teks berulang dan near-duplicate untuk FLAG dan pembagian evaluasi, bukan penghapusan.

Modul 05 hlm. 22: teks yang sama dari ID/penulis berbeda bukan duplikasi observasi.
Definisi di sini:
- teks_berulang_grup : kunci identik setelah casefold, spasi, dan placeholder dibuang.
                       Emoji, negasi, tanda baca, dan angka dipertahankan.
- near_dup_grup      : cosine TF-IDF karakter 3-5 gram >= ambang, dengan syarat himpunan
                       kata negasi dan emoji sama persis (agar 'sudah cair' ≠ 'belum cair',
                       'cair 😭' ≠ 'cair 😍'). Hanya teks >= MIN_CHARS karakter.
- split_group_id     : gabungan keduanya (union-find); dipakai agar konten sama/dekat tidak
                       melintasi train/test pada evaluasi supervised nanti.
"""
from __future__ import annotations

import hashlib

import numpy as np

from .teks import ciri_makna, kunci_teks_berulang

AMBANG_NEAR = 0.90
MIN_CHARS = 40


class _UnionFind:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, i):
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]
            i = self.p[i]
        return i

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def _gid(prefix, teks):
    return prefix + hashlib.sha1(teks.encode("utf-8")).hexdigest()[:12]


def pasangan_near(teks: list[str], ambang=AMBANG_NEAR):
    """Pasangan indeks (i, j) dengan cosine >= ambang. Deterministik."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    idx = [i for i, t in enumerate(teks) if len(t) >= MIN_CHARS]
    if len(idx) < 2:
        return []
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, lowercase=True)
    X = vec.fit_transform([teks[i] for i in idx])
    hasil = []
    blok = 2000
    for mulai in range(0, X.shape[0], blok):
        S = (X[mulai:mulai + blok] @ X.T).tocoo()
        for a, b, v in zip(S.row, S.col, S.data):
            ia, ib = mulai + int(a), int(b)
            if ia < ib and v >= ambang:
                hasil.append((idx[ia], idx[ib], float(v)))
    return hasil


def kelompokkan(records: list[dict]) -> None:
    """Tambahkan kolom grup ke records (in place). Dihitung per platform."""
    for plat in sorted({r["platform"] for r in records}):
        sub = [r for r in records if r["platform"] == plat]
        kunci = [kunci_teks_berulang(r["text_minimal"]) for r in sub]
        ukuran = {}
        for k in kunci:
            ukuran[k] = ukuran.get(k, 0) + 1
        for r, k in zip(sub, kunci):
            r["teks_berulang_grup"] = _gid("rep_", plat + "|" + k) if ukuran[k] > 1 else None
            r["teks_berulang_n"] = ukuran[k]
        uf = _UnionFind(len(sub))
        # Exact repeat -> satu grup.
        pertama = {}
        for i, k in enumerate(kunci):
            if k in pertama:
                uf.union(pertama[k], i)
            else:
                pertama[k] = i
        ciri = [ciri_makna(r["text_minimal"]) for r in sub]
        near = 0
        uf_near = _UnionFind(len(sub))
        for i, j, _ in pasangan_near([r["text_embedding"] for r in sub]):
            if kunci[i] == kunci[j] or ciri[i] != ciri[j]:
                continue
            uf.union(i, j)
            uf_near.union(i, j)
            near += 1
        akar_near = [uf_near.find(i) for i in range(len(sub))]
        n_near = {}
        for a in akar_near:
            n_near[a] = n_near.get(a, 0) + 1
        akar = [uf.find(i) for i in range(len(sub))]
        n_split = {}
        for a in akar:
            n_split[a] = n_split.get(a, 0) + 1
        for i, r in enumerate(sub):
            r["near_dup_grup"] = (_gid("near_", plat + "|" + sub[akar_near[i]]["post_id"])
                                  if n_near[akar_near[i]] > 1 else None)
            # ID grup stabil: berbasis post_id anggota pertama (urutan records deterministik).
            r["split_group_id"] = _gid("grp_", plat + "|" + sub[akar[i]]["post_id"])
            r["split_group_n"] = n_split[akar[i]]
