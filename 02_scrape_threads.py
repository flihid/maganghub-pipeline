"""
Langkah 2 (Threads) - Scraping hasil pencarian Threads dengan Playwright.

Kenapa tidak memakai selector HTML seperti scraper X?
Threads memakai nama class yang diacak (misalnya "x1lliihq x193iq5w"), sehingga
selector berbasis class mudah rusak. Sebagai gantinya, skrip ini membaca data
terstruktur (JSON) yang memang dikirim Threads ke browser:
  1. JSON yang tertanam di halaman awal: <script type="application/json" data-sjs>
  2. Respons JSON yang dimuat browser setiap kali halaman di-scroll (permintaan GraphQL)
Dari JSON itu dicari objek post: objek yang punya `code`, `taken_at`,
`caption.text`, dan `user.username`.

Alur per kata kunci:
  1. Buka URL pencarian tab Terbaru (config.URL_PENCARIAN_THREADS).
  2. Ambil post dari JSON halaman awal, lalu scroll berulang sambil membaca
     respons JSON baru.
  3. Berhenti jika: batas MAKS_POST_THREADS_PER_KUERI tercapai, N scroll tanpa post baru,
     N scroll berturut-turut hanya berisi post sebelum awal jendela penelitian,
     atau Threads membalas dengan status 429 (terlalu banyak permintaan).
  4. Simpan ke data/raw/threads_<kata-kunci>.jsonl.

Pencarian Threads tidak punya filter tanggal; post di luar jendela penelitian
dibuang di 03_preprocess.py.

Cara pakai (PowerShell):
    python 02_scrape_threads.py --uji      # uji coba: 1 kata kunci, maks 20 post
    python 02_scrape_threads.py            # semua kata kunci
"""

import argparse
import csv
import json
import random
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import config

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DIR_RAW = Path(config.DIR_RAW)
FILE_PROGRES = DIR_RAW / "progres_threads.json"
FILE_LOG = DIR_RAW / "log_scraping_threads.csv"

AWAL_PENELITIAN = min(s for s, _ in config.JENDELA_WAKTU.values())  # "2026-07-01"


# ---------------------------------------------------------------------------
# Fungsi murni - mudah diuji
# ---------------------------------------------------------------------------
def tampak_post(d) -> bool:
    return (
        isinstance(d, dict)
        and "code" in d
        and "taken_at" in d
        and isinstance(d.get("caption"), dict)
        and isinstance(d.get("user"), dict)
        and "username" in d["user"]
    )


def cari_post(obj, hasil: list) -> None:
    """Telusuri JSON bersarang dan kumpulkan semua objek yang berbentuk post."""
    if isinstance(obj, dict):
        if tampak_post(obj):
            hasil.append(obj)
        for v in obj.values():
            cari_post(v, hasil)
    elif isinstance(obj, list):
        for v in obj:
            cari_post(v, hasil)


def parse_json_longgar(teks: str) -> list:
    """Respons Threads bisa diawali 'for (;;);' atau berisi beberapa JSON per baris."""
    teks = teks.strip()
    if teks.startswith("for (;;);"):
        teks = teks[len("for (;;);"):]
    try:
        return [json.loads(teks)]
    except json.JSONDecodeError:
        pass
    hasil = []
    for baris in teks.splitlines():
        baris = baris.strip()
        if baris.startswith("{") or baris.startswith("["):
            try:
                hasil.append(json.loads(baris))
            except json.JSONDecodeError:
                continue
    return hasil


