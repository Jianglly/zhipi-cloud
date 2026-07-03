@echo off

:: Self-elevate: request admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs" >nul 2>&1
    exit /b
)

echo ============================================
echo   Add zhipicloud.top to hosts file
echo ============================================
echo.

set HOSTS=%SystemRoot%\System32\drivers\etc\hosts

:: Check if already added
findstr /C:"zhipicloud.top" "%HOSTS%" >nul 2>&1
if %errorlevel%==0 (
    echo [OK] zhipicloud.top is already in hosts file.
    goto :end
)

:: Add entries
echo. >> "%HOSTS%"
echo # ZhiPi Cloud - Cloudflare Tunnel >> "%HOSTS%"
echo 104.21.78.59    zhipicloud.top >> "%HOSTS%"
echo 172.67.217.55   zhipicloud.top >> "%HOSTS%"
echo 104.21.78.59    www.zhipicloud.top >> "%HOSTS%"

if %errorlevel%==0 (
    echo [SUCCESS] Added zhipicloud.top to hosts file.
    echo.
    echo Now try opening https://zhipicloud.top in your browser!
) else (
    echo [FAILED] Could not write to hosts file.
    echo Try right-clicking this file ^> "Run as administrator"
)

:end
echo.
pause
