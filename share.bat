@echo off
chcp 65001 >nul 2>&1
title ZhiPi Cloud - Network Share

echo.
echo ==================================================
echo      ZhiPi Cloud - Network Sharing
echo ==================================================
echo.
echo [INFO] Start the system in "shared" mode first:
echo   Double-click start.bat and choose [2] Network Share
echo.
echo Press Enter to start tunnel after system is ready...
pause >nul

cd /d %~dp0
python tunnel.py
pause
