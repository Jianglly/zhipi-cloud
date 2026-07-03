@echo off
cd /d %~dp0\..
title ZhiPi Cloud - Cloudflare Tunnel
echo.
echo  Starting Cloudflare Tunnel for zhipicloud.top...
echo.

bin\cloudflared.exe tunnel --config zhipi-cloud\zhipi-backend\cloudflared-config.yml run zhipi-cloud

pause
