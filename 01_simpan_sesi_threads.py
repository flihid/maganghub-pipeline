"""
Langkah 1 (Threads) - Simpan sesi login Threads (dijalankan SEKALI).

Pencarian Threads hanya bisa diakses oleh akun yang login. Skrip ini membuka
Chromium, kamu login MANUAL dengan akun Instagram, lalu cookie sesinya
disimpan ke `sesi_threads.json`.

Jika Threads menolak login dari browser ini (misalnya muncul pesan pembatasan),
BERHENTI. Jangan diulang berkali-kali: akun Threads terhubung ke akun Instagram,
dan percobaan berulang berisiko membuat akun Instagram dibatasi.

Catatan keamanan:
- `sesi_threads.json` berisi cookie login. Perlakukan seperti password.
  File ini sudah dimasukkan ke .gitignore.

Cara pakai (PowerShell):
    python 01_simpan_sesi_threads.py
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import config


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(locale="id-ID")
        page = context.new_page()
        page.goto("https://www.threads.com/login")

        print("=" * 60)
        print("Login secara manual di jendela browser (pilih masuk dengan Instagram).")
        print("Tunggu sampai beranda Threads muncul,")
        print("lalu kembali ke terminal ini dan tekan ENTER.")
        print("=" * 60)
        input()

        # Login lewat Instagram sering terjadi di tab/jendela baru, jadi URL tab pertama
        # tidak bisa dijadikan patokan. Simpan cookie dari seluruh browser, lalu buktikan
        # dengan membuka halaman pencarian (hanya bisa dibuka jika sudah login).
        context.storage_state(path=config.FILE_SESI_THREADS)

        cek = context.new_page()
        cek.goto(config.URL_PENCARIAN_THREADS.format(q="maganghub"), wait_until="domcontentloaded")
        cek.wait_for_timeout(5000)
        url_cek = cek.url
        browser.close()

    if "/login" in url_cek:
        Path(config.FILE_SESI_THREADS).unlink(missing_ok=True)
        print("Halaman pencarian masih mengarahkan ke login, jadi sesi belum tersimpan.")
        print("Pastikan beranda Threads sudah tampil sebelum menekan ENTER.")
        print("Jika Threads menolak login, hentikan di sini dan jangan diulang terus.")
        sys.exit(1)

    print(f"Sesi disimpan ke {Path(config.FILE_SESI_THREADS).resolve()}")
    print(f"Halaman pencarian terbuka tanpa diminta login: {url_cek}")
    print("Sekarang jalankan: python 02_scrape_threads.py --uji")


if __name__ == "__main__":
    main()
