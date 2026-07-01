@echo off
setlocal

set "PROJECT_ROOT=E:\Homwork\数据库系统\手工试卷批阅"
set "BACKEND_DIR=%PROJECT_ROOT%\zhipi-cloud\zhipi-backend"
set "FRONTEND_DIR=%PROJECT_ROOT%\zhipi-cloud\zhipi-frontend"

REM --- Step 1: Check Python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYV=%%i
echo [OK] Python %PYV%

REM --- Step 2: Check Node.js ---
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found! Install from https://nodejs.org/
    pause
    exit /b 1
)
for /f %%i in ('node --version') do set NV=%%i
echo [OK] Node.js %NV%

REM --- Step 3: Try start MySQL ---
sc query MySQL80 >nul 2>&1
if not errorlevel 1 (
    net start MySQL80 >nul 2>&1
    echo [OK] MySQL80 started
    goto :mysql_done
)
sc query MySQL >nul 2>&1
if not errorlevel 1 (
    net start MySQL >nul 2>&1
    echo [OK] MySQL started
) else (
    echo [WARN] MySQL service NOT found. Please start manually.
)
:mysql_done

REM --- Step 4: Start Backend ---
cd /d "%BACKEND_DIR%"
if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo [INFO] .env created. Edit DB_PASSWORD then re-run this script.
        pause
        exit /b 0
    ) else (
        echo [ERROR] No .env.example found!
        pause
        exit /b 1
    )
)

start "ZhiPi-Backend" cmd /k "cd /d %BACKEND_DIR% & echo Backend starting on http://localhost:8000 & .venv\Scripts\python.exe main.py"
echo [OK] Backend launching...

REM --- Step 5: Start Frontend ---
cd /d "%FRONTEND_DIR%"
if not exist node_modules (
    echo Installing frontend deps... (first run only)
    call npm install
)

start "ZhiPi-Frontend" cmd /k "cd /d %FRONTEND_DIR% & echo Frontend starting on http://localhost:5173 & npm run dev"
echo [OK] Frontend launching...

echo.
echo ============================================
echo   ZhiPi Cloud System - ALL SERVICES STARTED!
echo -------------------------------------------
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000
echo   API Docs : http://localhost:8000/docs
echo -------------------------------------------
echo   Teacher  : T001 / 123456
echo   Student  : 2414100311 / 123456
echo ============================================
echo.
pause
endlocal
