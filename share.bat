@echo off
cd /d %~dp0
title ZhiPi Cloud - Cloudflare Tunnel
echo.
echo  Starting Cloudflare Tunnel for zhipicloud.top...
echo.

cloudflared.exe tunnel --config cloudflared-config.yml run zhipi-cloud

pause
