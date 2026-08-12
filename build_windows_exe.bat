@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Voer eerst start_converter.bat uit om de omgeving te installeren.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install --upgrade pyinstaller
if errorlevel 1 goto :error

if exist "build" rmdir /s /q "build"
if exist "dist\NC1_STEP_Converter" rmdir /s /q "dist\NC1_STEP_Converter"

".venv\Scripts\pyinstaller.exe" --noconfirm --clean --windowed --onedir ^
  --name NC1_STEP_Converter ^
  --collect-all cadquery ^
  --collect-all OCP ^
  --collect-all matplotlib ^
  --collect-all ifcopenshell ^
  --collect-all xlsxwriter ^
  --hidden-import matplotlib.backends.backend_tkagg ^
  --hidden-import ifcopenshell.api ^
  --hidden-import ifcopenshell.geom ^
  --add-data "profiles.json;." ^
  --add-data "materials.json;." ^
  app.py
if errorlevel 1 goto :error

copy /y README.md "dist\NC1_STEP_Converter\README.md" >nul
copy /y VERSIE_EN_TESTSTATUS.txt "dist\NC1_STEP_Converter\VERSIE_EN_TESTSTATUS.txt" >nul
if exist CHANGELOG.md copy /y CHANGELOG.md "dist\NC1_STEP_Converter\CHANGELOG.md" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\NC1_STEP_Converter' -DestinationPath 'dist\NC1_STEP_Converter_Windows_x64.zip' -Force"

echo.
echo Windows-EXE gereed:
echo %CD%\dist\NC1_STEP_Converter\NC1_STEP_Converter.exe
echo Release ZIP:
echo %CD%\dist\NC1_STEP_Converter_Windows_x64.zip
echo.
echo De complete map NC1_STEP_Converter moet bij de EXE blijven.
pause
exit /b 0

:error
echo.
echo De Windows-build is mislukt. Zie de foutmelding hierboven.
pause
exit /b 1
