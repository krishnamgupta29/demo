@echo off
setlocal enabledelayedexpansion
title DENTRACE - Clinical Decision Support Engine

echo =======================================================================
echo   DENTRACE: Clinical Decision Support Engine Launcher
echo   Regulatory Notice: Draft for dentist review. Not a diagnosis.
echo =======================================================================
echo.

cd /d "%~dp0"

:: 1. Locate Python 3.11 Runtime
set "PYTHON_CMD="

:: Priority 1: Local extracted venv if present
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%~dp0.venv\Scripts\python.exe"
    goto :FOUND_PYTHON
)

:: Priority 2: System Python 3.11 launcher
py -3.11 -c "import sys; sys.exit(0)" >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py -3.11"
    goto :FOUND_PYTHON
)

:: Priority 3: Default python executable if Python 3.11
python -c "import sys; sys.exit(0 if sys.version_info.major==3 and sys.version_info.minor==11 else 1)" >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto :FOUND_PYTHON
)

:: Priority 4: Developer workstation fallback
if exist "D:\mini\.venv\Scripts\python.exe" (
    set "PYTHON_CMD=D:\mini\.venv\Scripts\python.exe"
    goto :FOUND_PYTHON
)
if exist "C:\mini\.venv\Scripts\python.exe" (
    set "PYTHON_CMD=C:\mini\.venv\Scripts\python.exe"
    goto :FOUND_PYTHON
)

echo [ERROR] Python 3.11 was not detected on this machine.
echo [HINT] Please install Python 3.11.9 from https://www.python.org/downloads/
echo Press any key to exit...
pause >nul
exit /b 1

:FOUND_PYTHON
echo [*] Using Python interpreter: !PYTHON_CMD!
echo [*] Starting DENTRACE Desktop Launcher...
echo.

!PYTHON_CMD! scripts\launcher\launcher.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] DENTRACE encountered a fatal startup error.
    pause
)
