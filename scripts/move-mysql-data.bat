@echo off
chcp 65001 >nul
echo ============================================
echo   MySQL Data Migration: C -^> E
echo ============================================
echo.

:: Check admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Please right-click this file and select "Run as Administrator"
    echo [ERROR] 请右键 -> 以管理员身份运行
    pause
    exit /b 1
)

set SRC=C:\ProgramData\MySQL\MySQL Server 8.0\Data
set DST=E:\MySQL\Data
set MYINI=C:\ProgramData\MySQL\MySQL Server 8.0\my.ini

echo [1/4] Stopping MySQL service...
net stop MySQL80
if %errorlevel% neq 0 (
    echo [WARN] Could not stop MySQL80, trying MySQL...
    net stop MySQL
)
echo.

echo [2/4] Copying data to E:\MySQL\Data...
if not exist "%DST%" mkdir "%DST%"
robocopy "%SRC%" "%DST%" /E /COPY:DAT /R:3 /W:3 /MT:4
if %errorlevel% gtr 7 (
    echo [ERROR] Copy failed!
    pause
    exit /b 1
)
echo [OK] Data copied successfully!
echo.

echo [3/4] Updating my.ini datadir...
powershell -Command "(Get-Content '%MYINI%') -replace 'datadir=.*', 'datadir=E:/MySQL/Data' | Set-Content '%MYINI%'"
echo [OK] datadir updated to E:/MySQL/Data
echo.

echo [4/4] Starting MySQL service...
net start MySQL80
if %errorlevel% neq 0 (
    net start MySQL
)
echo.

echo ============================================
echo   Migration Complete!
echo   Data now lives at: E:\MySQL\Data
echo ============================================
echo.
echo Test it: mysql -u root -p -P 3307 -e "SHOW DATABASES;"
echo.
pause
