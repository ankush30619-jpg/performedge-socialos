@echo off
title Expert Social Media Planner
cd /d "%~dp0"

REM Read saved Python path from setup
set "PYTHON_EXE="
if exist .python_path.txt (
    set /p PYTHON_EXE=<.python_path.txt
)

REM Validate it still exists
if not exist "%PYTHON_EXE%" set "PYTHON_EXE="

REM If missing, search common locations
if "%PYTHON_EXE%"=="" (
    for %%P in (
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        "C:\Program Files\Python312\python.exe"
    ) do (
        if exist %%P set "PYTHON_EXE=%%~P"
    )
)

if "%PYTHON_EXE%"=="" (
    echo Python not found. Please run SETUP.bat first.
    pause
    exit /b 1
)

REM Find pythonw.exe alongside python.exe for no-console launch
set "PYTHONW_EXE=%PYTHON_EXE:python.exe=pythonw.exe%"
if not exist "%PYTHONW_EXE%" set "PYTHONW_EXE=%PYTHON_EXE%"

start "" "%PYTHONW_EXE%" app.py
exit
