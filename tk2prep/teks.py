"""Versi teks sesuai tujuan analisis (Modul 06 hlm. 7-15, 18-25, 29-38).

text_minimal   : NFC + unescape HTML + whitespace aman + masking identitas. Negasi, emoji
                 (termasuk ZWJ U+200D dan variation selector U+FE0F), tanda baca, kapitalisasi,
                 hashtag, urutan kata, dan pemanjangan huruf dipertahankan.
text_sentiment : baseline = text_minimal; placeholder mention berderet di awal reply diringkas.
                 Tidak ada stemming, stopword removal, atau normalisasi slang. Tokenizer/casing
                 ditentukan oleh model transformer yang dipilih nanti.
text_sentiment_slang_v1 : VARIAN OPSIONAL dengan kamus slang kecil yang tidak ambigu; setiap
                 penggantian dicatat (slang_v1_ganti) sehingga dapat dibalik. Tidak otomatis lebih baik.
text_embedding : konteks utuh untuk sentence embedding BERTopic: placeholder URL dan deret
                 mention pembuka reply dihapus, tanda '#' dilepas (kata hashtag dipertahankan).
text_topic_repr: token huruf kecil untuk CountVectorizer/c-TF-IDF SETELAH embedding/clustering:
                 placeholder, URL, emoji, angka, dan tanda baca dibuang; stopword fungsi dibuang;
                 negasi, kata domain (gaji, kerja, magang, eksploitasi) dan nama program dipertahankan.
"""
from __future__ import annotations

import html
import re
import unicodedata

VERSI_TEKS = "teks_v1"

# Karakter tak terlihat yang dipakai sebagai pengisi/penghindar filter. ZWJ (U+200D) dan
# variation selector (U+FE0F/U+FE0E) SENGAJA tidak ada di sini karena bagian dari emoji.
TAK_TERLIHAT = dict.fromkeys(map(ord, "​⁠﻿­"), None)
SPASI_KHUSUS = dict.fromkeys(map(ord, "ㅤᅟᅠ       "), " ")

POLA_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
POLA_DOMAIN = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:com|id|co|net|org|ly|io|me|app)(?:/\S*)?\b", re.I)
POLA_MENTION = re.compile(r"(?<![\w@])@\w{1,30}")
POLA_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
POLA_TELEPON = re.compile(r"(?<!\d)(?:\+62|62|0)8\d{1,3}[\s.-]?\d{3,4}[\s.-]?\d{3,5}(?!\d)")
POLA_NIK = re.compile(r"(?<!\d)\d{16}(?!\d)")
POLA_NAMA_DIRI = re.compile(r"\b(?:nama\s+(?:saya|aku|gue|gw)|namaku)\s+(?:adalah\s+)?[A-Z][a-z]+", re.U)
POLA_HASHTAG = re.compile(r"#(\w+)")
POLA_PLACEHOLDER = re.compile(r"\[(?:URL|USER|EMAIL|PHONE|NIK)\]")
POLA_MENTION_AWAL = re.compile(r"^(?:\s*\[USER\])+\s*")

NEGASI = {"tidak", "tak", "bukan", "belum", "jangan", "tanpa", "gak", "ga", "nggak", "ngga", "enggak",
          "engga", "kagak", "gk", "tdk", "blm", "bkn", "jgn", "ndak", "nda", "gaada", "gada", "no", "not"}

# Stopword fungsi untuk REPRESENTASI topik saja (tidak dipakai di teks embedding/sentimen).
# Basis: daftar lama 03_preprocess.py + kata fungsi informal. Negasi dan kata domain
# sengaja tidak ada. Bukan daftar resmi; dicatat di vectorizer_config.json agar dapat ditinjau.
STOPWORD_TOPIK = sorted(set("""
ada adalah adanya agar akan akhirnya aku amat anda antara apa apakah apalagi atau bagaimana bagi
bahkan bahwa banyak beberapa begini begitu berapa bersama biar bila bisa boleh buat cuma dalam dan
dari demikian dengan di dia diri dong dulu hal hanya harus hingga ia ini itu jadi jika juga justru
kalau kami kamu kan karena kata ke kemudian kenapa kepada ketika kita kok lagi lah lain lalu maka
mana masih mau memang mereka meski nah namun nanti nya oleh pada para pun saat saja sama sambil
sampai sangat saya se sebagai sebelum sedang sehingga sekali sekarang selalu seperti serta sih siapa
sini situ suatu sudah supaya tadi tapi telah tentang terhadap terus tetapi toh untuk ya yaitu yakni
yang yg dgn dg utk krn karna jg aja aj udh udah sdh dah tp tpi dr dri trs trus lg lgi bs bsa kalo klo
gimana gmn emg emang gw gue gua lu lo loe elu km sy ak aq kak ka kakak min mimin nder sender guys gais
deh dih nih tuh loh lho kah yah yaa yaaa ye yeu wkwk wkwkwk wkwkwkwk awokwok haha hahaha hehe hihi anjir
anjay sih sihh nya2 aja2 oke ok okay the and of to is in for on with this that it be are you i
""".split()))

