from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.product import APP_VERSION, APP_VERSION_NUMERIC


def main() -> int:
    installer = (ROOT / "installer" / "CWS_Convertor.iss").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "build-windows-exe.yml").read_text(encoding="utf-8")
    batch = (ROOT / "build_windows_exe.bat").read_text(encoding="utf-8")

    assert f'#define MyAppVersion "{APP_VERSION}"' in installer
    assert f'#define MyAppNumericVersion "{APP_VERSION_NUMERIC}"' in installer
    assert "VersionInfoVersion={#MyAppNumericVersion}" in installer
    assert "VersionInfoProductVersion={#MyAppNumericVersion}" in installer
    assert "VersionInfoProductVersion={#MyAppVersion}" not in installer
    assert re.fullmatch(r"\d+\.\d+\.\d+\.\d+", APP_VERSION_NUMERIC)

    assert f"CWS_VERSION: {APP_VERSION}" in workflow
    assert "actions/checkout@v6" in workflow
    assert "actions/setup-python@v6" in workflow
    assert 'Get-ChildItem tests -Filter "*_smoke.py"' in workflow
    assert "Start-Process -FilePath $installer.Path" in workflow
    assert "Start-Process -FilePath $uninstaller" in workflow
    assert workflow.count("-Wait -PassThru -WindowStyle Hidden") == 2
    assert "$installProcess.ExitCode" in workflow
    assert "$uninstallProcess.ExitCode" in workflow
    assert f'set "CWS_VERSION={APP_VERSION}"' in batch
    assert "for %%F in (tests\\*_smoke.py)" in batch
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
