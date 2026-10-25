@echo off
setlocal
cd /d "%~dp0"
set TWS_TELEMETRY=0
echo Pengambilan penuh: utamakan tanggal yang belum dicoba, bergiliran antar fase.
echo Klik launcher ini lagi untuk resume. Jangan jalankan dua kolektor bersamaan.
".venv\Scripts\python.exe" twscrape_pipeline.py collect --mode full --per-day 60 --max-raw 10000
set "COLLECTION_EXIT=%ERRORLEVEL%"
echo Memperbarui hasil lokal, termasuk bila pengambilan berhenti sebagian.
".venv\Scripts\python.exe" 03_preprocess.py
if errorlevel 1 goto failed
".venv\Scripts\python.exe" 04_audit_collection.py
if errorlevel 1 goto failed
if not "%COLLECTION_EXIT%"=="0" goto failed
echo Run selesai. Periksa checkpoint dan audit untuk cakupan aktual.
pause
exit /b 0
:failed
echo Run belum tuntas. Data tetap tersimpan; baca status terakhir di atas.
echo NoAccountError: tunggu sebelum mencoba lagi. Setup ulang hanya bila sesi tidak aktif/kedaluwarsa.
pause
exit /b 2
