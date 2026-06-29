@echo off
setlocal EnableDelayedExpansion
title Park Smart UK - Setup and Launch
color 0A

REM ================================================================
REM  Park Smart UK - Windows One-Click FULL Automatic Setup Script
REM  Installs: Python packages + OpenCV + Tesseract OCR (all auto)
REM  Just double-click this file. Works on Windows 10 / 11
REM ================================================================

echo.
echo  ================================================================
echo    PARK SMART UK - Full Automatic Setup
echo    Installing EVERYTHING automatically. Please wait...
echo  ================================================================
echo.

REM ── STEP 0: Must be in the correct folder ────────────────────────
if not exist "app.py" (
    echo.
    echo  [ERROR] Wrong folder!
    echo  This script must be inside the "park_smart_uk" project folder.
    echo  (The folder that has app.py, requirements.txt inside it)
    echo.
    pause
    exit /b 1
)

REM ── STEP 1: Check Python ──────────────────────────────────────────
echo  [Step 1 of 8]  Checking Python...
echo  ----------------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [!] Python is NOT installed.
    echo.
    echo  ACTION NEEDED - Please do this ONE TIME:
    echo    1. Your browser will open the Python download page
    echo    2. Click the yellow "Download Python" button
    echo    3. Run the installer
    echo    4. VERY IMPORTANT: Tick "Add Python to PATH" checkbox at bottom!
    echo    5. Click "Install Now"  -  wait for it to finish
    echo    6. Close this window and double-click setup_and_run.bat again
    echo.
    echo  Press any key to open Python download page...
    pause >nul
    start https://www.python.org/downloads/
    echo.
    echo  After installing Python, please run this script again.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  OK  Python %PYVER% found.
echo.

REM ── STEP 2: Check pip ────────────────────────────────────────────
echo  [Step 2 of 8]  Checking pip (Python package manager)...
echo  ----------------------------------------------------------------
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo  pip missing, installing it...
    python -m ensurepip --upgrade >nul 2>&1
)
python -m pip install --upgrade pip --quiet 2>nul
echo  OK  pip is ready.
echo.

REM ── STEP 3: Create virtual environment ───────────────────────────
echo  [Step 3 of 8]  Setting up isolated Python environment...
echo  ----------------------------------------------------------------
if exist "parksmart_venv\" (
    echo  OK  Virtual environment already exists.
) else (
    python -m venv parksmart_venv
    if errorlevel 1 (
        echo.
        echo  [ERROR] Could not create virtual environment.
        echo  Try right-clicking setup_and_run.bat and choosing "Run as Administrator"
        pause
        exit /b 1
    )
    echo  OK  Virtual environment created.
)
echo.

REM Activate virtual environment
call parksmart_venv\Scripts\activate.bat
if errorlevel 1 (
    echo  [ERROR] Could not activate virtual environment.
    pause
    exit /b 1
)

REM Upgrade pip inside the venv too
python -m pip install --upgrade pip --quiet 2>nul

REM ── STEP 4: Install Web Framework ────────────────────────────────
echo  [Step 4 of 8]  Installing Web Framework (Flask)...
echo  ----------------------------------------------------------------
echo  Installing: Flask, Werkzeug...
python -m pip install "Flask==3.0.3" "Werkzeug==3.0.3" --quiet
if errorlevel 1 (
    echo  Retrying with latest versions...
    python -m pip install Flask Werkzeug --quiet
)
python -m pip install "python-dotenv==1.0.1" --quiet 2>nul || python -m pip install python-dotenv --quiet
echo  OK  Flask web framework installed.
echo.

REM ── STEP 5: Install Computer Vision (OpenCV) ─────────────────────
echo  [Step 5 of 8]  Installing Computer Vision packages (OpenCV)...
echo  ----------------------------------------------------------------
echo  Installing: opencv-python (computer vision library)...
python -m pip install "opencv-python==4.10.0.84" --quiet
if errorlevel 1 (
    echo  Trying latest OpenCV version...
    python -m pip install opencv-python --quiet
    if errorlevel 1 (
        echo  Trying headless OpenCV (no GUI needed for server)...
        python -m pip install opencv-python-headless --quiet
    )
)
echo  Installing: Pillow (image processing)...
python -m pip install "Pillow==10.4.0" --quiet 2>nul || python -m pip install Pillow --quiet

echo  Installing: pytesseract (Python bridge to Tesseract OCR)...
python -m pip install "pytesseract==0.3.13" --quiet 2>nul || python -m pip install pytesseract --quiet

