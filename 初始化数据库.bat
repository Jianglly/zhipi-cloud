@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   智批云 - 数据库一键初始化
echo ============================================
echo.
echo   确保 MySQL 服务已启动！
echo   如果还没装 MySQL，请先安装 MySQL 8.0+
echo.
python 初始化数据库.py
pause
