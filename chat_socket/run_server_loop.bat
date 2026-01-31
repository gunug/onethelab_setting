@echo off
title Chat Socket Server

REM Get port from argument, default to 8765
set "PORT=%~1"
if "%PORT%"=="" set "PORT=8765"

REM Change to parent directory (onethelab_setting) for Claude CLI working directory
cd /d "%~dp0.."

:restart_loop
echo Starting server...
echo Access: http://localhost:%PORT%
echo Working directory: %cd%
echo.
python "chat_socket/server.py" --port %PORT%

REM Exit code 100 = restart request
if %errorlevel% == 100 (
    echo.
    echo ========================================
    echo Restarting server... (applying changes)
    echo ========================================
    echo.
    timeout /t 2 /nobreak > nul
    goto restart_loop
)

echo.
echo Server stopped.
pause
