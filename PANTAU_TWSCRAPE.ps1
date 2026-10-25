$Host.UI.RawUI.WindowTitle = 'Progres scraping MagangHub'
Set-Location -LiteralPath $PSScriptRoot
while ($true) {
    Clear-Host
    Write-Host 'PROGRES SCRAPING MAGANGHUB' -ForegroundColor Cyan
    Write-Host 'Jendela ini hanya memantau; tidak menjalankan scraper tambahan.'
    Write-Host 'Menutup jendela ini tidak menghentikan scraping.'
    Write-Host ''
    $taskCollectors = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -like '*twscrape_pipeline.py*collect*' })
    if ($taskCollectors.Count -gt 0) {
        Write-Host 'Proses scraper: AKTIF' -ForegroundColor Green
    } else {
        Write-Host 'Proses scraper: TIDAK AKTIF' -ForegroundColor Yellow
    }
    $taskStates = @(Get-ChildItem -LiteralPath 'data/raw' -Filter 'twscrape_state_*.json' |
        Sort-Object LastWriteTime -Descending)
    foreach ($taskFile in $taskStates) {
        try {
            $taskState = Get-Content -LiteralPath $taskFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($taskState.settings.mode -ne 'full') { continue }
            $taskJobs = @($taskState.jobs.PSObject.Properties | ForEach-Object { $_.Value })
            $taskLast = $taskJobs | Sort-Object finished_at -Descending | Select-Object -First 1
            Write-Host ('Total post unik: ' + $taskState.total_unique)
            Write-Host ('Tanggal diproses: ' + $taskJobs.Count + ' / 117')
            Write-Host ('Status checkpoint: ' + $taskState.status)
            Write-Host ''
            Write-Host 'Tambahan melalui twscrape per fase:'
            $taskState.sdk_counts_per_phase.PSObject.Properties | ForEach-Object {
                Write-Host ('  ' + $_.Name + ': ' + $_.Value)
            }
            Write-Host ''
            Write-Host ('Tanggal terakhir selesai: ' + $taskLast.since)
            Write-Host ('Tambahan terakhir: ' + $taskLast.added)
            Write-Host ('Status kueri terakhir: ' + $taskLast.status)
            Write-Host ('Waktu selesai kueri: ' + $taskLast.finished_at)
            if ($taskLast.error_type) { Write-Host ('Galat: ' + $taskLast.error_type) -ForegroundColor Yellow }
            break
        } catch {
            Write-Host 'Checkpoint sedang diperbarui; mencoba lagi.'
        }
    }
    Write-Host ''
    Write-Host 'Diperbarui setiap 5 detik. Angka berubah setelah satu kueri selesai.'
    Write-Host 'Ctrl+C untuk menutup pemantau.'
    Start-Sleep -Seconds 5
}
