"""
Langkah 2 - Scraping hasil pencarian X dengan Playwright.

Alur per kombinasi (kata kunci x subjendela waktu):
  1. Buka URL pencarian X tab "Terbaru" dengan filter lang:id since: until:
  2. Tunggu post pertama muncul (halaman dirender JavaScript -> butuh Playwright,
     sama seperti timeline Mastodon di Tutorial 2).
  3. Ekstrak semua post yang sedang ada di DOM, lalu scroll ke bawah.
     X memakai "virtualized list": post lama DIHAPUS dari DOM saat kita scroll,
     karena itu ekstraksi dilakukan di SETIAP putaran scroll dan hasilnya
     dikumpulkan di dictionary berdasarkan tweet_id (sekaligus deduplikasi).
  4. Berhenti jika: batas MAKS_POST_PER_KUERI tercapai, atau
     MAKS_SCROLL_TANPA_BARU putaran berturut-turut tidak menemukan post baru,
     atau X menampilkan pesan error / batas akses.
  5. Simpan ke data/raw/x_<fase>.jsonl (satu baris JSON per post).

Skrip bisa dihentikan (Ctrl+C) dan dijalankan ulang kapan saja:
kombinasi yang sudah selesai dicatat di data/raw/progres.json dan dilewati,
dan post yang ID-nya sudah tersimpan tidak ditulis dua kali.

Cara pakai (PowerShell):
    python 02_scrape_x.py --uji               # uji coba: 1 kueri, 1 subjendela, maks 20 post
    python 02_scrape_x.py                     # semua fase
    python 02_scrape_x.py --fase fase2_seleksi
    python 02_scrape_x.py --headless          # tanpa menampilkan jendela browser
"""

import argparse
import csv
import json
import random
import re
import sys
import time
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import config

# Supaya karakter non-ASCII tidak membuat PowerShell error saat print.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DIR_RAW = Path(config.DIR_RAW)
FILE_PROGRES = DIR_RAW / "progres.json"
FILE_LOG = DIR_RAW / "log_scraping.csv"

# ---------------------------------------------------------------------------
# Elemen DOM yang diekstrak.
# SELECTOR INI BISA BERUBAH jika X memperbarui tampilannya. Jika hasil scraping
# kosong padahal post terlihat di browser, buka DevTools (F12) -> klik kanan
# sebuah post -> Inspect, lalu sesuaikan selector di bawah.
#   article[data-testid="tweet"]      -> satu post
#   div[data-testid="tweetText"]      -> isi teks post
#   time[datetime]                    -> stempel waktu (ISO 8601, UTC);
#                                        elemen <a> induknya berisi permalink /<user>/status/<id>
#   [data-testid="reply|retweet|like"] -> tombol metrik; aria-label berisi angkanya
# ---------------------------------------------------------------------------
JS_EKSTRAK = r"""
() => Array.from(document.querySelectorAll('article[data-testid="tweet"]')).map(a => {
  const t = a.querySelector('time[datetime]');
  const link = t ? t.closest('a') : null;
  const teks = a.querySelector('div[data-testid="tweetText"]');
  const metrik = (ids) => {
    for (const id of ids) {
      const el = a.querySelector(`[data-testid="${id}"]`);
      if (el) return el.getAttribute('aria-label');
    }
    return null;
  };
  return {
    href: link ? link.getAttribute('href') : null,
    created_at: t ? t.getAttribute('datetime') : null,
    text: teks ? teks.innerText : null,
    label_reply: metrik(['reply']),
    label_repost: metrik(['retweet', 'unretweet']),
    label_like: metrik(['like', 'unlike']),
  };
})
"""

POLA_ERROR = re.compile(
    r"something went wrong|terjadi kesalahan|ada yang salah|rate limit|"
    r"try reloading|coba muat ulang",
    re.IGNORECASE,
)
POLA_KOSONG = re.compile(r"no results for|tidak ada hasil", re.IGNORECASE)
POLA_HREF = re.compile(r"^/([^/]+)/status/(\d+)")


