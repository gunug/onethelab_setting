@echo off
setlocal enabledelayedexpansion
title Chat Socket Installer

echo ================================================
echo Chat Socket Installer - Dependencies
echo ================================================
echo(

:: ========================================
:: 1. Python
:: ========================================
echo [1/5] Checking Python...
where python > nul 2>&1
if errorlevel 1 (
    echo [!] Python not found. Installing...
    echo(
    winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo [Error] Python install failed
        echo Manual install: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo(
    echo [OK] Python installed
    echo [!] Restarting script in new terminal...
    echo(
    timeout /t 2 /nobreak > nul
    start "" cmd /k "%~f0"
    exit /b 0
) else (
    echo [OK] Python installed
)
echo(

:: ========================================
:: 2. Node.js
:: ========================================
echo [2/5] Checking Node.js...
where node > nul 2>&1
if errorlevel 1 (
    echo [!] Node.js not found. Installing...
    echo(
    winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo [Error] Node.js install failed
        echo Manual install: https://nodejs.org/
        pause
        exit /b 1
    )
    echo(
    echo [OK] Node.js installed
    echo [!] Restarting script in new terminal...
    echo(
    timeout /t 2 /nobreak > nul
    start "" cmd /k "%~f0"
    exit /b 0
) else (
    echo [OK] Node.js installed
)
echo(

:: ========================================
:: 3. ngrok
:: ========================================
echo [3/5] Checking ngrok...
where ngrok > nul 2>&1
if errorlevel 1 (
    echo [!] ngrok not found. Installing...
    echo(
    winget install ngrok.ngrok --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo [Error] ngrok install failed
        echo Manual install: https://ngrok.com/download
        pause
        exit /b 1
    )
    echo(
    echo [OK] ngrok installed
    echo [!] Restarting script in new terminal...
    echo(
    timeout /t 2 /nobreak > nul
    start "" cmd /k "%~f0"
    exit /b 0
) else (
    echo [OK] ngrok installed
)
echo(

:: ========================================
:: 4. aiohttp (Python module)
:: ========================================
echo [4/5] Checking aiohttp module...
python -c "import aiohttp" > nul 2>&1
if errorlevel 1 (
    echo [!] Installing aiohttp...
    python -m pip install aiohttp -q
    echo [OK] aiohttp installed
) else (
    echo [OK] aiohttp installed
)
echo(

:: ========================================
:: 5. Claude CLI
:: ========================================
echo [5/5] Checking Claude CLI...
where claude > nul 2>&1
if errorlevel 1 (
    echo [!] Claude CLI not found. Installing...
    echo(
    call npm install -g @anthropic-ai/claude-code
    if errorlevel 1 (
        echo [Error] Claude CLI install failed
        echo Manual install: npm install -g @anthropic-ai/claude-code
        pause
        exit /b 1
    )
    echo [OK] Claude CLI installed
) else (
    echo [OK] Claude CLI installed
)
echo(

:: ========================================
:: Done
:: ========================================
echo ================================================
echo Installation complete!
echo ================================================
echo(
echo Installed dependencies:
echo   - Python 3.12
echo   - Node.js LTS
echo   - ngrok
echo   - aiohttp (Python)
echo   - Claude CLI
echo(
echo Next step:
echo   Run config.bat to configure ngrok settings
echo   (authtoken, domain, OAuth)
echo(
echo ================================================
echo(
echo Press any key to close...
pause > nul
