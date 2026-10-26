@echo off
setlocal
cd /d "%~dp0"
title Pengawas otomatis scraping MagangHub
echo Pengawas lokal: memantau proses dan resume setelah cooldown, maksimal 3 kali.
echo Sesi tidak aktif atau galat lain menghentikan pengawas untuk diperiksa.
echo Jangan jalankan launcher scraping lain selama pengawas aktif.
".venv\Scripts\python.exe" supervise_twscrape.py
echo Pengawas selesai atau membutuhkan pemeriksaan. Lihat status terakhir di atas.
pause
