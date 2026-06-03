# CareOS M-Pesa Demo Script
# Works on any machine regardless of venv name

# Auto-detect project path
$projectPath = if (Test-Path "C:\Users\Nico.Olusamu\Desktop\CareOs") {
    "C:\Users\Nico.Olusamu\Desktop\CareOs"
} elseif (Test-Path "C:\Users\user\Desktop\CareOs") {
    "C:\Users\user\Desktop\CareOs"
} else {
    Split-Path -Parent $MyInvocation.MyCommand.Path
}
Set-Location -LiteralPath $projectPath

# Auto-detect python executable directly by choosing a venv with Django installed
$pythonCandidates = @('.venv', 'venv', 'venv312', '.venv-1')
$pythonExe = $null
foreach ($candidate in $pythonCandidates) {
    $path = Join-Path $projectPath "$candidate\Scripts\python.exe"
    if (Test-Path $path) {
        try {
            $hasDjango = & "$path" -c "import importlib.util; print(importlib.util.find_spec('django') is not None)" 2>$null
            if ($hasDjango -match 'True') {
                $pythonExe = $path
                break
            }
        } catch {
            # ignore missing modules or execution failures
        }
    }
}
if (-not $pythonExe) {
    Write-Host "No Django-enabled venv found!" -ForegroundColor Red
    exit 1
}

Write-Host "Using Python: $pythonExe" -ForegroundColor Cyan

# Start ngrok in background
$ngrokPath = if (Test-Path "C:\ngrok\ngrok.exe")                        { "C:\ngrok\ngrok.exe" }
             elseif (Test-Path "$env:USERPROFILE\ngrok\ngrok.exe")       { "$env:USERPROFILE\ngrok\ngrok.exe" }
             else { "ngrok" }

Write-Host "Waiting for ngrok..." -ForegroundColor Yellow
Start-Process -FilePath $ngrokPath -ArgumentList "http 8000" -WindowStyle Minimized
Start-Sleep -Seconds 4

# Get ngrok URL
try {
    $tunnels  = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels"
    $ngrokUrl = ($tunnels.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1).public_url
    if (-not $ngrokUrl) { $ngrokUrl = $tunnels.tunnels[0].public_url }
} catch {
    Write-Host "Could not get ngrok URL - check ngrok is running!" -ForegroundColor Red
    exit 1
}

# Update .env
(Get-Content .env) -replace 'MPESA_CALLBACK_URL=.*', "MPESA_CALLBACK_URL=$ngrokUrl/billing/mpesa/callback/" | Set-Content .env
Write-Host "ngrok started: $ngrokUrl" -ForegroundColor Green
Write-Host ".env updated automatically" -ForegroundColor Green
Write-Host "Current MPESA_CALLBACK_URL:" -NoNewline
Get-Content .env | Select-String 'MPESA_CALLBACK_URL' | ForEach-Object { Write-Host " $_" }

# Open browser
Start-Process "http://127.0.0.1:8000"
Write-Host "Opening CareOS in browser..." -ForegroundColor Cyan

# Start Django using the python executable directly — no activate needed
Write-Host "Starting Django server..." -ForegroundColor Cyan
& $pythonExe manage.py runserver