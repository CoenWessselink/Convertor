from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.product import APP_NAME, APP_VERSION, APP_VERSION_NUMERIC


def main() -> int:
    installer = (ROOT / "installer" / "CWS_Convertor.iss").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "build-windows-exe.yml").read_text(encoding="utf-8")
    batch = (ROOT / "build_windows_exe.bat").read_text(encoding="utf-8")
    spec = (ROOT / "CWS_Convertor.spec").read_text(encoding="utf-8")
    runtime_lock = (ROOT / "requirements-runtime.lock.txt").read_text(encoding="utf-8")
    runtime_hook = (ROOT / "pyinstaller_hooks" / "pyi_rth_casadi_dll_path.py").read_text(encoding="utf-8")
    gui_entry = (ROOT / "app.py").read_text(encoding="utf-8")
    cli_entry = (ROOT / "cli.py").read_text(encoding="utf-8")
    packaged_smoke = (ROOT / "tests" / "packaged_runtime_smoke.py").read_text(encoding="utf-8")

    assert f'#define MyAppVersion "{APP_VERSION}"' in installer
    assert f'#define MyAppName "{APP_NAME}"' in installer
    assert '#define MyAppExeName "CWS_Convertor.exe"' in installer
    assert f'#define MyAppNumericVersion "{APP_VERSION_NUMERIC}"' in installer
    assert "VersionInfoVersion={#MyAppNumericVersion}" in installer
    assert "VersionInfoProductVersion={#MyAppNumericVersion}" in installer
    assert "VersionInfoProductVersion={#MyAppVersion}" not in installer
    assert "PrivilegesRequiredOverridesAllowed=commandline" in installer
    assert "Root: HKCR" not in installer
    assert installer.count('Root: HKA; Subkey: "Software\\Classes\\') == 20
    assert re.fullmatch(r"\d+\.\d+\.\d+\.\d+", APP_VERSION_NUMERIC)

    assert f"CWS_VERSION: {APP_VERSION}" in workflow
    assert "name: CWS_Convertor_${{ env.CWS_VERSION }}_Windows_x64" in workflow
    assert "actions/checkout@v6" in workflow
    assert "actions/setup-python@v6" in workflow
    assert 'Get-ChildItem tests -Filter "*_smoke.py"' in workflow
    assert "Smoke script $($_.Name) failed with exit code" in workflow
    assert '"casadi"' in spec
    assert '"scipy"' in spec
    assert '"ezdxf"' in spec
    assert "scipy._external.array_api_compat" in spec
    assert "pyi_rth_casadi_dll_path.py" in spec
    assert "hook-casadi.py" in workflow or "pyinstaller_hooks/**" in workflow
    assert "casadi==3.7.2" in runtime_lock
    assert "ezdxf==1.4.4" in runtime_lock
    assert "vtk==9.6.2" in runtime_lock
    assert "vtkmodules.vtkRenderingOpenGL2" in spec
    assert "os.add_dll_directory" in runtime_hook
    assert "libcasadi.dll" in runtime_hook
    assert "multiprocessing.freeze_support()" in gui_entry
    assert "multiprocessing.freeze_support()" in cli_entry
    assert "project-inspect-source-geometry" in packaged_smoke
    assert "triangulated_mesh" in packaged_smoke
    assert '"vtk_viewer"' in packaged_smoke
    assert workflow.count("packaged_runtime_smoke.py") == 3
    assert "--label dist" in workflow
    assert "--label portable" in workflow
    assert "--label installed" in workflow
    assert "inspect_windows_native_dependencies.py" in workflow
    assert "WINDOWS_RELEASE_MANIFEST.json" in workflow
    assert "GITHUB_STEP_SUMMARY" in workflow
    assert "app.py --self-test" in workflow
    assert "app.py --gui-smoke" in workflow
    assert "validation/run_core_phase0_baseline.py --skip-tests" in workflow
    assert "ci-core-phase0-baseline.json" in workflow
    assert "Start-Process -FilePath $installer.Path" in workflow
    assert workflow.count("/CURRENTUSER") == 1
    assert workflow.count("/TASKS=fileassoc") == 1
    assert "windows_installer_association_smoke.py" in workflow
    assert "Start-Process -FilePath $uninstaller" in workflow
    assert workflow.count("-Wait -PassThru -WindowStyle Hidden") == 2
    assert "$installProcess.ExitCode" in workflow
    assert "$uninstallProcess.ExitCode" in workflow
    assert f'set "CWS_VERSION={APP_VERSION}"' in batch
    assert "for %%F in (tests\\*_smoke.py)" in batch
    assert batch.count("packaged_runtime_smoke.py") == 3
    assert batch.count("/CURRENTUSER") == 1
    assert batch.count("/TASKS=fileassoc") == 1
    assert "windows_installer_association_smoke.py" in batch
    lazy_import = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import cws_convertor.project; "
                "assert 'cadquery' not in sys.modules; "
                "assert 'cws_convertor.project.canonical_rebuild' not in sys.modules"
            ),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert lazy_import.returncode == 0, lazy_import.stderr
    print("windows_release_config_smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
