@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
    echo Voer eerst start_converter.bat uit om de SteelConverter-ontwikkelomgeving te installeren.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" cli.py %*
