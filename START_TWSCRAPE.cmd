@echo off
setlocal
cd /d "%~dp0"
set TWS_TELEMETRY=0
if not exist ".venv\Scripts\python.exe" (
  echo Environment belum ada. Baca README_TWSCRAPE.md.
  pause
  exit /b 2
)
echo Pilot twscrape: maksimal 50 post baru per fase.
if not exist ".twscrape\accounts.db" (
  ".venv\Scripts\python.exe" twscrape_pipeline.py setup
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" twscrape_pipeline.py collect --mode pilot
if errorlevel 1 goto failed
".venv\Scripts\python.exe" 03_preprocess.py
if errorlevel 1 goto failed
".venv\Scripts\python.exe" 04_audit_collection.py
if errorlevel 1 goto failed
echo Pilot selesai dijalankan. Periksa distribusi fase dan review manual sebelum full.
pause
exit /b 0
:failed
echo Proses berhenti. Data yang sudah tersimpan tetap ada.
echo Untuk memperbarui sesi, jalankan perintah setup di README_TWSCRAPE.md.
pause
exit /b 2
