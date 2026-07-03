@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if errorlevel 1 (
    echo [ERROR] Cannot enter project root directory
    pause
    exit /b 1
)
echo Starting Cloudflare Tunnel (Ctrl+C to stop)...
"%~dp0..\bin\cloudflared.exe" tunnel --config "%~dp0..\zhipi-cloud\zhipi-backend\scripts\cloudflared-config.yml" run
echo.
echo [Tunnel stopped]
pause
