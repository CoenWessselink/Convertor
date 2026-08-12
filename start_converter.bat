@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1

if not exist ".venv\Scripts\python.exe" (
    if exist ".venv" rmdir /s /q ".venv"
    echo Eerste installatie: lokale Python-omgeving wordt aangemaakt.
    py -3.12 -m venv .venv 2>nul
    if errorlevel 1 (
        python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)" 2>nul
        if not errorlevel 1 python -m venv .venv
    )
    if not exist ".venv\Scripts\python.exe" (
        echo.
        echo Geen geschikte Python-versie gevonden.
        echo Installeer 64-bits Python 3.12 en voer dit bestand opnieuw uit.
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -c "import struct; raise SystemExit(0 if struct.calcsize('P') * 8 == 64 else 1)"
    if errorlevel 1 (
        echo Alleen 64-bits Python wordt ondersteund.
        rmdir /s /q ".venv"
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 goto :install_error
)

".venv\Scripts\python.exe" -c "import cadquery, matplotlib, xlsxwriter, ifcopenshell, fitz, pypdf, reportlab" 2>nul
if errorlevel 1 (
    echo Benodigde pakketten worden geinstalleerd of bijgewerkt.
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :install_error
)

".venv\Scripts\python.exe" app.py
set APP_EXIT=%errorlevel%
if not "%APP_EXIT%"=="0" pause
exit /b %APP_EXIT%

:install_error
echo.
echo Installatie van de benodigde pakketten is mislukt. Controleer internetverbinding en foutmelding hierboven.
echo Verwijder zo nodig de map .venv en voer start_converter.bat opnieuw uit.
pause
exit /b 1
