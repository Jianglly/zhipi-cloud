# ZhiPi Cloud - One-Click Start All Services
# Run with: right-click -> "Run with PowerShell"
# Or: powershell -ExecutionPolicy Bypass -File start.ps1

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$SCRIPTS = Join-Path $ROOT "scripts"
$BIN = Join-Path $ROOT "bin"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ZhiPi Cloud - Start All Services" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Root : $ROOT"
Write-Host "Scripts: $SCRIPTS"
Write-Host ""

# ---------------------------------------------------------
# 1. Backend
# ---------------------------------------------------------
Write-Host "[1/3] Backend ..." -ForegroundColor Yellow
$BACKEND_DIR = Join-Path $ROOT "zhipi-cloud\zhipi-backend"
$PYTHON_EXE = "C:\Users\HP\.workbuddy\binaries\python\versions\3.13.12\python.exe"
$UVICORN_ARGS = @("-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000")

if (-not (Test-Path $PYTHON_EXE)) {
    Write-Host "  [ERROR] Python not found: $PYTHON_EXE" -ForegroundColor Red
    pause
    exit 1
}

Start-Process -FilePath $PYTHON_EXE `
    -ArgumentList $UVICORN_ARGS `
    -WorkingDirectory $BACKEND_DIR `
    -WindowStyle Normal

Start-Sleep -Milliseconds 500
Write-Host "       Backend window launched." -ForegroundColor Green

# ---------------------------------------------------------
# 2. Frontend
# ---------------------------------------------------------
Write-Host "[2/3] Frontend ..." -ForegroundColor Yellow
$FRONTEND_DIR = Join-Path $ROOT "zhipi-cloud\zhipi-frontend"

if (Test-Path $FRONTEND_DIR) {
    # Check if node_modules exists
    if (Test-Path (Join-Path $FRONTEND_DIR "node_modules")) {
        Start-Process -FilePath "npm.cmd" `
            -ArgumentList "run", "dev" `
            -WorkingDirectory $FRONTEND_DIR `
            -WindowStyle Normal
        Start-Sleep -Milliseconds 500
        Write-Host "       Frontend window launched." -ForegroundColor Green
    } else {
        Write-Host "       [SKIP] node_modules not found, run 'npm install' first." -ForegroundColor DarkYellow
    }
} else {
    Write-Host "       [SKIP] frontend folder not found." -ForegroundColor DarkYellow
}

# ---------------------------------------------------------
# 3. Cloudflare Tunnel
# ---------------------------------------------------------
Write-Host "[3/3] Tunnel ..." -ForegroundColor Yellow
$CLOUDFLARED_EXE = Join-Path $BIN "cloudflared.exe"
$TUNNEL_CONFIG = Join-Path $ROOT "zhipi-cloud\zhipi-backend\scripts\cloudflared-config.yml"

if ((Test-Path $CLOUDFLARED_EXE) -and (Test-Path $TUNNEL_CONFIG)) {
    $TUNNEL_ARGS = @("tunnel", "--config", $TUNNEL_CONFIG, "run")
    Start-Process -FilePath $CLOUDFLARED_EXE `
        -ArgumentList $TUNNEL_ARGS `
        -WorkingDirectory $ROOT `
        -WindowStyle Normal
    Start-Sleep -Milliseconds 500
    Write-Host "       Tunnel window launched." -ForegroundColor Green
} else {
    Write-Host "       [SKIP] cloudflared.exe or config not found." -ForegroundColor DarkYellow
}

# ---------------------------------------------------------
# Done
# ---------------------------------------------------------
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  All services launched." -ForegroundColor Cyan
Write-Host "  Close each window to stop that service." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to close this window..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