def normalisasi(d: dict, meta: dict):
    teks = (d.get("caption") or {}).get("text")
    if not teks:
        return None
    username = d["user"]["username"]
    pk = str(d.get("pk") or d.get("id") or d["code"]).split("_")[0]
    try:
        dibuat = datetime.fromtimestamp(int(d["taken_at"]), tz=timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None
    info = d.get("text_post_app_info") or {}
    return {
        "tweet_id": f"th_{pk}",
        "platform": "threads",
        "url": f"https://www.threads.com/@{username}/post/{d['code']}",
        "username": username,
        "created_at": dibuat,
        "text": teks,
        "n_reply": info.get("direct_reply_count"),
        "n_repost": info.get("repost_count"),
        "n_like": d.get("like_count"),
        **meta,
    }


def slug(kata: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", kata.lower()).strip("-")


# ---------------------------------------------------------------------------
def muat_id_tersimpan() -> set:
    ids = set()
    for f in DIR_RAW.glob("threads_*.jsonl"):
        with open(f, encoding="utf-8") as fh:
            for baris in fh:
                if baris.strip():
                    ids.add(json.loads(baris)["tweet_id"])
    return ids


def muat_progres() -> set:
    if FILE_PROGRES.exists():
        return set(json.loads(FILE_PROGRES.read_text(encoding="utf-8")))
    return set()


def tulis_log(baris: dict) -> None:
    """Tulis ulang seluruh log agar baris lama dan baru tetap sejajar walau kolomnya bertambah."""
    rows = []
    if FILE_LOG.exists():
        with open(FILE_LOG, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    rows.append(baris)
    kolom = list(dict.fromkeys(k for r in rows for k in r))
    with open(FILE_LOG, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=kolom)
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------------------
def scrape_satu(page, kata, id_global, maks_post):
    from playwright.sync_api import TimeoutError as PWTimeout

    meta = {"fase": None, "kueri": kata, "since": None, "until": None,
            "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}

    antrean = []          # respons jaringan yang belum dibaca
    status_429 = [False]

    def saat_respons(resp):
        if resp.status == 429:
            status_429[0] = True
        if "graphql" in resp.url or "/api/" in resp.url:
            antrean.append(resp)

    page.on("response", saat_respons)
    try:
        url = config.URL_PENCARIAN_THREADS.format(q=urllib.parse.quote(kata))
        page.goto(url, wait_until="domcontentloaded")
        if "/login" in page.url:
            return [], "sesi_kedaluwarsa", None
        try:
            page.wait_for_load_state("networkidle", timeout=config.TIMEOUT_MUAT_MS)
        except PWTimeout:
            pass

        terkumpul = {}   # post BARU yang akan disimpan
        terlihat = set() # semua post yang muncul selama scroll ini, termasuk yang sudah tersimpan

        def serap(daftar_post):
            """Kembalikan jumlah post yang belum pernah TERLIHAT di sesi scroll ini.
            Penghitung 'tanpa_baru' memakai angka ini, bukan jumlah post yang disimpan,
            supaya saat dijalankan ulang skrip tetap scroll melewati post lama yang
            sudah tersimpan dan tidak berhenti terlalu cepat."""
            baru_terlihat, tanggal = 0, []
            for d in daftar_post:
                rec = normalisasi(d, meta)
                if not rec:
                    continue
                tanggal.append(rec["created_at"][:10])
                if rec["tweet_id"] not in terlihat:
                    terlihat.add(rec["tweet_id"])
                    baru_terlihat += 1
                if rec["tweet_id"] not in terkumpul and rec["tweet_id"] not in id_global:
                    terkumpul[rec["tweet_id"]] = rec
            return baru_terlihat, tanggal

        # 1. JSON di halaman awal
        awal = []
        for isi in page.eval_on_selector_all(
            'script[type="application/json"][data-sjs]', "els => els.map(e => e.textContent)"
        ):
            for data in parse_json_longgar(isi):
                cari_post(data, awal)
        serap(awal)

        # 2. scroll + baca respons jaringan
        tanpa_baru, terlalu_lama = 0, 0
        tanggal_terlihat = []
        status = "selesai"
        while len(terkumpul) < maks_post:
            page.mouse.wheel(0, random.randint(2200, 3200))
            time.sleep(random.uniform(*config.JEDA_SCROLL_DETIK))

            if status_429[0]:
                status = "dibatasi_429"
                break

            batch = []
            while antrean:
                resp = antrean.pop(0)
                try:
                    for data in parse_json_longgar(resp.text()):
                        cari_post(data, batch)
                except Exception:
                    continue
            baru, tanggal = serap(batch)
            tanggal_terlihat.extend(tanggal)

            tanpa_baru = 0 if baru else tanpa_baru + 1
            # Putaran tanpa data sama sekali tidak mengubah penghitung ini.
            if tanggal:
                terlalu_lama = terlalu_lama + 1 if max(tanggal) < AWAL_PENELITIAN else 0

            if tanpa_baru >= config.MAKS_SCROLL_TANPA_BARU:
                break
            if terlalu_lama >= config.MAKS_SCROLL_TERLALU_LAMA:
                status = "melewati_awal_jendela"
                break
        else:
            status = "batas_maks"

        tertua = min(tanggal_terlihat) if tanggal_terlihat else None
        return list(terkumpul.values())[:maks_post], status, tertua
    finally:
        page.remove_listener("response", saat_respons)


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="Scraper pencarian Threads untuk korpus MagangHub")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--uji", action="store_true", help="uji coba: 1 kata kunci, maks 20 post")
    ap.add_argument("--kata", action="append",
                    help="jalankan ulang kata kunci tertentu (boleh diulang), mengabaikan progres")
    ap.add_argument("--maks", type=int, help="ganti batas post baru per kata kunci")
    args = ap.parse_args()

    if not Path(config.FILE_SESI_THREADS).exists():
        sys.exit(f"{config.FILE_SESI_THREADS} belum ada. Jalankan dulu: python 01_simpan_sesi_threads.py")

    DIR_RAW.mkdir(parents=True, exist_ok=True)
    daftar = config.KATA_KUNCI_THREADS
    maks_post = args.maks or config.MAKS_POST_THREADS_PER_KUERI
    if args.uji:
        daftar, maks_post = daftar[:1], 20

    id_global = muat_id_tersimpan()
    selesai = set() if args.uji else muat_progres()
    if args.kata:
        daftar = args.kata
        selesai -= set(args.kata)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(storage_state=config.FILE_SESI_THREADS, locale="id-ID")
        page = context.new_page()

        for i, kata in enumerate(daftar, 1):
            if kata in selesai:
                continue
            print(f"[{i}/{len(daftar)}] {kata} ... ", end="", flush=True)
            t0 = time.time()
            try:
                records, status, tertua = scrape_satu(page, kata, id_global, maks_post)
            except Exception as e:
                records, status, tertua = [], f"exception:{type(e).__name__}", None

            if records:
                with open(DIR_RAW / f"threads_{slug(kata)}.jsonl", "a", encoding="utf-8") as fh:
                    for r in records:
                        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                id_global.update(r["tweet_id"] for r in records)

            tulis_log({
                "waktu": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "kueri": kata, "maks_post": maks_post, "jumlah_post_baru": len(records),
                "tertua_terlihat": tertua, "status": status,
                "durasi_detik": round(time.time() - t0, 1),
            })
            print(f"{len(records)} post baru ({status}) | post tertua yang terlihat: {tertua}")

            if status in ("sesi_kedaluwarsa", "dibatasi_429"):
                print("Threads menolak permintaan. Progres disimpan; berhenti di sini.")
                print("Jangan langsung diulang - tunggu minimal beberapa jam.")
                break

            if not args.uji:
                selesai.add(kata)
                FILE_PROGRES.write_text(json.dumps(sorted(selesai), indent=1), encoding="utf-8")
                time.sleep(random.uniform(*config.JEDA_ANTAR_KUERI_DETIK))

        browser.close()

    print(f"Selesai. Total post Threads tersimpan: {len(id_global)}. Log: {FILE_LOG}")


if __name__ == "__main__":
    main()
