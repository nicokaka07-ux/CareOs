# CareOS Setup Script — run once on any new machine
# Usage: Open PowerShell on Desktop, paste this line:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned; iwr -useb https://raw.githubusercontent.com/nicokaka07-ux/CareOs/main/setup.ps1 | iex

$username = $env:USERNAME
$desktop  = "C:\Users\$username\Desktop"
$project  = "$desktop\CareOs"

Write-Host "Setting up CareOS for $username..." -ForegroundColor Cyan

# Clone only if not already there
if (-not (Test-Path "$project\manage.py")) {
    Write-Host "Cloning project..." -ForegroundColor Yellow
    cd $desktop
    git clone https://github.com/nicokaka07-ux/CareOs.git
} else {
    Write-Host "Project already exists, pulling latest..." -ForegroundColor Yellow
    cd $project
    git pull
}

cd $project

# Check Python
$python = $null
foreach ($v in @("3.12", "3.11", "3.13")) {
    try {
        $test = & py -$v --version 2>&1
        if ($test -match "Python") { $python = $v; break }
    } catch {}
}

if (-not $python) {
    Write-Host "No suitable Python found! Install Python 3.12 from:" -ForegroundColor Red
    Write-Host "https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe" -ForegroundColor Yellow
    exit 1
}

Write-Host "Using Python $python" -ForegroundColor Green

# Create venv
if (-not (Test-Path "venv312\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    & py -$python -m venv venv312
}

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
& "venv312\Scripts\pip.exe" install -r requirements.txt

# Create .env if missing
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env" -ErrorAction SilentlyContinue
    Write-Host ".env created - please fill in your M-Pesa keys!" -ForegroundColor Red
    code .env
}

# Run migrations
Write-Host "Running migrations..." -ForegroundColor Yellow
& "venv312\Scripts\python.exe" manage.py migrate

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "Run the project with:" -ForegroundColor Cyan
Write-Host ". '$project\demo_mpesa.ps1'" -ForegroundColor White