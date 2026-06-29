@echo off
title Park Smart UK
color 0A

echo.
echo  =========================================
echo   PARK SMART UK - Starting Server...
echo  =========================================
echo.

if not exist "app.py" (
    echo [ERROR] Run this from the Park Smart UK project folder.
    pause
    exit /b 1
)

if not exist "parksmart_venv\" (
    echo [!] Virtual environment not found.
    echo     Please run setup_and_run.bat first to do the initial setup.
    pause
    exit /b 1
)

call parksmart_venv\Scripts\activate.bat

echo  Opening browser at http://localhost:5001
echo  Press Ctrl+C to stop the server.
echo.

ping -n 2 127.0.0.1 >nul
start http://localhost:5001
python app.py

echo.
pause
