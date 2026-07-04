@echo off
chcp 65001 >nul
cd /d "%~dp0.."

set "AUTO=0"
if /i "%~1"=="--auto" set "AUTO=1"

echo ===============================
echo   ZhiPi Cloud - Init Database
echo ===============================
echo.
echo This will create all tables and seed demo data.
echo Make sure MySQL is running and zhipi-backend/.env is configured.
echo.
if "%AUTO%"=="0" pause

set "PYTHON=C:\Users\HP\.workbuddy\binaries\python\versions\3.13.12\python.exe"

echo Running init script ...
"%PYTHON%" scripts\init_database.py
if errorlevel 1 (
    echo.
    echo [ERROR] Init failed. Check the messages above.
    if "%AUTO%"=="0" pause
    exit /b 1
)

echo.
if "%AUTO%"=="0" pause
exit /b 0
