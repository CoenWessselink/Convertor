@echo off
setlocal EnableExtensions
set PYTHONUTF8=1
cd /d "%~dp0"

set "CWS_VERSION=0.10.19-beta-dev"
set "CWS_DIST=CWS_Convertor"
set "CWS_RESULTS=%CD%\validation\results\windows-runtime"
set "CWS_PORTABLE=%TEMP%\CWS_Convertor_Portable_Clean"
set "CWS_INSTALL_DIR=%TEMP%\CWS_Convertor_Installed"
for /f %%I in ('git rev-parse HEAD') do set "CWS_COMMIT=%%I"
if not defined CWS_COMMIT goto :error
set "CWS_COMMIT7=%CWS_COMMIT:~0,7%"
for /f %%I in ('git status --porcelain=v1') do goto :dirty_tree

echo [1/10] Python 3.12 buildomgeving controleren...
where py >nul 2>&1 || goto :no_python
if not exist ".venv-build\Scripts\python.exe" (
    py -3.12 -m venv .venv-build || goto :error
)

echo [2/10] Dependencies installeren...
".venv-build\Scripts\python.exe" -m pip install --upgrade pip || goto :error
".venv-build\Scripts\python.exe" -m pip install -r requirements-build.lock.txt || goto :error
".venv-build\Scripts\python.exe" -m pip check || goto :error

echo [3/10] Bronregressies, native selftest en GUI-smoke uitvoeren...
set "PYTHONPATH=%CD%"
if not exist "%CWS_RESULTS%" mkdir "%CWS_RESULTS%"
".venv-build\Scripts\python.exe" -m compileall -q . || goto :error
".venv-build\Scripts\python.exe" validation\run_all_smokes_v9.py --headless-windows --output "validation\results\phase3\source-smokes" || goto :error
".venv-build\Scripts\python.exe" tests\edit_workspace_ui_smoke.py || goto :error
".venv-build\Scripts\python.exe" cli.py --version || goto :error
".venv-build\Scripts\python.exe" CWS_Convertor_App.py --self-test --output "%CWS_RESULTS%\source-native-selftest.json" || goto :error
".venv-build\Scripts\python.exe" CWS_Convertor_App.py --gui-smoke --output "%CWS_RESULTS%\source-gui-smoke.json" || goto :error
".venv-build\Scripts\python.exe" validation\run_phase_b_progressive_loading.py --output "%CWS_RESULTS%\source-phase-b-progressive-loading.json" || goto :error

echo [4/10] Exacte fasegates en volledige 10-minutensoak uitvoeren...
".venv-build\Scripts\python.exe" tools\build_phase1_reproducible_evidence.py || goto :error
".venv-build\Scripts\python.exe" tools\run_phase1_unified_gates.py || goto :error
".venv-build\Scripts\python.exe" tools\run_phase2_unified_gates.py || goto :error
".venv-build\Scripts\python.exe" tools\run_phase3_gates.py --reuse-fresh-evidence || goto :error
".venv-build\Scripts\python.exe" tools\capture_bom_production_hub.py --project "validation\master_completion\hvpc_project\HVPC te Hengelo fasen totaal.cwscproj" --output "%CWS_RESULTS%\bom-production-hub" || goto :error

echo [5/10] Schone PyInstaller onedir-build maken...
if exist "build" rmdir /s /q "build"
if exist "dist\%CWS_DIST%" rmdir /s /q "dist\%CWS_DIST%"
if exist "dist_installer" rmdir /s /q "dist_installer"
".venv-build\Scripts\pyinstaller.exe" --noconfirm --clean CWS_Convertor.spec || goto :error
if not exist "dist\%CWS_DIST%\CWS_Convertor.exe" goto :error
if not exist "dist\%CWS_DIST%\CWS_Convertor_CLI.exe" goto :error
".venv-build\Scripts\python.exe" validation\inspect_windows_native_dependencies.py "dist\%CWS_DIST%" --output "%CWS_RESULTS%\dist-native-inventory.json" || goto :error

echo [6/10] Dist testen zonder Python op child-PATH...
".venv-build\Scripts\python.exe" tests\packaged_runtime_smoke.py --runtime-dir "dist\%CWS_DIST%" --label dist --result-dir "%CWS_RESULTS%" || goto :error

echo [7/10] Portable ZIP maken, schoon uitpakken en testen...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\%CWS_DIST%' -DestinationPath 'dist\CWS_Convertor_Final_%CWS_VERSION%_%CWS_COMMIT7%_Portable.zip' -Force" || goto :error
if exist "%CWS_PORTABLE%" rmdir /s /q "%CWS_PORTABLE%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive 'dist\CWS_Convertor_Final_%CWS_VERSION%_%CWS_COMMIT7%_Portable.zip' -DestinationPath '%CWS_PORTABLE%'" || goto :error
".venv-build\Scripts\python.exe" tests\packaged_runtime_smoke.py --runtime-dir "%CWS_PORTABLE%\%CWS_DIST%" --label portable --result-dir "%CWS_RESULTS%" || goto :error

