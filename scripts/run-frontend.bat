@echo off
chcp 65001 >nul
cd /d "%~dp0..\zhipi-cloud\zhipi-frontend"
if errorlevel 1 (
    echo [ERROR] Cannot enter frontend directory
    pause
    exit /b 1
)
echo Starting frontend dev server (Ctrl+C to stop)...
cmd /c npm run dev
echo.
echo [Frontend stopped]
pause
