@echo off
chcp 65001 >nul
echo ===== 智批云 Android 打包 =====
echo.
echo [1/3] 构建前端...
cd /d "%~dp0zhipi-cloud\zhipi-frontend"
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 前端构建失败！
    pause
    exit /b 1
)
echo.
echo [2/3] 同步 Web 资源到 Android 工程...
call npx cap sync
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 同步失败！
    pause
    exit /b 1
)
echo.
echo [3/3] 打开 Android Studio...
call npx cap open android
echo.
echo ===== 打包完成！在 Android Studio 中 Build APK =====
pause
