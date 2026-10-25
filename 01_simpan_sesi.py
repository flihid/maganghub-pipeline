"""
Langkah 1 - Simpan sesi login X (dijalankan SEKALI).

Pencarian X hanya bisa diakses oleh akun yang login. Skrip ini membuka
browser Chromium, kamu login MANUAL seperti biasa, lalu cookie sesinya
disimpan ke file `sesi_x.json` agar skrip scraping tidak perlu login ulang.

Catatan keamanan:
- `sesi_x.json` berisi cookie login. Perlakukan seperti password.
  File ini sudah dimasukkan ke .gitignore - jangan pernah di-commit atau dibagikan.
- Disarankan memakai akun X cadangan, bukan akun pribadi utama.

Cara pakai (PowerShell):
    python 01_simpan_sesi.py
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
        page.goto("https://x.com/login")

        print("=" * 60)
        print("Login secara manual di jendela browser yang terbuka.")
        print("Tunggu sampai timeline Beranda/Home muncul,")
        print("lalu kembali ke terminal ini dan tekan ENTER.")
        print("=" * 60)
        input()

        if "login" in page.url or "flow" in page.url:
            print("Sepertinya belum berhasil login (URL masih di halaman login).")
            print("Ulangi skrip ini setelah login selesai.")
            browser.close()
            sys.exit(1)

        context.storage_state(path=config.FILE_SESI)
        browser.close()

    print(f"Sesi disimpan ke {Path(config.FILE_SESI).resolve()}")
    print("Sekarang jalankan: python 02_scrape_x.py")


if __name__ == "__main__":
    main()
