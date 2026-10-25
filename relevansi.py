"""
Aturan relevansi dua jalur, dipakai bersama oleh cek_cakupan.py dan 03_preprocess.py
supaya keduanya selalu menghitung dengan aturan yang sama. Penjelasan aturan ada di
config.py (bagian KATA KUNCI).
"""

import pandas as pd

import config


def tandai_relevansi(df: pd.DataFrame) -> pd.Series:
    """
    Kembalikan Series berisi 'eksplisit', 'konteks', atau '' (tidak relevan) per baris.

    Butuh kolom: platform, tweet_id, kueri, text.
    Panggil SEBELUM deduplikasi: satu post bisa terjaring beberapa kata kunci, dan
    jalur konteks berlaku jika SALAH SATU kata kunci yang menjaringnya adalah jangkar.
    """
    teks = df["text"].fillna("")
    eksplisit = teks.str.contains(config.POLA_RELEVAN, case=False, regex=True)

    jangkar = {k.strip('"').lower() for k in config.KUERI_JANGKAR_KONTEKS}
    dari_jangkar = df["kueri"].fillna("").str.strip('"').str.lower().isin(jangkar)
    dari_jangkar = dari_jangkar.groupby([df["platform"], df["tweet_id"]]).transform("max")
    konteks = dari_jangkar & teks.str.contains(config.POLA_KONTEKS, case=False, regex=True)

    hasil = pd.Series("", index=df.index)
    hasil[konteks] = "konteks"
    hasil[eksplisit] = "eksplisit"   # eksplisit menang jika keduanya terpenuhi
    return hasil
