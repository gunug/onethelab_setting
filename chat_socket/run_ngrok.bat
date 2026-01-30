@echo off
title Chat Socket + ngrok

echo ================================================
echo Chat Socket + ngrok
echo ================================================
echo(
echo Domain: https://onethelab.ngrok.dev
echo OAuth: gunug850@gmail.com
echo(
echo [1] Starting server...
REM Start server in separate window with restart loop (parent directory)
REM Use absolute path for bat file, /D sets working directory
start "Chat Socket Server" /D "%~dp0.." cmd /k ""%~dp0run_server_loop.bat""
echo [Wait] 3 seconds...
timeout /t 3 /nobreak > nul
echo [2] Starting ngrok tunnel...
echo(
ngrok http 8765 --domain=onethelab.ngrok.dev --oauth=google --oauth-allow-email=gunug850@gmail.com
echo(
echo ================================================
echo ngrok closed.
echo ================================================
pause
