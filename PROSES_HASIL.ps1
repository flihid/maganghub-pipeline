$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Environment .venv belum ada; lihat README_MANDIRI.md.' }
$taskExport = Get-ChildItem -LiteralPath (Join-Path $env:USERPROFILE 'Downloads') -Filter 'maganghub-x-*.json' -File |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $taskExport) { throw 'Ekspor maganghub-x-*.json belum ditemukan di Downloads.' }
& $taskPython import_browser_export.py $taskExport.FullName
if ($LASTEXITCODE -ne 0) { throw 'Impor gagal; pembersihan tidak dijalankan.' }
& $taskPython 03_preprocess.py
if ($LASTEXITCODE -ne 0) { throw 'Preprocessing gagal.' }
& $taskPython 04_audit_collection.py
if ($LASTEXITCODE -ne 0) { throw 'Audit gagal.' }
Write-Host 'Selesai. Kandidat dan laporan ada di data/processed. Tetap perlu tinjauan relevansi dan privasi.'
