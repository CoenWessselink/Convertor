from __future__ import annotations

from pathlib import Path
import re
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
    assert f'set "CWS_VERSION={APP_VERSION}"' in batch
    assert "for %%F in (tests\\*_smoke.py)" in batch
    print("windows_release_config_smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