# ---------------------------------------------------------------------------
# Fungsi murni (tanpa browser) - mudah diuji
# ---------------------------------------------------------------------------
def subjendela(since: str, until: str, hari: int):
    """Pecah rentang [since, until) menjadi potongan maksimal `hari` hari."""
    awal = date.fromisoformat(since)
    akhir = date.fromisoformat(until)
    while awal < akhir:
        ujung = min(awal + timedelta(days=hari), akhir)
        yield awal.isoformat(), ujung.isoformat()
        awal = ujung


def buat_url(kata_kunci: str, since: str, until: str) -> str:
    q = f"{kata_kunci} lang:{config.BAHASA} since:{since} until:{until}"
    params = {"q": q, "src": "typed_query", "f": "live"}
    return "https://x.com/search?" + urllib.parse.urlencode(params)


def ambil_angka(label):
    """'12 Balasan. Balas' -> 12 ; '1.234 Likes. Like' -> 1234 ; 'Balas' -> 0."""
    if not label:
        return None
    cocok = re.search(r"\d[\d.,]*", label)
    if not cocok:
        return 0
    return int(re.sub(r"[.,]", "", cocok.group()))


def normalisasi(item: dict, meta: dict):
    """Ubah hasil mentah JS menjadi satu record. None jika data inti tidak lengkap."""
    href = item.get("href") or ""
    cocok = POLA_HREF.match(href)
    if not cocok or not item.get("text"):
        return None
    username, tweet_id = cocok.group(1), cocok.group(2)
    return {
        "tweet_id": tweet_id,
        "url": f"https://x.com/{username}/status/{tweet_id}",
        "username": username,
        "created_at": item.get("created_at"),
        "text": item["text"],
        "n_reply": ambil_angka(item.get("label_reply")),
        "n_repost": ambil_angka(item.get("label_repost")),
        "n_like": ambil_angka(item.get("label_like")),
        **meta,
    }


# ---------------------------------------------------------------------------
# Penyimpanan, progres, dan log
# ---------------------------------------------------------------------------
def muat_id_tersimpan() -> set:
    ids = set()
    for f in DIR_RAW.glob("x_*.jsonl"):
        with open(f, encoding="utf-8") as fh:
            for baris in fh:
                baris = baris.strip()
                if baris:
                    ids.add(json.loads(baris)["tweet_id"])
    return ids


def muat_progres() -> set:
    if FILE_PROGRES.exists():
        return set(json.loads(FILE_PROGRES.read_text(encoding="utf-8")))
    return set()


def simpan_progres(selesai: set) -> None:
    FILE_PROGRES.write_text(json.dumps(sorted(selesai), indent=1), encoding="utf-8")


def tulis_log(baris: dict) -> None:
    baru = not FILE_LOG.exists()
    with open(FILE_LOG, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(baris.keys()))
        if baru:
            w.writeheader()
        w.writerow(baris)


