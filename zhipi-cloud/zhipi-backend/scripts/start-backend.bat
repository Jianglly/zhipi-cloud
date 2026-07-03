@echo off
chcp 65001 >nul
echo ===============================
echo   智批云 - 启动后端服务
echo ===============================
echo.

REM 项目根目录（此文件在 zhipi-cloud\zhipi-backend\scripts\）
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..\..\..
set BACKEND_DIR=%PROJECT_ROOT%\zhipi-cloud\zhipi-backend
set PYTHON_EXE=C:\Users\HP\.workbuddy\binaries\python\versions\3.13.12\python.exe

echo [1/3] 检查 Python 环境...
if not exist "%PYTHON_EXE%" (
    echo [错误] 找不到 Python：%PYTHON_EXE%
    echo 请先安装 WorkBuddy 或手动修改此文件中的 PYTHON_EXE 路径
    pause
    exit /b 1
)
echo        OK: %PYTHON_EXE%
echo.

echo [2/3] 检查后端目录...
if not exist "%BACKEND_DIR%\main.py" (
    echo [错误] 找不到 main.py：%BACKEND_DIR%
    pause
    exit /b 1
)
echo        OK: %BACKEND_DIR%
echo.

echo [3/3] 启动后端服务（端口 8000）...
echo        关闭此窗口将停止服务
echo.
cd /d "%BACKEND_DIR%"
"%PYTHON_EXE%" -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