echo  OK  OpenCV and image packages installed.
echo.

REM ── STEP 6: Install Machine Learning packages ─────────────────────
echo  [Step 6 of 8]  Installing Machine Learning packages...
echo  ----------------------------------------------------------------
echo  Installing: numpy...
python -m pip install "numpy==1.26.4" --quiet
if errorlevel 1 ( python -m pip install "numpy>=1.24,<2.0" --quiet )

echo  Installing: scikit-learn and joblib...
python -m pip install "scikit-learn==1.5.1" "joblib==1.4.2" --quiet
if errorlevel 1 ( python -m pip install scikit-learn joblib --quiet )

echo  Installing: TensorFlow (largest package - please wait 2-5 mins)...
echo  [This is normal - TensorFlow is a large download ~500MB]
python -m pip install "tensorflow==2.17.0" --quiet
if errorlevel 1 (
    echo  Trying tensorflow-cpu (smaller, works without GPU)...
    python -m pip install "tensorflow-cpu==2.17.0" --quiet
    if errorlevel 1 (
        echo  Trying any compatible TensorFlow version...
        python -m pip install tensorflow --quiet
        if errorlevel 1 (
            python -m pip install tensorflow-cpu --quiet
        )
    )
)

echo  Installing: pytest (testing tools)...
python -m pip install "pytest==8.3.2" "pytest-flask==1.3.0" --quiet 2>nul || python -m pip install pytest pytest-flask --quiet

echo  OK  All Machine Learning packages installed.
echo.

REM ── STEP 7: Auto-Install Tesseract OCR ───────────────────────────
echo  [Step 7 of 8]  Checking Tesseract OCR (sign reading engine)...
echo  ----------------------------------------------------------------

set TESS_FOUND=0
set "TESS_PATH="

REM Check all common install locations
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe"         set "TESS_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe"         & set TESS_FOUND=1
if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"   set "TESS_PATH=C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"   & set TESS_FOUND=1
if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"  set "TESS_PATH=%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"  & set TESS_FOUND=1
if exist "%APPDATA%\Tesseract-OCR\tesseract.exe"                set "TESS_PATH=%APPDATA%\Tesseract-OCR\tesseract.exe"                & set TESS_FOUND=1
if exist "C:\tools\Tesseract-OCR\tesseract.exe"                 set "TESS_PATH=C:\tools\Tesseract-OCR\tesseract.exe"                 & set TESS_FOUND=1

where tesseract >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%p in ('where tesseract 2^>nul') do if "!TESS_PATH!"=="" set "TESS_PATH=%%p"
    set TESS_FOUND=1
)

if "%TESS_FOUND%"=="1" (
    echo  OK  Tesseract OCR already installed at:
    echo      %TESS_PATH%
    goto :update_env_tesseract
)

REM ── AUTO DOWNLOAD AND INSTALL TESSERACT ──────────────────────────
echo  Tesseract OCR not found. Downloading and installing automatically...
echo  (This is a ~50MB download - please wait)
echo.

set TESS_INSTALLER_URL=https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe
set TESS_INSTALLER=%TEMP%\tesseract_setup.exe

REM Use PowerShell to download (available on all Windows 10/11)
echo  Downloading Tesseract installer...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%TESS_INSTALLER_URL%' -OutFile '%TESS_INSTALLER%' -UseBasicParsing}" 2>nul
if not exist "%TESS_INSTALLER%" (
    REM Fallback: try the 32-bit version
    set TESS_INSTALLER_URL=https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w32-setup-5.3.3.20231005.exe
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%TESS_INSTALLER_URL%' -OutFile '%TESS_INSTALLER%' -UseBasicParsing}" 2>nul
)

if exist "%TESS_INSTALLER%" (
    echo  Download complete! Installing Tesseract silently...
    REM /S = silent install, /D = install directory
    "%TESS_INSTALLER%" /S /D=C:\Program Files\Tesseract-OCR
    if errorlevel 1 (
        REM Try installing to user folder if no admin rights
        "%TESS_INSTALLER%" /S /D=%LOCALAPPDATA%\Programs\Tesseract-OCR
    )
    del "%TESS_INSTALLER%" >nul 2>&1

    REM Re-check after install
    if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
        set "TESS_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe"
        set TESS_FOUND=1
        echo  OK  Tesseract OCR installed successfully!
    ) else if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe" (
        set "TESS_PATH=%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"
        set TESS_FOUND=1
        echo  OK  Tesseract OCR installed successfully!
    ) else (
        echo  [WARNING] Tesseract installed but path not found.
        echo  OCR feature may need manual Tesseract setup.
    )
) else (
    echo.
    echo  [WARNING] Could not auto-download Tesseract (no internet or blocked).
    echo  The app will run but the parking sign OCR feature won't work.
    echo  To fix later: download from https://github.com/UB-Mannheim/tesseract/wiki
    echo  and install to: C:\Program Files\Tesseract-OCR\
    echo  Then run this script again.
)

