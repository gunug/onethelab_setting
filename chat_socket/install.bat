@echo off
setlocal enabledelayedexpansion
title Chat Socket Installer

echo ================================================
echo Chat Socket Installer
echo ================================================
echo(

:: ========================================
:: Load existing settings from run_ngrok.bat
:: ========================================
set "EXISTING_DOMAIN="
set "EXISTING_EMAIL="
set "CONFIG_FILE=%~dp0run_ngrok.bat"

if exist "%CONFIG_FILE%" (
    for /f "tokens=*" %%a in ('findstr /c:"--domain=" "%CONFIG_FILE%"') do (
        set "LINE=%%a"
        for %%b in (!LINE!) do (
            set "TOKEN=%%b"
            if "!TOKEN:~0,9!"=="--domain=" (
                set "EXISTING_DOMAIN=!TOKEN:~9!"
            )
            if "!TOKEN:~0,21!"=="--oauth-allow-email=" (
                set "EXISTING_EMAIL=!TOKEN:~21!"
            )
        )
    )
)

:: ========================================
:: 1. Python
:: ========================================
echo [1/6] Checking Python...
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
:: 2. ngrok
:: ========================================
echo [2/6] Checking ngrok...
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
:: 3. aiohttp
:: ========================================
echo [3/6] Checking aiohttp module...
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
:: 4. ngrok authtoken
:: ========================================
echo [4/6] ngrok authtoken setup...
echo(
echo ================================================
echo 1. Go to https://dashboard.ngrok.com
echo 2. Copy 'Your Authtoken'
echo 3. Paste below
echo (Press Enter to skip if already configured)
echo ================================================
echo(
set /p NGROK_TOKEN=Authtoken:
if not "%NGROK_TOKEN%"=="" (
    ngrok config add-authtoken %NGROK_TOKEN%
    if errorlevel 1 (
        echo [Error] authtoken setup failed
        pause
        exit /b 1
    )
    echo [OK] authtoken configured
) else (
    echo [Skip] Keep existing config
)
echo(

:: ========================================
:: 5. Static domain (optional)
:: ========================================
echo [5/6] Static domain setup (Personal plan or higher)...
echo(
echo ================================================
echo Example: myapp.ngrok-free.app
if not "%EXISTING_DOMAIN%"=="" (
    echo Current: %EXISTING_DOMAIN%
    echo (Press Enter to keep current value)
) else (
    echo (Press Enter to skip - will use random URL)
)
echo ================================================
echo(
set /p NGROK_DOMAIN=Static domain:
if "%NGROK_DOMAIN%"=="" (
    if not "%EXISTING_DOMAIN%"=="" (
        set "NGROK_DOMAIN=%EXISTING_DOMAIN%"
        echo [OK] Keep: %EXISTING_DOMAIN%
    ) else (
        echo [Skip] Will use random URL
    )
) else (
    echo [OK] Domain: %NGROK_DOMAIN%
)
echo(

:: ========================================
:: 6. Google OAuth (optional)
:: ========================================
echo [6/6] Google OAuth setup (Personal plan or higher)...
echo(
echo ================================================
echo Enter allowed Google email address
echo Example: user@gmail.com
if not "%EXISTING_EMAIL%"=="" (
    echo Current: %EXISTING_EMAIL%
    echo (Press Enter to keep current value)
) else (
    echo (Press Enter to skip - public access)
)
echo ================================================
echo(
set /p OAUTH_EMAIL=Allowed email:
if "%OAUTH_EMAIL%"=="" (
    if not "%EXISTING_EMAIL%"=="" (
        set "OAUTH_EMAIL=%EXISTING_EMAIL%"
        echo [OK] Keep: %EXISTING_EMAIL%
    ) else (
        echo [Skip] Public access (no OAuth)
    )
) else (
    echo [OK] OAuth email: %OAUTH_EMAIL%
)
echo(

:: ========================================
:: Generate run_ngrok.bat
:: ========================================
echo [Info] Generating run_ngrok.bat...

set "NGROK_CMD=ngrok http 8765"
set "DOMAIN_DISPLAY=Random URL"
set "OAUTH_DISPLAY=Public"

if not "%NGROK_DOMAIN%"=="" (
    set "NGROK_CMD=!NGROK_CMD! --domain=%NGROK_DOMAIN%"
    set "DOMAIN_DISPLAY=https://%NGROK_DOMAIN%"
)

if not "%OAUTH_EMAIL%"=="" (
    set "NGROK_CMD=!NGROK_CMD! --oauth=google --oauth-allow-email=%OAUTH_EMAIL%"
    set "OAUTH_DISPLAY=%OAUTH_EMAIL%"
)

set "OUTPUT_FILE=%~dp0run_ngrok.bat"

echo @echo off> "%OUTPUT_FILE%"
echo title Chat Socket + ngrok>> "%OUTPUT_FILE%"
echo(>> "%OUTPUT_FILE%"
echo echo ================================================>> "%OUTPUT_FILE%"
echo echo Chat Socket + ngrok>> "%OUTPUT_FILE%"
echo echo ================================================>> "%OUTPUT_FILE%"
echo echo(>> "%OUTPUT_FILE%"
echo echo Domain: %DOMAIN_DISPLAY%>> "%OUTPUT_FILE%"
echo echo OAuth: %OAUTH_DISPLAY%>> "%OUTPUT_FILE%"
echo echo(>> "%OUTPUT_FILE%"
echo echo [1] Starting server...>> "%OUTPUT_FILE%"
echo start "Chat Socket Server" cmd /k "cd /d %%~dp0 ^&^& python server.py">> "%OUTPUT_FILE%"
echo echo [Wait] 3 seconds...>> "%OUTPUT_FILE%"
echo timeout /t 3 /nobreak ^> nul>> "%OUTPUT_FILE%"
echo echo [2] Starting ngrok tunnel...>> "%OUTPUT_FILE%"
echo echo(>> "%OUTPUT_FILE%"
echo !NGROK_CMD!>> "%OUTPUT_FILE%"
echo echo(>> "%OUTPUT_FILE%"
echo echo ================================================>> "%OUTPUT_FILE%"
echo echo ngrok closed.>> "%OUTPUT_FILE%"
echo echo ================================================>> "%OUTPUT_FILE%"
echo pause>> "%OUTPUT_FILE%"

echo [OK] run_ngrok.bat generated
echo(

:: ========================================
:: Done
:: ========================================
echo ================================================
echo Installation complete!
echo ================================================
echo(
echo Settings:
echo   Domain: %DOMAIN_DISPLAY%
echo   OAuth:  %OAUTH_DISPLAY%
echo(
echo How to run:
echo   run.bat        - Local server only
echo   run_ngrok.bat  - Server + ngrok tunnel
echo(
echo ================================================
echo(
echo Press any key to close...
pause > nul
