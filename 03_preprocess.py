"""
Langkah 3 - Preprocessing: data mentah -> dataset bersih siap analisis.

Tahapan (urutannya penting, dan jumlah baris di setiap tahap dicatat ke
data/processed/log_preprocessing.csv untuk laporan bagian C5):

  1. Gabung semua file data/raw/x_*.jsonl dan data/raw/threads_*.jsonl (kolom `platform`)
  2. Deduplikasi berdasarkan ID post per platform
  3. Buang post tanpa teks
  4. Saring relevansi dua jalur (relevansi.py): menyebut nama program, ATAU terjaring
     kata kunci jangkar dan memuat istilah khas program. Jalurnya dicatat di kolom
     `dasar_relevansi`; 30 sampel jalur konteks disimpan untuk pemeriksaan manual
  5. Tandai teks berulang dengan ID berbeda untuk review; pertahankan observasinya
  6. Saring heuristik promosi/tagar; teks pendek ditandai, bukan otomatis dibuang
  7. Buang akun otomatis (config.AKUN_DIBUANG, mis. meta.ai), lalu tandai jenis akun:
     resmi / media / publik (tidak dibuang)
  8. Anonimisasi: username -> hash SHA-256 bergaram; @mention di teks -> @user; URL dihapus
  9. Tetapkan fase dan tanggal berdasarkan waktu WIB
 10. Buat tiga versi teks:
       teks_model_minimal : baseline transformer, pertahankan ekspresi asli
       teks_model : pembersihan ringan  -> untuk IndoBERT (sentimen) dan embedding BERTopic
       teks_token : pembersihan berat   -> untuk analisis frekuensi/n-gram dan representasi
                                           kata pada BERTopic (CountVectorizer)

Kenapa dua versi? Model transformer (IndoBERT, sentence-transformers) membaca
konteks kalimat, jadi stopword dan tanda baca justru membantu. Stemming dan
penghapusan stopword hanya dipakai untuk analisis berbasis hitungan kata.

Cara pakai (PowerShell):
    python 03_preprocess.py
"""

import hashlib
import html
import re
import secrets
import sys
from pathlib import Path

import pandas as pd

import config
from relevansi import tandai_relevansi
from promosi import klasifikasi_promosi, VERSION as VERSI_PROMOSI

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DIR_RAW = Path(config.DIR_RAW)
DIR_OUT = Path(config.DIR_PROCESSED)

# ---------------------------------------------------------------------------
# Kamus normalisasi kata tidak baku.
# Daftar bawaan ini kecil; jika file Colloquial Indonesian Lexicon
# (Salsabila dkk., IALP 2018) ada di data/lexicon/, isinya digabungkan.
# Unduh dari: https://github.com/nasalsabila/kamus-alay
# ---------------------------------------------------------------------------
SLANG_BAWAAN = {
    "gak": "tidak", "ga": "tidak", "gk": "tidak", "nggak": "tidak", "ngga": "tidak",
    "enggak": "tidak", "tdk": "tidak", "tak": "tidak", "kagak": "tidak",
    "yg": "yang", "dgn": "dengan", "dg": "dengan", "krn": "karena", "karna": "karena",
    "utk": "untuk", "u": "untuk", "jg": "juga", "aja": "saja", "aj": "saja",
    "udh": "sudah", "udah": "sudah", "sdh": "sudah", "dah": "sudah",
    "blm": "belum", "blom": "belum", "bgt": "banget", "bngt": "banget",
    "kalo": "kalau", "klo": "kalau", "kl": "kalau", "gimana": "bagaimana", "gmn": "bagaimana",
    "emg": "memang", "emang": "memang", "org": "orang", "orng": "orang",
    "sm": "sama", "tp": "tapi", "tpi": "tapi", "dr": "dari", "dri": "dari",
    "trs": "terus", "trus": "terus", "lg": "lagi", "lgi": "lagi", "bs": "bisa", "bsa": "bisa",
    "skrg": "sekarang", "skrng": "sekarang", "knp": "kenapa", "napa": "kenapa",
    "gaji": "gaji", "fresgrad": "fresh graduate", "freshgrad": "fresh graduate",
    "fg": "fresh graduate", "kerjaan": "pekerjaan", "loker": "lowongan kerja",
    "kmrn": "kemarin", "bkn": "bukan", "jd": "jadi", "jdi": "jadi", "mrk": "mereka",
    "sy": "saya", "gw": "saya", "gue": "saya", "aku": "saya", "lu": "kamu", "lo": "kamu",
    "km": "kamu", "pd": "pada", "dlm": "dalam", "ttg": "tentang", "bener": "benar",
    "bnr": "benar", "kyk": "seperti", "kayak": "seperti", "pake": "pakai", "abis": "habis",
    "nganggur": "menganggur", "ngelamar": "melamar", "doang": "saja", "mulu": "melulu", "ampe": "sampai", "sampe": "sampai",
}

