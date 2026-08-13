@echo off
setlocal EnableExtensions
set PYTHONUTF8=1
cd /d "%~dp0"

set "CWS_VERSION=0.8.0-alpha-dev"
set "CWS_DIST=CWS_Convertor"

echo [1/7] Python 3.12 buildomgeving controleren...
where py >nul 2>&1 || goto :no_python
if not exist ".venv-build\Scripts\python.exe" (
    py -3.12 -m venv .venv-build || goto :error
)

echo [2/7] Dependencies installeren...
".venv-build\Scripts\python.exe" -m pip install --upgrade pip || goto :error
".venv-build\Scripts\python.exe" -m pip install -r requirements-build.lock.txt || goto :error
".venv-build\Scripts\python.exe" -m pip check || goto :error

echo [3/7] Regressie- en projecttests uitvoeren...
set "PYTHONPATH=%CD%"
".venv-build\Scripts\python.exe" -m compileall -q . || goto :error
for %%F in (tests\*_smoke.py) do (
    echo   %%~nxF
    ".venv-build\Scripts\python.exe" "%%F" || goto :error
)
".venv-build\Scripts\python.exe" cli.py --version || goto :error
".venv-build\Scripts\python.exe" cli.py project-new --help >nul || goto :error
".venv-build\Scripts\python.exe" cli.py project-import-baseline --help >nul || goto :error
".venv-build\Scripts\python.exe" cli.py project-import --help >nul || goto :error
".venv-build\Scripts\python.exe" cli.py project-tree --help >nul || goto :error
".venv-build\Scripts\python.exe" cli.py project-list-parts --help >nul || goto :error
".venv-build\Scripts\python.exe" cli.py project-migrate --help >nul || goto :error
".venv-build\Scripts\python.exe" -c "from app import ConverterApp; app=ConverterApp(); app.update_idletasks(); app.destroy(); print('GUI smoke OK')" || goto :error

echo [4/7] Oude build verwijderen...
if exist "build" rmdir /s /q "build"
if exist "dist\%CWS_DIST%" rmdir /s /q "dist\%CWS_DIST%"
if exist "dist_installer" rmdir /s /q "dist_installer"

echo [5/7] Standalone onedir-programma bouwen...
".venv-build\Scripts\pyinstaller.exe" --noconfirm --clean CWS_Convertor.spec || goto :error
if not exist "dist\%CWS_DIST%\CWS_Convertor.exe" goto :error
if not exist "dist\%CWS_DIST%\CWS_Convertor_CLI.exe" goto :error
"dist\%CWS_DIST%\CWS_Convertor_CLI.exe" --version || goto :error

echo [6/7] Portable ZIP maken...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\%CWS_DIST%' -DestinationPath 'dist\CWS_Convertor_Portable_%CWS_VERSION%_x64.zip' -Force" || goto :error

echo [7/7] Installer bouwen...
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo Inno Setup 6 is niet aanwezig op deze buildcomputer.
    echo De portable ZIP is wel gemaakt; installeer Inno Setup 6 en voer dit bestand opnieuw uit.
    exit /b 2
)
"%ISCC%" "installer\CWS_Convertor.iss" || goto :error

powershell -NoProfile -ExecutionPolicy Bypass -Command "$files=@('dist\CWS_Convertor_Portable_%CWS_VERSION%_x64.zip','dist_installer\CWS_Convertor_Setup_%CWS_VERSION%_x64.exe'); $lines=foreach($f in $files){$h=(Get-FileHash -Algorithm SHA256 $f).Hash.ToLowerInvariant(); \"$h  $([IO.Path]::GetFileName($f))\"}; $lines | Set-Content -Encoding ascii 'SHA256SUMS_WINDOWS.txt'; Get-Content 'SHA256SUMS_WINDOWS.txt'" || goto :error

echo.
echo Gereed:
echo   %CD%\dist_installer\CWS_Convertor_Setup_%CWS_VERSION%_x64.exe
echo   %CD%\dist\CWS_Convertor_Portable_%CWS_VERSION%_x64.zip
echo   %CD%\SHA256SUMS_WINDOWS.txt
exit /b 0

:no_python
echo Python Launcher ontbreekt op de buildcomputer. Dit is alleen een ontwikkelaars-/CI-buildscript.
exit /b 3

:error
echo.
echo De Windows-releasebuild is mislukt. Zie de foutmelding hierboven.
exit /b 1
