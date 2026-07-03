@echo off
chcp 65001 >nul
cd /d "%~dp0..\zhipi-cloud\zhipi-backend"
if errorlevel 1 (
    echo [ERROR] Cannot enter backend directory
    pause
    exit /b 1
)
echo Starting backend server (Ctrl+C to stop)...
"C:\Users\HP\.workbuddy\binaries\python\versions\3.13.12\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
echo.
echo [Backend stopped]
pause
