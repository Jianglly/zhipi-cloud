@echo off
chcp 65001 >nul 2>&1
title Install Cloudflared

echo.
echo ============================================
echo   Installing Cloudflare Tunnel (cloudflared)
echo ============================================
echo.

echo [1/3] Installing via winget...
winget install --id Cloudflare.cloudflared --accept-source-agreements --accept-package-agreements
if %errorlevel% neq 0 (
    echo.
    echo winget failed, trying direct download...
    
    echo [2/3] Downloading from GitHub...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%~dp0cloudflared_new.exe' -UseBasicParsing"
    
    if exist "%~dp0cloudflared_new.exe" (
        move /y "%~dp0cloudflared_new.exe" "%~dp0cloudflared.exe" >nul 2>&1
        echo Download OK
    ) else (
        echo Download FAILED!
        echo Please install manually: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
        pause
        exit /b 1
    )
) else (
    echo.
    echo [2/3] winget installed OK
)

echo.
echo [3/3] Verifying...
where cloudflared >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('cloudflared --version') do set CFVER=%%i
    echo Installed: %CFVER%
) else if exist "%~dp0cloudflared.exe" (
    echo cloudflared.exe is in project folder
) else (
    echo ERROR: cloudflared not found!
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Installation Complete!
echo ============================================
echo.
echo Now run these commands in cmd:
echo   cd %~dp0
echo   cloudflared.exe tunnel login
echo   cloudflared.exe tunnel create zhipi-cloud
echo   cloudflared.exe tunnel route dns zhipi-cloud zhipicloud.top
echo.

pause
