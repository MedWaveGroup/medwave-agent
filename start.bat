@echo off
REM MedWave Ad Tracker — One-click startup for Windows
REM Just double-click this file

echo.
echo   ========================================
echo        MedWave Ad Tracker
echo   ========================================
echo.

cd /d "%~dp0"

REM Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo   Python is not installed.
    echo   Download it from: https://www.python.org/downloads/
    echo   Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

REM Install dependencies
echo   Installing dependencies...
python -m pip install -q -r requirements.txt
echo   Done.
echo.

REM Check .env
if not exist .env (
    echo   No .env file found — copying from .env.example
    copy .env.example .env >nul
    echo   Please edit .env with your API keys, then run this again.
    echo.
    pause
    exit /b 1
)

echo   Starting dashboard...
echo   ----------------------------------------
echo.
echo   Open your browser to: http://localhost:8000
echo.
echo   Press Ctrl+C to stop.
echo   ----------------------------------------
echo.

python run.py
pause
