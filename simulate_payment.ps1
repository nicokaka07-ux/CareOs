# Simulates Safaricom callback - run during demo after STK push

# Auto-detect project path
$projectPath = if (Test-Path "C:\Users\Nico.Olusamu\Desktop\CareOs") {
    "C:\Users\Nico.Olusamu\Desktop\CareOs"
} elseif (Test-Path "C:\Users\user\Desktop\CareOs") {
    "C:\Users\user\Desktop\CareOs"
} else {
    Split-Path -Parent $MyInvocation.MyCommand.Path
}

# Find python executable inside the venv under the project path
$pythonExe = if (Test-Path "$projectPath\.venv-1\Scripts\python.exe")    { "$projectPath\.venv-1\Scripts\python.exe" }
             elseif (Test-Path "$projectPath\venv312\Scripts\python.exe") { "$projectPath\venv312\Scripts\python.exe" }
             elseif (Test-Path "$projectPath\venv313\Scripts\python.exe") { "$projectPath\venv313\Scripts\python.exe" }
             elseif (Test-Path "$projectPath\.venv\Scripts\python.exe")   { "$projectPath\.venv\Scripts\python.exe" }
             else { Write-Host "No venv found!" -ForegroundColor Red; exit 1 }

# Get latest pending transaction
$checkoutId = & $pythonExe -c @"
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from billing.models import MpesaTransaction
t = MpesaTransaction.objects.filter(status='pending').order_by('-initiated_at').first()
print(t.checkout_request_id if t else 'NONE')
"@

if ($checkoutId -eq 'NONE') {
    Write-Host "No pending transaction found!" -ForegroundColor Red
    exit 1
}

Write-Host "Using checkout ID: $checkoutId" -ForegroundColor Yellow

# Get ngrok URL
try {
    $tunnels  = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels"
    $ngrokUrl = ($tunnels.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1).public_url
    if (-not $ngrokUrl) { $ngrokUrl = $tunnels.tunnels[0].public_url }
} catch {
    Write-Host "Could not get ngrok URL - is ngrok running?" -ForegroundColor Red
    exit 1
}

# Fire the callback
$body = @{
    Body = @{
        stkCallback = @{
            CheckoutRequestID = $checkoutId
            ResultCode        = 0
            ResultDesc        = "The service request is processed successfully."
            CallbackMetadata  = @{
                Item = @(
                    @{ Name = "Amount";             Value = 5 },
                    @{ Name = "MpesaReceiptNumber"; Value = "RBA7X3K9QP" },
                    @{ Name = "PhoneNumber";        Value = "254708374149" }
                )
            }
        }
    }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "$ngrokUrl/billing/mpesa/callback/" -Method POST -ContentType "application/json" -Body $body
Write-Host "Check the browser - should update in 5 seconds." -ForegroundColor Green