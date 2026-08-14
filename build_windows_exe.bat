@echo off
setlocal EnableExtensions
set PYTHONUTF8=1
cd /d "%~dp0"

set "CWS_VERSION=0.8.3-beta-dev"
set "CWS_DIST=CWS_Convertor"
set "CWS_RESULTS=%CD%\validation\results\windows-runtime"
set "CWS_PORTABLE=%TEMP%\CWS_Convertor_Portable_Clean"
set "CWS_INSTALL_DIR=%TEMP%\CWS_Convertor_Installed"

echo [1/9] Python 3.12 buildomgeving controleren...
where py >nul 2>&1 || goto :no_python
if not exist ".venv-build\Scripts\python.exe" (
    py -3.12 -m venv .venv-build || goto :error
)

echo [2/9] Dependencies installeren...
".venv-build\Scripts\python.exe" -m pip install --upgrade pip || goto :error
".venv-build\Scripts\python.exe" -m pip install -r requirements-build.lock.txt || goto :error
".venv-build\Scripts\python.exe" -m pip check || goto :error

echo [3/9] Bronregressies, native selftest en GUI-smoke uitvoeren...
set "PYTHONPATH=%CD%"
if not exist "%CWS_RESULTS%" mkdir "%CWS_RESULTS%"
".venv-build\Scripts\python.exe" -m compileall -q . || goto :error
for %%F in (tests\*_smoke.py) do (
    echo   %%~nxF
    ".venv-build\Scripts\python.exe" "%%F" || goto :error
)
".venv-build\Scripts\python.exe" cli.py --version || goto :error
".venv-build\Scripts\python.exe" app.py --self-test --output "%CWS_RESULTS%\source-native-selftest.json" || goto :error
".venv-build\Scripts\python.exe" app.py --gui-smoke --output "%CWS_RESULTS%\source-gui-smoke.json" || goto :error
".venv-build\Scripts\python.exe" validation\run_phase_b_progressive_loading.py --output "%CWS_RESULTS%\source-phase-b-progressive-loading.json" || goto :error

echo [4/9] Schone PyInstaller onedir-build maken...
if exist "build" rmdir /s /q "build"
if exist "dist\%CWS_DIST%" rmdir /s /q "dist\%CWS_DIST%"
if exist "dist_installer" rmdir /s /q "dist_installer"
".venv-build\Scripts\pyinstaller.exe" --noconfirm --clean CWS_Convertor.spec || goto :error
if not exist "dist\%CWS_DIST%\CWS_Convertor.exe" goto :error
if not exist "dist\%CWS_DIST%\CWS_Convertor_CLI.exe" goto :error
".venv-build\Scripts\python.exe" validation\inspect_windows_native_dependencies.py "dist\%CWS_DIST%" --output "%CWS_RESULTS%\dist-native-inventory.json" || goto :error

echo [5/9] Dist testen zonder Python op child-PATH...
".venv-build\Scripts\python.exe" tests\packaged_runtime_smoke.py --runtime-dir "dist\%CWS_DIST%" --label dist --result-dir "%CWS_RESULTS%" || goto :error

echo [6/9] Portable ZIP maken, schoon uitpakken en testen...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\%CWS_DIST%' -DestinationPath 'dist\CWS_Convertor_Portable_%CWS_VERSION%_x64.zip' -Force" || goto :error
if exist "%CWS_PORTABLE%" rmdir /s /q "%CWS_PORTABLE%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive 'dist\CWS_Convertor_Portable_%CWS_VERSION%_x64.zip' -DestinationPath '%CWS_PORTABLE%'" || goto :error
".venv-build\Scripts\python.exe" tests\packaged_runtime_smoke.py --runtime-dir "%CWS_PORTABLE%\%CWS_DIST%" --label portable --result-dir "%CWS_RESULTS%" || goto :error

echo [7/9] Installer bouwen...
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo Inno Setup 6 is niet aanwezig op deze buildcomputer.
    exit /b 2
)
"%ISCC%" "installer\CWS_Convertor.iss" || goto :error

echo [8/9] Installeren, volledig testen en verwijderen...
if exist "%CWS_INSTALL_DIR%" rmdir /s /q "%CWS_INSTALL_DIR%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Start-Process -FilePath '%CD%\dist_installer\CWS_Convertor_Setup_%CWS_VERSION%_x64.exe' -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/CURRENTUSER','/TASKS=fileassoc','/DIR=%CWS_INSTALL_DIR%') -Wait -PassThru -WindowStyle Hidden; exit $p.ExitCode" || goto :error
".venv-build\Scripts\python.exe" tests\packaged_runtime_smoke.py --runtime-dir "%CWS_INSTALL_DIR%" --label installed --result-dir "%CWS_RESULTS%" || goto :error
".venv-build\Scripts\python.exe" tests\windows_installer_association_smoke.py --runtime-dir "%CWS_INSTALL_DIR%" || goto :error
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Start-Process -FilePath '%CWS_INSTALL_DIR%\unins000.exe' -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -Wait -PassThru -WindowStyle Hidden; exit $p.ExitCode" || goto :error
if exist "%CWS_INSTALL_DIR%\CWS_Convertor.exe" goto :error
if exist "%CWS_INSTALL_DIR%\CWS_Convertor_CLI.exe" goto :error

echo [9/9] Checksums en releasebestanden maken...
if not exist "release" mkdir "release"
copy /y "dist\CWS_Convertor_Portable_%CWS_VERSION%_x64.zip" "release\" >nul || goto :error
copy /y "dist_installer\CWS_Convertor_Setup_%CWS_VERSION%_x64.exe" "release\" >nul || goto :error
copy /y "WINDOWS_RUNTIME_VALIDATION.md" "release\" >nul || goto :error
powershell -NoProfile -ExecutionPolicy Bypass -Command "$files=@('release\CWS_Convertor_Portable_%CWS_VERSION%_x64.zip','release\CWS_Convertor_Setup_%CWS_VERSION%_x64.exe'); $lines=foreach($f in $files){$h=(Get-FileHash -Algorithm SHA256 $f).Hash.ToLowerInvariant(); \"$h  $([IO.Path]::GetFileName($f))\"}; $lines | Set-Content -Encoding ascii 'release\SHA256SUMS.txt'; Get-Content 'release\SHA256SUMS.txt'" || goto :error

echo.
echo Gereed:
echo   %CD%\release\CWS_Convertor_Setup_%CWS_VERSION%_x64.exe
echo   %CD%\release\CWS_Convertor_Portable_%CWS_VERSION%_x64.zip
echo   %CD%\release\SHA256SUMS.txt
exit /b 0

:no_python
echo Python Launcher ontbreekt op de buildcomputer. Dit is alleen een ontwikkelaars-/CI-buildscript.
exit /b 3

:error
echo.
echo De Windows-releasebuild is mislukt. Zie de foutmelding hierboven.
exit /b 1