# Kamus slang kecil, sengaja menghindari kata ambigu (u, sm, kl, km, tp=tempat?, dll.).
SLANG_V1 = {
    "yg": "yang", "dgn": "dengan", "utk": "untuk", "krn": "karena", "tdk": "tidak", "gak": "tidak",
    "nggak": "tidak", "ngga": "tidak", "enggak": "tidak", "gk": "tidak", "blm": "belum", "udh": "sudah",
    "sdh": "sudah", "bgt": "banget", "bngt": "banget", "skrg": "sekarang", "knp": "kenapa",
    "gmn": "bagaimana", "dlm": "dalam", "ttg": "tentang", "jgn": "jangan", "bkn": "bukan",
}


def normalisasi_unicode(teks: str) -> str:
    """NFC (bukan NFKC: NFKC mengubah huruf gaya/fullwidth dan dapat merusak emoji tertentu)."""
    t = unicodedata.normalize("NFC", teks)
    t = t.translate(TAK_TERLIHAT).translate(SPASI_KHUSUS)
    # Buang karakter kontrol C0/C1 kecuali tab/newline; Cf lain (ZWJ, VS) dipertahankan.
    return "".join(ch for ch in t if ch in "\t\n" or unicodedata.category(ch) != "Cc")


def teks_minimal(teks: str) -> str:
    t = normalisasi_unicode(html.unescape(teks))
    t = POLA_EMAIL.sub("[EMAIL]", t)          # sebelum mention, agar user@mail tidak jadi [USER]
    t = POLA_URL.sub("[URL]", t)
    t = POLA_DOMAIN.sub("[URL]", t)
    t = POLA_MENTION.sub("[USER]", t)
    t = POLA_TELEPON.sub("[PHONE]", t)
    t = POLA_NIK.sub("[NIK]", t)
    return re.sub(r"\s+", " ", t).strip()


def _ringkas_mention_awal(t: str) -> str:
    return POLA_MENTION_AWAL.sub("[USER] ", t, count=1).strip()


def teks_sentimen(minimal: str) -> str:
    return _ringkas_mention_awal(minimal)


def teks_sentimen_slang(sentimen: str) -> tuple[str, list]:
    diganti = []

    def ganti(m):
        kata = m.group(0)
        baru = SLANG_V1.get(kata.lower())
        if baru is None:
            return kata
        diganti.append((m.start(), kata, baru))
        return baru

    return re.sub(r"\b[\w]+\b", ganti, sentimen), diganti


def pecah_hashtag(tag: str) -> str:
    """#MagangHub -> 'Magang Hub'; #maganghub tetap 'maganghub' (segmentasi tidak sempurna)."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", tag)


def teks_embedding(minimal: str) -> str:
    t = re.sub(r"^(?:\s*\[USER\])+\s*", "", minimal)        # alamat reply, bukan isi
    t = t.replace("[URL]", " ")
    t = POLA_HASHTAG.sub(lambda m: pecah_hashtag(m.group(1)), t)
    return re.sub(r"\s+", " ", t).strip()


def teks_topik(minimal: str) -> str:
    t = POLA_PLACEHOLDER.sub(" ", minimal)
    t = POLA_HASHTAG.sub(lambda m: " " + pecah_hashtag(m.group(1)) + " ", t)
    t = unicodedata.normalize("NFKC", t).casefold()          # gaya huruf -> huruf biasa untuk hitungan
    t = re.sub(r"(.)\1{2,}", r"\1\1", t)                    # "bangeeett" -> "bangeett" (konsisten)
    t = re.sub(r"[^a-z\s]", " ", t)                          # angka, emoji, tanda baca keluar
    stop = set(STOPWORD_TOPIK)
    return " ".join(w for w in t.split() if len(w) > 1 and (w in NEGASI or w not in stop))


def audit_pii(teks_asli: str) -> list[str]:
    """Tanda PII di isi teks (sebelum masking). Nama orang tidak dapat dideteksi andal: hanya pola
    'nama saya X' yang ditandai; selebihnya perlu pemeriksaan manusia saat mengutip."""
    t = html.unescape(teks_asli)
    hasil = []
    if POLA_EMAIL.search(t):
        hasil.append("email")
    if POLA_TELEPON.search(t):
        hasil.append("telepon")
    if POLA_NIK.search(t):
        hasil.append("angka_16_digit")
    if POLA_NAMA_DIRI.search(t):
        hasil.append("nama_diri")
    return hasil


def kunci_teks_berulang(minimal: str) -> str:
    """Kunci teks identik: casefold + spasi; placeholder dibuang. Emoji, negasi, tanda baca dan
    angka DIPERTAHANKAN supaya 'cair 😭' dan 'cair 😍' atau 'sudah cair' vs 'belum cair' berbeda."""
    t = POLA_PLACEHOLDER.sub(" ", minimal)
    t = unicodedata.normalize("NFKC", t).casefold()
    return re.sub(r"\s+", " ", t).strip()


def ciri_makna(minimal: str) -> tuple[frozenset, frozenset]:
    """(kata negasi, emoji) — dua near-duplicate hanya digabung jika keduanya sama."""
    kata = set(re.findall(r"\w+", minimal.casefold()))
    emoji = {ch for ch in minimal if unicodedata.category(ch) == "So"}
    return frozenset(kata & NEGASI), frozenset(emoji)


def jumlah_token(teks: str) -> int:
    return len(re.findall(r"\w+", teks))