# Stopword dasar. Kata negasi (tidak, bukan, jangan, belum, tanpa) SENGAJA
# tidak dimasukkan karena menentukan makna pro/kontra.
STOPWORD = set("""
ada adalah adanya agar akan akhirnya aku amat anda antara apa apakah apalagi atau
bagaimana bagi bahkan bahwa banget banyak beberapa begini begitu belakang berapa
berbagai bersama biasa bila bisa boleh buat cuma dalam dan dari demikian dengan di
dia diri dong dulu hal hanya harus hingga ia ini itu jadi jika juga justru kalau
kami kamu kan karena kata ke kemudian kenapa kepada ketika kita kok lagi lah lain
lalu maka mana masih mau memang mereka meski nah namun nanti nya oleh pada para
pun saat saja sama sambil sampai sangat saya se sebagai sebelum sedang sehingga
sekali sekarang selalu seperti serta sih siapa sini situ suatu sudah supaya tadi
tapi telah tentang terhadap terus tetapi toh untuk ya yaitu yakni yang
""".split())

POLA_URL = re.compile(r"https?://\S+|www\.\S+|\b\S+\.(?:com|id|co|net|org|ly)/\S*")
POLA_MENTION = re.compile(r"@\w+")
POLA_HASHTAG = re.compile(r"#\w+")
POLA_RT = re.compile(r"^rt\s+", re.IGNORECASE)
POLA_ULANG_AKHIR = re.compile(r"([a-z])\1{2,}\b")  # "lagiii" -> "lagi" (di akhir kata)
POLA_ULANG = re.compile(r"([a-z])\1{2,}")           # "maaaaf" -> "maaf" (di tengah kata)
POLA_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF‍️]+"
)


# ---------------------------------------------------------------------------
def muat_slang() -> dict:
    kamus = dict(SLANG_BAWAAN)
    f = Path(config.FILE_LEKSIKON)
    if f.exists():
        lex = pd.read_csv(f)
        kol_slang = "slang" if "slang" in lex.columns else lex.columns[0]
        kol_formal = "formal" if "formal" in lex.columns else lex.columns[1]
        tambahan = dict(zip(lex[kol_slang].astype(str).str.lower(), lex[kol_formal].astype(str).str.lower()))
        tambahan.update(kamus)  # entri bawaan menang jika bentrok
        kamus = tambahan
        print(f"Leksikon dimuat: {len(kamus)} entri")
    else:
        print(f"Leksikon {f} tidak ditemukan, memakai {len(kamus)} entri bawaan")
    return kamus


def muat_salt() -> str:
    f = Path(config.FILE_SALT)
    if not f.exists():
        f.write_text(secrets.token_hex(16), encoding="utf-8")
    return f.read_text(encoding="utf-8").strip()


def hash_user(username: str, salt: str) -> str:
    return hashlib.sha256((salt + username.lower()).encode("utf-8")).hexdigest()[:16]


def normalisasi_kata(teks: str, kamus: dict) -> str:
    return re.sub(r"\b\w+\b", lambda m: kamus.get(m.group().lower(), m.group()), teks)


def bersih_ringan(teks: str, kamus: dict) -> str:
    t = html.unescape(teks)
    t = POLA_RT.sub("", t)
    t = POLA_URL.sub(" ", t)
    t = POLA_MENTION.sub("@user", t)
    t = t.replace("\n", " ").lower()
    t = POLA_ULANG_AKHIR.sub(r"\1", t)
    t = POLA_ULANG.sub(r"\1\1", t)
    t = normalisasi_kata(t, kamus)
    return re.sub(r"\s+", " ", t).strip()


def bersih_minimal(teks: str) -> str:
    """Transformer baseline: preserve negation, emoji, case and expressive spelling."""
    t = html.unescape(teks)
    t = POLA_URL.sub(" [URL] ", t)
    t = POLA_MENTION.sub("[USER]", t)
    return re.sub(r"\s+", " ", t).strip()


def bersih_berat(teks_model: str) -> str:
    t = POLA_EMOJI.sub(" ", teks_model)
    t = t.replace("@user", " ")
    t = POLA_HASHTAG.sub(lambda m: m.group()[1:], t)   # "#maganghub" -> "maganghub"
    t = re.sub(r"[^a-z\s]", " ", t)                     # buang angka & tanda baca
    domain = set(config.STOPWORD_DOMAIN)
    token = [w for w in t.split() if len(w) > 1 and w not in STOPWORD and w not in domain]
    return " ".join(token)