echo [8/10] Installer bouwen...
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo Inno Setup 6 is niet aanwezig op deze buildcomputer.
    exit /b 2
)
"%ISCC%" "/DCommit7=%CWS_COMMIT7%" "installer\CWS_Convertor.iss" || goto :error

echo [9/10] Installeren, volledig testen en verwijderen...
if exist "%CWS_INSTALL_DIR%" rmdir /s /q "%CWS_INSTALL_DIR%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Start-Process -FilePath '%CD%\dist_installer\CWS_Convertor_Setup_%CWS_VERSION%_%CWS_COMMIT7%_x64.exe' -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/CURRENTUSER','/TASKS=fileassoc','/DIR=%CWS_INSTALL_DIR%') -Wait -PassThru -WindowStyle Hidden; exit $p.ExitCode" || goto :error
".venv-build\Scripts\python.exe" tests\packaged_runtime_smoke.py --runtime-dir "%CWS_INSTALL_DIR%" --label installed --result-dir "%CWS_RESULTS%" || goto :error
".venv-build\Scripts\python.exe" tests\windows_installer_association_smoke.py --runtime-dir "%CWS_INSTALL_DIR%" --output "%CWS_RESULTS%\installed-associations.json" || goto :error
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Start-Process -FilePath '%CWS_INSTALL_DIR%\unins000.exe' -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -Wait -PassThru -WindowStyle Hidden; exit $p.ExitCode" || goto :error
if exist "%CWS_INSTALL_DIR%\CWS_Convertor.exe" goto :error
if exist "%CWS_INSTALL_DIR%\CWS_Convertor_CLI.exe" goto :error
".venv-build\Scripts\python.exe" tests\windows_installer_association_smoke.py --expect-absent --output "%CWS_RESULTS%\uninstall-associations.json" || goto :error

echo [10/10] Codex-overdracht, SBOM, checksums en releasebestanden maken...
if exist "release" rmdir /s /q "release"
mkdir "release"
copy /y "dist\CWS_Convertor_Final_%CWS_VERSION%_%CWS_COMMIT7%_Portable.zip" "release\" >nul || goto :error
copy /y "dist_installer\CWS_Convertor_Setup_%CWS_VERSION%_%CWS_COMMIT7%_x64.exe" "release\" >nul || goto :error
copy /y "WINDOWS_RUNTIME_VALIDATION.md" "release\" >nul || goto :error
git archive --format=zip --output="release\CWS_Convertor_Source_%CWS_VERSION%_%CWS_COMMIT7%.zip" %CWS_COMMIT% || goto :error
git bundle create "release\CWS_Convertor_%CWS_VERSION%_%CWS_COMMIT7%.bundle" HEAD || goto :error
".venv-build\Scripts\python.exe" tools\generate_sbom.py "release\CWS_Convertor_SBOM_%CWS_VERSION%_%CWS_COMMIT7%.cdx.json" || goto :error
if not exist "release\BOM_EVIDENCE" mkdir "release\BOM_EVIDENCE"
copy /y "%CWS_RESULTS%\bom-production-hub\*" "release\BOM_EVIDENCE\" >nul || goto :error
if not exist "release\TEST_EVIDENCE" mkdir "release\TEST_EVIDENCE"
copy /y "validation\phases\PHASE_1_REPRODUCIBLE_EVIDENCE.json" "release\TEST_EVIDENCE\" >nul || goto :error
copy /y "validation\phases\PHASE_1_SOURCE_TEST_EVIDENCE.json" "release\TEST_EVIDENCE\" >nul || goto :error
copy /y "validation\phases\PHASE_2_SOURCE_TEST_EVIDENCE.json" "release\TEST_EVIDENCE\" >nul || goto :error
copy /y "validation\phases\PHASE_3_SOURCE_TEST_EVIDENCE.json" "release\TEST_EVIDENCE\" >nul || goto :error
copy /y "validation\phases\PHASE_3_SOAK_EVIDENCE.json" "release\TEST_EVIDENCE\" >nul || goto :error
".venv-build\Scripts\python.exe" tools\build_codex_release_manifest.py --release-dir release --runtime-results "%CWS_RESULTS%" || goto :error

echo.
echo Gereed:
echo   %CD%\release\CWS_Convertor_Setup_%CWS_VERSION%_%CWS_COMMIT7%_x64.exe
echo   %CD%\release\CWS_Convertor_Final_%CWS_VERSION%_%CWS_COMMIT7%_Portable.zip
echo   %CD%\release\CWS_Convertor_Source_%CWS_VERSION%_%CWS_COMMIT7%.zip
echo   %CD%\release\CWS_Convertor_%CWS_VERSION%_%CWS_COMMIT7%.bundle
echo   %CD%\release\CODEX_RELEASE_MANIFEST.json
echo   %CD%\release\SHA256SUMS.txt
exit /b 0

:dirty_tree
echo Releasebuild geweigerd: working tree is niet schoon.
exit /b 4

:no_python
echo Python Launcher ontbreekt op de buildcomputer. Dit is alleen een ontwikkelaars-/CI-buildscript.
exit /b 3

:error
echo.
echo De Windows-releasebuild is mislukt. Zie de foutmelding hierboven.
exit /b 1
