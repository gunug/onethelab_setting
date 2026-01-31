@echo off
chcp 65001 > nul
title Chat Socket Config

echo ================================================
echo Chat Socket Config - ngrok Settings
echo ================================================
echo.

:: ========================================
:: 1. Port number
:: ========================================
echo [1/4] Port number setup...
echo.
echo ================================================
echo Default port: 8765
echo (Press Enter to use default)
echo ================================================
echo.
set /p SERVER_PORT=Port number:
if "%SERVER_PORT%"=="" (
    set "SERVER_PORT=8765"
    echo [OK] Using default port: 8765
) else (
    echo [OK] Port: %SERVER_PORT%
)
echo.

:: ========================================
:: 2. ngrok authtoken
:: ========================================
echo [2/4] ngrok authtoken setup...
echo.
echo ================================================
echo 1. Go to https://dashboard.ngrok.com
echo 2. Copy 'Your Authtoken'
echo 3. Paste below
echo (Press Enter to skip if already configured)
echo ================================================
echo.
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
echo.

:: ========================================
:: 3. Static domain (optional)
:: ========================================
echo [3/4] Static domain setup...
echo.
echo ================================================
echo Example: myapp.ngrok-free.app
echo (Press Enter to skip - will use random URL)
echo ================================================
echo.
set /p NGROK_DOMAIN=Static domain:
if "%NGROK_DOMAIN%"=="" (
    echo [Skip] Will use random URL
) else (
    echo [OK] Domain: %NGROK_DOMAIN%
)
echo.

:: ========================================
:: 4. Google OAuth (optional)
:: ========================================
echo [4/4] Google OAuth setup...
echo.
echo ================================================
echo Enter allowed Google email address
echo Example: user@gmail.com
echo (Press Enter to skip - public access)
echo ================================================
echo.
set /p OAUTH_EMAIL=Allowed email:
if "%OAUTH_EMAIL%"=="" (
    echo [Skip] Public access (no OAuth)
) else (
    echo [OK] OAuth email: %OAUTH_EMAIL%
)
echo.

:: ========================================
:: Generate run_ngrok.bat
:: ========================================
echo [Info] Generating run_ngrok.bat...

set "OUTPUT_FILE=%~dp0run_ngrok.bat"

:: Build ngrok command
set "NGROK_CMD=ngrok http %SERVER_PORT%"
set "PORT_DISPLAY=%SERVER_PORT%"
set "DOMAIN_DISPLAY=Random URL"
set "OAUTH_DISPLAY=Public"

if not "%NGROK_DOMAIN%"=="" (
    set "NGROK_CMD=%NGROK_CMD% --domain=%NGROK_DOMAIN%"
    set "DOMAIN_DISPLAY=https://%NGROK_DOMAIN%"
)

if not "%OAUTH_EMAIL%"=="" (
    set "NGROK_CMD=%NGROK_CMD% --oauth=google --oauth-allow-email=%OAUTH_EMAIL%"
    set "OAUTH_DISPLAY=%OAUTH_EMAIL%"
)

:: Write run_ngrok.bat using parentheses block
(
echo @echo off
echo title Chat Socket + ngrok
echo.
echo REM Store script directory before start command
echo set "SCRIPT_DIR=%%~dp0"
echo.
echo echo ================================================
echo echo Chat Socket + ngrok
echo echo ================================================
echo echo.
echo echo Port: %PORT_DISPLAY%
echo echo Domain: %DOMAIN_DISPLAY%
echo echo OAuth: %OAUTH_DISPLAY%
echo echo.
echo echo [1] Starting server (with restart loop)...
echo start "Chat Socket Server" /D "%%SCRIPT_DIR%%" cmd /k "run_server_loop.bat %SERVER_PORT%"
echo echo [Wait] 3 seconds...
echo timeout /t 3 /nobreak ^> nul
echo echo [2] Starting ngrok tunnel...
echo echo.
echo %NGROK_CMD%
echo echo.
echo echo ================================================
echo echo ngrok closed.
echo echo ================================================
echo pause
) > "%OUTPUT_FILE%"

echo [OK] run_ngrok.bat generated
echo.

:: ========================================
:: Done
:: ========================================
echo ================================================
echo Configuration complete!
echo ================================================
echo.
echo Settings:
echo   Port:   %PORT_DISPLAY%
echo   Domain: %DOMAIN_DISPLAY%
echo   OAuth:  %OAUTH_DISPLAY%
echo.
echo How to run:
echo   run.bat        - Local server only
echo   run_ngrok.bat  - Server + ngrok tunnel
echo.
echo ================================================
echo.
echo Press any key to close...
pause > nul