def kunci_duplikat(teks: str) -> str:
    t = POLA_URL.sub("", teks.lower())
    t = POLA_MENTION.sub("", t)
    return re.sub(r"[^a-z0-9]", "", t)


def tentukan_fase(ts_wib) -> str:
    tgl = ts_wib.date().isoformat()
    for nama, (since, until) in config.JENDELA_WAKTU.items():
        if since <= tgl < until:
            return nama
    return "di_luar_jendela"


# ---------------------------------------------------------------------------
def main() -> None:
    DIR_OUT.mkdir(parents=True, exist_ok=True)
    log = []

    def catat(tahap, df_sebelum, df_sesudah, ket=""):
        log.append({"tahap": tahap, "sebelum": len(df_sebelum), "sesudah": len(df_sesudah),
                    "dibuang": len(df_sebelum) - len(df_sesudah), "keterangan": ket})

    # 1. gabung (X dan Threads)
    files = sorted(DIR_RAW.glob("x_*.jsonl")) + sorted(DIR_RAW.glob("threads_*.jsonl"))
    if not files:
        sys.exit("Tidak ada file data/raw/x_*.jsonl atau threads_*.jsonl. Jalankan skrip scraping dulu.")
    bagian = []
    for f in files:
        d = pd.read_json(f, lines=True, dtype={"tweet_id": str})
        d["platform"] = "threads" if f.name.startswith("threads_") else "x"
        bagian.append(d)
    df = pd.concat(bagian, ignore_index=True)
    per_platform = df["platform"].value_counts().to_dict()
    log.append({"tahap": "1_gabung_raw", "sebelum": len(df), "sesudah": len(df), "dibuang": 0,
                "keterangan": f"{len(files)} file; " + ", ".join(f"{k}={v}" for k, v in per_platform.items())})

    # Relevansi dihitung SEBELUM dedup: jalur konteks berlaku jika salah satu
    # kata kunci yang menjaring post itu adalah kata kunci jangkar.
    df["dasar_relevansi"] = tandai_relevansi(df)

    # 2. dedup ID post (post yang sama bisa terjaring oleh beberapa kata kunci)
    a = df; df = df.drop_duplicates(["platform", "tweet_id"], keep="first"); catat("2_dedup_id_post", a, df)

    # 3. teks kosong
    a = df; df = df[df["text"].fillna("").str.strip() != ""]; catat("3_teks_kosong", a, df)

    # 4. relevansi (dua jalur, lihat config.py)
    a = df; df = df[df["dasar_relevansi"] != ""]
    jalur = df["dasar_relevansi"].value_counts().to_dict()
    catat("4_tidak_relevan", a, df,
          f"lolos eksplisit={jalur.get('eksplisit', 0)}, lolos konteks={jalur.get('konteks', 0)}")

    # 5. Identical text is not necessarily a duplicate observation (Module 5 p22).
    df = df.assign(_kunci=df["text"].map(kunci_duplikat),
                   _ts=pd.to_datetime(df["created_at"], utc=True, format="ISO8601")).sort_values("_ts")
    df = df.assign(teks_berulang=df.duplicated(["platform", "_kunci"], keep=False))
    df = df.drop(columns=["_kunci", "_ts"])
    catat("5_tandai_teks_berulang", df, df,
          f"{int(df['teks_berulang'].sum())} baris bertanda; ID berbeda dipertahankan untuk review")

    # 6. spam / bot
    hasil_promosi = pd.DataFrame(
        [klasifikasi_promosi(t, config.MAKS_HASHTAG) for t in df['text']], index=df.index)
    df = df.assign(promosi_status=hasil_promosi['keputusan'],
                   promosi_alasan=hasil_promosi['alasan'], promosi_sinyal=hasil_promosi['sinyal'],
                   versi_promosi=VERSI_PROMOSI)
    audit = df[df['promosi_status'] != 'keep'][['tweet_id', 'platform', 'text', 'promosi_status',
                                               'promosi_alasan', 'promosi_sinyal', 'versi_promosi']].copy()
    audit['text'] = audit['text'].map(bersih_minimal)
    audit.rename(columns={'tweet_id':'post_id', 'text':'teks_review'}).to_csv(
        DIR_OUT / 'audit_penyaringan_promosi.csv', index=False, encoding='utf-8-sig')
    a = df; df = df[df['promosi_status'] != 'exclude'].copy()
    catat('6_promosi', a, df, VERSI_PROMOSI + '; exclude=penawaran; review tetap dipertahankan')

    # 7. akun otomatis dibuang, lalu jenis akun ditandai
    a = df; df = df[~df["username"].str.lower().isin(config.AKUN_DIBUANG)]
    catat("7_akun_otomatis", a, df, "akun di config.AKUN_DIBUANG: " + ", ".join(config.AKUN_DIBUANG))
    u = df["username"].str.lower()
    df = df.assign(jenis_akun="publik")
    df.loc[u.isin(config.AKUN_MEDIA), "jenis_akun"] = "media"
    df.loc[u.isin(config.AKUN_RESMI), "jenis_akun"] = "resmi"

    # 8. anonimisasi + 10. dua versi teks
    salt = muat_salt()
    kamus = muat_slang()
    df = df.assign(
        user_hash=df["username"].map(lambda x: hash_user(x, salt)),
        teks_model_minimal=df["text"].map(bersih_minimal),
        teks_model=df["text"].map(lambda x: bersih_ringan(x, kamus)),
    )
    df = df.assign(teks_token=df["teks_model"].map(bersih_berat))

    # Short sentiment can remain informative; this is a review flag, not removal.
    df = df.assign(teks_pendek=df["teks_token"].str.split().str.len() < config.MIN_KATA)
    catat("6b_tandai_teks_pendek", df, df,
          f"{int(df['teks_pendek'].sum())} baris < {config.MIN_KATA} token; dipertahankan")

    # 9. waktu WIB, tanggal, fase
    ts = pd.to_datetime(df["created_at"], utc=True, format="ISO8601").dt.tz_convert("Asia/Jakarta")
    df = df.assign(waktu_wib=ts.dt.strftime("%Y-%m-%d %H:%M"), tanggal=ts.dt.strftime("%Y-%m-%d"),
                   fase=ts.map(tentukan_fase))
    a = df; df = df[df["fase"] != "di_luar_jendela"]; catat("9_di_luar_jendela", a, df)

    # Kolom final. username, url, dan teks asli TIDAK ikut disimpan (minimalisasi data):
    # url memuat username, sehingga identitas tetap bisa dilacak jika url disimpan.
    df = df.rename(columns={"tweet_id": "post_id"})
    kolom = ["post_id", "platform", "user_hash", "jenis_akun", "waktu_wib", "tanggal", "fase",
             "dasar_relevansi", "n_reply", "n_repost", "n_like", "teks_model_minimal", "teks_model", "teks_token",
             "teks_berulang", "teks_pendek", "promosi_status", "promosi_alasan", "promosi_sinyal", "versi_promosi"]
    # Preserve collection provenance and known truncation for manual review.
    kolom += [c for c in ("scraped_at", "text_truncated", "collector", "language_filter", "post_lang") if c in df.columns]
    df = df[kolom].sort_values("waktu_wib").reset_index(drop=True)

    # Sampel acak post yang lolos lewat jalur konteks, untuk diperiksa manual oleh tim.
    # Isi kolom relevan_manual dengan 1 (relevan) atau 0 (tidak), lalu hitung presisinya
    # untuk laporan C5.
    konteks = df[df["dasar_relevansi"] == "konteks"]
    if len(konteks):
        (konteks.sample(min(30, len(konteks)), random_state=42)[["post_id", "platform", "teks_model"]]
         .assign(relevan_manual="")
         .to_csv(DIR_OUT / "sampel_cek_relevansi_konteks.csv", index=False, encoding="utf-8-sig"))

    # Preserve ambiguous observations separately so review does not erase criticism.
    df.to_csv(DIR_OUT / 'maganghub_kandidat.csv', index=False, encoding='utf-8-sig')
    df[df['promosi_status'] == 'review'].to_csv(
        DIR_OUT / 'review_promosi.csv', index=False, encoding='utf-8-sig')
    a = df; df = df[df['promosi_status'] == 'keep'].copy()
    catat('11_tahan_untuk_review_promosi', a, df, 'tetap tersimpan di maganghub_kandidat.csv dan review_promosi.csv')
    ringkasan = df.groupby(["platform", "fase", "jenis_akun"]).size().unstack(fill_value=0)
    df.to_csv(DIR_OUT / "maganghub_bersih.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(log).to_csv(DIR_OUT / "log_preprocessing.csv", index=False, encoding="utf-8-sig")
    ringkasan.to_csv(DIR_OUT / "ringkasan_per_fase.csv", encoding="utf-8-sig")
    df.groupby(["tanggal", "platform"]).size().unstack(fill_value=0).to_csv(
        DIR_OUT / "volume_harian.csv", encoding="utf-8-sig")

    print()
    print(pd.DataFrame(log).to_string(index=False))
    print()
    print(ringkasan.to_string())
    print(f"\nKandidat hasil penyaringan otomatis (perlu review): {len(df)} post -> {DIR_OUT / 'maganghub_bersih.csv'}")


if __name__ == "__main__":
    main()
