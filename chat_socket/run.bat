@echo off
echo ========================================
echo Chat Socket Server Start
echo ========================================
echo.

REM Check aiohttp
pip show aiohttp > nul 2>&1
if errorlevel 1 (
    echo Installing aiohttp library...
    pip install aiohttp
    echo.
)

:restart_loop
echo Starting server...
echo Access: http://localhost:8765
echo.
python "%~dp0server.py"

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
