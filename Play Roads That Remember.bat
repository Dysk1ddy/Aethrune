@echo off
setlocal

REM Always run from this file's folder so the user never needs to cd first.
cd /d "%~dp0"

set "PYTHON_CMD="

where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py"

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo Python was not found on this computer.
    echo.
    echo Install Python from https://www.python.org/downloads/
    echo and make sure "Add python.exe to PATH" is enabled during install.
    echo.
    pause
    exit /b 1
)

"%PYTHON_CMD%" main.py
set "GAME_EXIT_CODE=%ERRORLEVEL%"

if not "%GAME_EXIT_CODE%"=="0" (
    echo.
    echo The game closed with an error.
    echo If this is your first time running it, install the requirements with:
    echo     pip install pygame rich
    echo.
    pause
)

exit /b %GAME_EXIT_CODE%
