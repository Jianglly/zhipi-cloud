@echo off
chcp 65001 >nul
cd /d %~dp0
echo ============================================
echo   ZhiPi Cloud - Database Init
echo ============================================
echo.
echo   Make sure MySQL service is running!
echo   If MySQL is not installed, install MySQL 8.0+
echo.
python init_db.py
pause
