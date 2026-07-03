@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PYTHON=C:\Users\HP\.workbuddy\binaries\python\versions\3.13.12\python.exe"
set "BACKEND=%~dp0zhipi-cloud\zhipi-backend"
set "URL=http://localhost:8000"

echo ===============================
echo   ZhiPi Cloud - Local Start
echo ===============================
echo.

:: ─── Step 1: 检查数据库是否已初始化 ───
echo [1/3] Checking database ...
"%PYTHON%" -c "
import sys, os
sys.path.insert(0, os.path.join(r'%BACKEND%'))
import pymysql

env = {}
with open(os.path.join(r'%BACKEND%', '.env'), 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()

try:
    conn = pymysql.connect(
        host=env.get('DB_HOST', 'localhost'),
        port=int(env.get('DB_PORT', '3306')),
        user=env['DB_USER'], password=env['DB_PASSWORD'],
        database=env.get('DB_NAME', 'zhipi_cloud'), charset='utf8mb4'
    )
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM admin')
    count = cursor.fetchone()[0]
    cursor.close(); conn.close()
    if count > 0:
        print('READY')
    else:
        print('EMPTY')
except Exception:
    print('MISSING')
" 2>nul | findstr READY >nul

if %errorlevel% equ 0 (
    echo       Database OK - tables exist
) else (
    echo       Database not initialized, running init script ...
    "%PYTHON%" "%~dp0scripts\init_database.py"
    if errorlevel 1 (
        echo.
        echo [ERROR] Database init failed. Check MySQL is running and .env is correct.
        pause
        exit /b 1
    )
)

echo.

:: ─── Step 2: 启动后端 ───
echo [2/3] Starting backend ...
start "ZhiPi-Backend" cmd /k "%~dp0scripts\run-backend.bat"
echo       Backend launched on port 8000

echo.

:: ─── Step 3: 等待后端就绪后打开浏览器 ───
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
if "%READY%"=="1" (
    echo       Server is ready!
    start "" "%URL%"
) else (
    echo       [WARN] Server not responding yet, open %URL% manually
)

echo.
echo ===============================
echo   Backend running at %URL%
echo   Close the backend window to stop.
echo ===============================
echo.
echo Press any key to close this window.
pause >nul
