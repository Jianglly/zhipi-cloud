@echo off
chcp 65001 >nul 2>&1
title ZhiPi Cloud - 网络共享

echo.
echo ==================================================
echo      ZhiPi Cloud - 网络共享入口
echo ==================================================
echo.
echo [提示] 请先以"网络共享模式"启动系统：
echo   双击 启动智批云.bat → 选 [2] 网络共享
echo.
echo 系统启动完成后，按回车启动内网穿透...
pause >nul

cd /d "E:\Homwork\数据库系统\手工试卷批阅"
python 内网穿透启动.py
pause