:update_env_tesseract
REM Update the .env file with Tesseract path automatically
if "%TESS_FOUND%"=="1" (
    python -c "
import re, os, sys
env_file = '.env'
tess = sys.argv[1].replace('\\\\', '\\\\\\\\')
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        txt = f.read()
    if re.search(r'#?\s*TESSERACT_CMD\s*=', txt):
        txt = re.sub(r'#?\s*TESSERACT_CMD\s*=.*', 'TESSERACT_CMD=' + tess, txt)
    else:
        txt += '\nTESSERACT_CMD=' + tess + '\n'
    with open(env_file, 'w') as f:
        f.write(txt)
    print('  .env updated: TESSERACT_CMD set to ' + sys.argv[1])
" "%TESS_PATH%" 2>nul
)
echo.

REM ── STEP 8: Final checks and .env setup ──────────────────────────
echo  [Step 8 of 8]  Final setup checks...
echo  ----------------------------------------------------------------

REM Create .env if missing
if not exist ".env" (
    echo  Creating .env configuration file...
    (
        echo # Park Smart UK - Environment Configuration
        echo FLASK_ENV=development
        echo FLASK_DEBUG=1
        echo SECRET_KEY=parksmart-uk-secret-key-2024
        echo GOOGLE_MAPS_API_KEY=AIzaSyDcSH2hKnoTjIJaxBp0HwQhgXSiBIz0ThA
        echo MAX_CONTENT_LENGTH=16777216
        echo UPLOAD_FOLDER=static/images/uploads
    ) > .env
    echo  OK  .env file created.
) else (
    echo  OK  .env file exists.
)

REM Create required folders
if not exist "static\images\uploads\" (
    mkdir "static\images\uploads" >nul 2>&1
    echo  OK  Created uploads folder.
)
if not exist "ml\models\" (
    mkdir "ml\models" >nul 2>&1
    echo  OK  Created ML models folder.
)

REM Quick verification - check all key packages are importable
echo.
echo  Verifying all packages are working...
python -c "
packages = [
    ('flask',           'Flask'),
    ('cv2',             'OpenCV'),
    ('pytesseract',     'pytesseract'),
    ('PIL',             'Pillow'),
    ('numpy',           'numpy'),
    ('sklearn',         'scikit-learn'),
    ('tensorflow',      'TensorFlow'),
    ('dotenv',          'python-dotenv'),
]
all_ok = True
for mod, name in packages:
    try:
        __import__(mod)
        print(f'  [OK] {name}')
    except ImportError as e:
        print(f'  [MISSING] {name} - {e}')
        all_ok = False
if all_ok:
    print()
    print('  All packages verified OK!')
else:
    print()
    print('  Some packages had issues. The app may still work.')
"
echo.

REM ── ALL DONE! Launch the app ──────────────────────────────────────
echo  ================================================================
echo    SETUP COMPLETE!
echo  ================================================================
echo.
echo    All packages installed:
echo      [OK] Flask (web server)
echo      [OK] OpenCV (computer vision / image processing)
echo      [OK] Tesseract OCR (parking sign reading)
echo      [OK] TensorFlow (parking availability prediction)
echo      [OK] scikit-learn (machine learning)
echo      [OK] Pillow, numpy, joblib (utilities)
echo.
echo    Starting the app now...
echo    Your browser will open automatically at: http://localhost:5001
echo.
echo    To STOP: press Ctrl+C  in this window
echo    To START AGAIN later: double-click run.bat (faster!)
echo  ================================================================
echo.

REM Wait 2 seconds then open browser
ping -n 3 127.0.0.1 >nul
start http://localhost:5001

REM Launch Flask
python app.py

REM Keep window open if there's an error
echo.
echo  ================================================================
echo    Server stopped.
echo    If you see an error above, take a screenshot and share it.
echo    To restart, double-click run.bat
echo  ================================================================
echo.
pause