def tulis_record(fase: str, records: list) -> None:
    with open(DIR_RAW / f"x_{fase}.jsonl", "a", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Scraping satu kombinasi kueri x subjendela
# ---------------------------------------------------------------------------
def scrape_satu(page, kata_kunci, fase, since, until, id_global, maks_post):
    from playwright.sync_api import TimeoutError as PWTimeout

    meta = {
        "fase": fase, "kueri": kata_kunci, "since": since, "until": until,
        "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    page.goto(buat_url(kata_kunci, since, until), wait_until="domcontentloaded")

    if "/login" in page.url or "/i/flow" in page.url:
        return [], "sesi_kedaluwarsa"

    try:
        page.wait_for_selector('article[data-testid="tweet"]', timeout=config.TIMEOUT_MUAT_MS)
    except PWTimeout:
        isi = page.inner_text("body")
        if POLA_KOSONG.search(isi):
            return [], "tidak_ada_hasil"
        if POLA_ERROR.search(isi):
            return [], "error_x"
        return [], "timeout"

    terkumpul = {}
    tanpa_baru = 0
    status = "selesai"
    while len(terkumpul) < maks_post and tanpa_baru < config.MAKS_SCROLL_TANPA_BARU:
        baru = 0
        for item in page.evaluate(JS_EKSTRAK):
            rec = normalisasi(item, meta)
            if rec and rec["tweet_id"] not in terkumpul and rec["tweet_id"] not in id_global:
                terkumpul[rec["tweet_id"]] = rec
                baru += 1
        tanpa_baru = 0 if baru else tanpa_baru + 1

        if POLA_ERROR.search(page.inner_text("body")):
            status = "error_x_di_tengah"
            break

        page.mouse.wheel(0, random.randint(2200, 3200))
        time.sleep(random.uniform(*config.JEDA_SCROLL_DETIK))

    if len(terkumpul) >= maks_post:
        status = "batas_maks"
    return list(terkumpul.values())[:maks_post], status


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="Scraper pencarian X untuk korpus MagangHub")
    ap.add_argument("--fase", choices=list(config.JENDELA_WAKTU), help="hanya jalankan satu fase")
    ap.add_argument("--headless", action="store_true", help="jalankan tanpa jendela browser")
    ap.add_argument("--uji", action="store_true", help="uji coba: 1 kueri, 1 subjendela, 20 post")
    args = ap.parse_args()

    if not Path(config.FILE_SESI).exists():
        sys.exit(f"File sesi {config.FILE_SESI} belum ada. Jalankan dulu: python 01_simpan_sesi.py")

    DIR_RAW.mkdir(parents=True, exist_ok=True)

    fase_dipakai = {args.fase: config.JENDELA_WAKTU[args.fase]} if args.fase else config.JENDELA_WAKTU
    tugas = [
        (kk, fase, s, u)
        for fase, (since, until) in fase_dipakai.items()
        for s, u in subjendela(since, until, config.PANJANG_SUBJENDELA_HARI)
        for kk in config.KATA_KUNCI
    ]
    maks_post = config.MAKS_POST_PER_KUERI
    if args.uji:
        tugas, maks_post = tugas[:1], 20

    id_global = muat_id_tersimpan()
    selesai = set() if args.uji else muat_progres()
    print(f"{len(tugas)} kombinasi kueri x subjendela | {len(id_global)} post sudah tersimpan sebelumnya")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(storage_state=config.FILE_SESI, locale="id-ID")
        page = context.new_page()

        for i, (kk, fase, s, u) in enumerate(tugas, 1):
            kunci = f"{fase}|{kk}|{s}|{u}"
            if kunci in selesai:
                continue

            print(f"[{i}/{len(tugas)}] {fase} | {kk} | {s} s.d. {u} ... ", end="", flush=True)
            t0 = time.time()
            try:
                records, status = scrape_satu(page, kk, fase, s, u, id_global, maks_post)
            except Exception as e:  # jaringan putus, halaman crash, dll.
                records, status = [], f"exception:{type(e).__name__}"

            if records:
                tulis_record(fase, records)
                id_global.update(r["tweet_id"] for r in records)
            tulis_log({
                "waktu": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "fase": fase, "kueri": kk, "since": s, "until": u,
                "jumlah_post_baru": len(records), "status": status,
                "durasi_detik": round(time.time() - t0, 1),
            })
            print(f"{len(records)} post baru ({status})")

            if status == "sesi_kedaluwarsa":
                print("Sesi login habis. Jalankan ulang 01_simpan_sesi.py lalu lanjutkan skrip ini.")
                break
            if status.startswith("error_x"):
                print("X menolak permintaan (kemungkinan batas akses). Progres disimpan.")
                print("Tunggu 15-30 menit, lalu jalankan ulang skrip ini - akan lanjut dari sini.")
                break

            if not args.uji:
                selesai.add(kunci)
                simpan_progres(selesai)
            time.sleep(random.uniform(*config.JEDA_ANTAR_KUERI_DETIK))

        browser.close()

    print(f"Selesai. Total post tersimpan: {len(id_global)}. Log: {FILE_LOG}")


if __name__ == "__main__":
    main()
