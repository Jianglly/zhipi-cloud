@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHON=C:\Users\HP\.workbuddy\binaries\python\versions\3.13.12\python.exe"
set "URL=http://localhost:8000"

echo ===============================
echo   ZhiPi Cloud - Local Start
echo ===============================
echo.

:: --- Step 1: Check database ---
echo [1/3] Checking database ...
"%PYTHON%" "%~dp0scripts\check_db.py" >nul 2>nul
if %errorlevel% equ 0 (
    echo       Database OK
) else (
    echo       Database not initialized, running init ...
    "%PYTHON%" "%~dp0scripts\init_database.py"
    if errorlevel 1 (
        echo.
        echo [ERROR] Database init failed.
        echo         Check MySQL is running and .env is correct.
        pause
        exit /b 1
    )
)

echo.

:: --- Step 2: Start backend ---
echo [2/3] Starting backend ...
start "ZhiPi-Backend" cmd /k "%~dp0scripts\run-backend.bat"
echo       Backend launched on port 8000

echo.

:: --- Step 3: Wait for server then open browser ---
echo [3/3] Waiting for server ...
set "READY=0"
for /l %%i in (1,1,15) do (
    if "!READY!"=="0" (
        timeout /t 1 /nobreak >nul 2>nul
        curl -s -o nul -w "%%{http_code}" "%URL%/health" 2>nul | findstr 200 >nul
        if !errorlevel! equ 0 (
            set "READY=1"
        )
    )
)
if "!READY!"=="1" (
    echo       Server is ready!
    start "" "%URL%"
) else (
    echo       [WARN] Server not responding yet.
    echo       Open %URL% manually.
)

echo.
echo ===============================
echo   Backend running at %URL%
echo   Close the backend window to stop.
echo ===============================
echo.
echo Press any key to close this window.
pause >nul
