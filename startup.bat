@echo off
title 河南18地市气象服务
echo ============================================
echo   河南18地市气象数据网站
echo ============================================
echo.
echo Starting Flask server...
start "Flask" /MIN python app.py
timeout /t 3 /nobreak >nul

echo Starting Cloudflare Tunnel...
echo.
echo ============================================
echo   公网地址将在下方显示:
echo ============================================
cloudflared tunnel --url http://localhost:5000

pause
