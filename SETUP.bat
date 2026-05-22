@echo off
title Expert Social Media Planner - Setup
echo ============================================================
echo   EXPERT SOCIAL MEDIA PLANNER - First-Time Setup
echo ============================================================
echo.

cd /d "%~dp0"

REM Try to find Python in common locations
set "PYTHON_EXE="
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python310\python.exe"
) do (
    if exist %%P (
        set "PYTHON_EXE=%%~P"
        goto :found
    )
)

REM Try PATH (skip the Microsoft Store stub)
for /f "delims=" %%i in ('where python.exe 2^>nul') do (
    echo %%i | findstr /v /i "WindowsApps" >nul
    if not errorlevel 1 (
        set "PYTHON_EXE=%%i"
        goto :found
    )
)

REM Not found - install
echo [!] Python is not installed.
echo.
echo Installing Python 3.12 via winget...
winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements --scope user
if errorlevel 1 (
    echo.
    echo [X] Auto-install failed. Please install Python 3.12 manually:
    echo     https://www.python.org/downloads/
    echo     Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)
echo.
echo Python installed. Re-running setup...
set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

:found
echo [OK] Python found at:
echo      %PYTHON_EXE%
"%PYTHON_EXE%" --version
echo.

REM Save Python path for RUN.bat
echo %PYTHON_EXE% > .python_path.txt

echo Upgrading pip...
"%PYTHON_EXE%" -m pip install --upgrade pip --quiet

echo.
echo Installing dependencies (google-genai, openpyxl, bs4, etc)...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [X] Dependency install failed. Check your internet connection.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   SETUP COMPLETE!
echo ============================================================
echo.
echo Next steps:
echo   1. Double-click RUN.bat to start the app
echo   2. Click "Settings" and paste your Gemini API key
echo   3. Get a free key at: https://aistudio.google.com/apikey
echo.
pause
