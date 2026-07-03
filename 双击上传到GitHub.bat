@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: 【核心】全局错误捕获，任何命令失败都会跳转到报错标签，防止闪退
if not defined DEBUG_GIT set "DEBUG_GIT=1"

echo ===============================
echo   Git Auto Push (Debug Mode)
echo ===============================
echo.

:: 1. 检查git是否可用
where git >nul 2>&1
if errorlevel 1 (
    echo [FATAL] 未找到git命令！
    echo 请确认已安装Git并添加到系统环境变量PATH中
    goto :error_exit
)

:: 2. 检查是否为git仓库
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo [FATAL] 当前目录不是Git仓库
    echo 请先运行: git init ^&^& git remote add origin ^<仓库地址^>
    goto :error_exit
)

:: 3. 检查是否有变更
git diff --quiet && git diff --cached --quiet
if not errorlevel 1 (
    echo [INFO] 没有检测到任何文件变更，无需推送
    goto :success_exit
)

:: 4. 生成时间戳（兼容Win10/Win11，替代已弃用的wmic）
for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set "d=%%a-%%b-%%c"
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set "t=%%a:%%b"
set "timestamp=%d% %t%"

:: 5. 暂存、提交、推送
echo [1/3] 暂存所有变更...
git add -A
if errorlevel 1 goto :error_exit

echo [2/3] 提交变更...
git commit -m "auto update: %timestamp%"
if errorlevel 1 goto :error_exit

echo [3/3] 推送到GitHub...
git push
if errorlevel 1 goto :error_exit

:success_exit
echo.
echo Done! 所有变更已成功推送到GitHub
pause
exit /b 0

:error_exit
echo.
echo ========================================
echo [ERROR] 脚本执行中断，请检查上方错误信息
echo ========================================
pause
exit /b 1