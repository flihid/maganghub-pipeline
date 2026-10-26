"""
Aturan relevansi, dipakai bersama oleh cek_cakupan.py, 03_preprocess.py (lama), dan tk2prep.

Audit TK2: versi lama mencocokkan kolom `kueri` dengan kueri jangkar secara string persis.
Kolektor X aktif menyimpan kueri gabungan "(maganghub OR "magang hub" OR ...)", sehingga
(a) jalur konteks tidak pernah berlaku untuk X, dan (b) kita tidak bisa tahu istilah mana
yang membuat post terjaring. Pencarian X juga dapat mencocokkan nama/handle akun, kutipan,
atau tautan yang tidak tersimpan di teks. Karena itu hasil OR TIDAK dianggap relevan
otomatis: bukti harus ada di teks yang terkumpul.

Hasil nilai_relevansi():
  eksplisit          nama program ada di teks (di luar mention/URL) atau di hashtag -> keep otomatis
  eksplisit_generik  hanya "magang nasional"/"pemagangan nasional" (bisa merujuk program lain) -> keep, ditandai
  eksplisit_handle   nama program hanya muncul di @mention atau URL -> keep, ditandai
  konteks_jangkar    tanpa nama program; terjaring kueri jangkar TUNGGAL + istilah khas -> pending review
  konteks_or         tanpa nama program; kueri gabungan OR + istilah khas -> pending review
  konteks_kueri_generik  tanpa nama program; kueri tunggal non-jangkar (mis. Threads "magang nasional") -> pending
  tanpa_bukti        tidak ada bukti teks -> exclude otomatis (dapat dibatalkan reviewer)
"""

import re
import unicodedata

import pandas as pd

import config

VERSION = "relevansi_v2"

POLA_PROGRAM_KHAS = re.compile(r"magang\s*hub|magang\s+kemn?a?ker|magang\s+kemenaker|maganghub", re.I)
POLA_PROGRAM_GENERIK = re.compile(r"magang\s+nasional|pemagangan\s+nasional", re.I)
POLA_KONTEKS = re.compile(config.POLA_KONTEKS, re.I)
POLA_URL = re.compile(r"https?://\S+|www\.\S+|\b(?:[a-z0-9-]+\.)+(?:com|id|co|net|org)(?:/\S*)?", re.I)
POLA_MENTION = re.compile(r"(?<![\w@])@\w+")
_JANGKAR = {k.strip('"').lower() for k in config.KUERI_JANGKAR_KONTEKS}


def istilah_kueri(kueri: str) -> list:
    """'(a OR "b c")' -> ['a', 'b c']; kueri tunggal -> [kueri]."""
    if not kueri:
        return []
    isi = kueri.strip()
    if isi.startswith("(") and isi.endswith(")"):
        isi = isi[1:-1]
    return [t.strip().strip('"').lower() for t in re.split(r"\s+OR\s+", isi) if t.strip()]


def dari_jangkar_tunggal(kueri: str) -> bool:
    """True hanya jika kueri terdiri dari SATU istilah dan istilah itu jangkar."""
    terms = istilah_kueri(kueri)
    return len(terms) == 1 and terms[0] in _JANGKAR


def _bentuk_cocok(teks: str) -> str:
    # NFKC untuk huruf bergaya (𝐌𝐚𝐠𝐚𝐧𝐠𝐇𝐮𝐛), hanya untuk pencocokan.
    return unicodedata.normalize("NFKC", teks or "")


def nilai_relevansi(text: str, kueri_list) -> tuple:
    """Kembalikan (jalur, bukti). kueri_list: semua kueri yang menjaring post (setelah dedup)."""
    teks = _bentuk_cocok(text)
    tanpa_link = POLA_MENTION.sub(" ", POLA_URL.sub(" ", teks))
    tanpa_link_hashtag = tanpa_link.replace("#", " ")
    m = POLA_PROGRAM_KHAS.search(tanpa_link_hashtag)
    if m:
        return "eksplisit", m.group(0).lower()
    m = POLA_PROGRAM_GENERIK.search(tanpa_link_hashtag)
    if m:
        return "eksplisit_generik", m.group(0).lower()
    m = POLA_PROGRAM_KHAS.search(teks) or POLA_PROGRAM_GENERIK.search(teks)
    if m:
        return "eksplisit_handle", m.group(0).lower()
    k = POLA_KONTEKS.search(tanpa_link) or re.search(r"\bmagang\b|\bpemagang\w*", tanpa_link, re.I)
    if k:
        if any(dari_jangkar_tunggal(q) for q in kueri_list):
            return "konteks_jangkar", k.group(0).lower()
        if any(len(istilah_kueri(q)) > 1 for q in kueri_list):
            return "konteks_or", k.group(0).lower()
        return "konteks_kueri_generik", k.group(0).lower()
    return "tanpa_bukti", ""


def tandai_relevansi(df: pd.DataFrame) -> pd.Series:
    """
    Kompatibilitas 03_preprocess.py: 'eksplisit', 'konteks', atau '' per baris.

    Butuh kolom: platform, tweet_id, kueri, text. Panggil SEBELUM deduplikasi.
    Perbaikan v2: kueri gabungan OR tidak lagi dianggap/diabaikan secara keliru; jalur
    konteks hanya berlaku jika salah satu kueri tunggal yang menjaring adalah jangkar.
    """
    teks = df["text"].fillna("")
    eksplisit = teks.str.contains(config.POLA_RELEVAN, case=False, regex=True)
    dari_jangkar = df["kueri"].fillna("").map(dari_jangkar_tunggal)
    dari_jangkar = dari_jangkar.groupby([df["platform"], df["tweet_id"]]).transform("max")
    konteks = dari_jangkar & teks.str.contains(config.POLA_KONTEKS, case=False, regex=True)

    hasil = pd.Series("", index=df.index)
    hasil[konteks] = "konteks"
    hasil[eksplisit] = "eksplisit"   # eksplisit menang jika keduanya terpenuhi
    return hasil
