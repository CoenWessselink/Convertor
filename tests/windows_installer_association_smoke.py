from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def _read_default(winreg: object, subkey: str) -> str:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey) as key:
        value, _value_type = winreg.QueryValueEx(key, "")
    return str(value)


def _assert_open_command(label: str, found: str, executable: Path) -> None:
    match = re.fullmatch(r'"(.+)" "%1"', found)
    if match is None:
        raise AssertionError(f"Open command {label} has invalid syntax: {found!r}")
    command_executable = Path(match.group(1))
    if not command_executable.is_file() or not command_executable.samefile(executable):
        raise AssertionError(
            f"Open command {label} targets {command_executable}, expected {executable}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate file associations created by a per-user Windows install."
    )
    parser.add_argument("--runtime-dir", type=Path)
    parser.add_argument("--expect-absent", action="store_true")
    args = parser.parse_args()

    if args.runtime_dir is None:
        installer = (ROOT / "installer" / "CWS_Convertor.iss").read_text(
            encoding="utf-8"
        )
        if "Root: HKCR" in installer:
            raise AssertionError("Installer associations must not target HKCR directly")
        if installer.count('Root: HKA; Subkey: "Software\\Classes\\') != 20:
            raise AssertionError("Expected 20 installation-mode-aware association entries")
        print("windows_installer_association_smoke: source configuration OK")
        return 0

    if sys.platform != "win32":
        raise SystemExit("windows_installer_association_smoke requires Windows")

    import winreg

    if args.expect_absent:
        keys = [
            r"Software\Classes\.cwscproj", r"Software\Classes\.nc", r"Software\Classes\.nc1",
            r"Software\Classes\.step", r"Software\Classes\.stp", r"Software\Classes\.ifc",
            r"Software\Classes\CWSConvertor.Project", r"Software\Classes\CWSConvertor.NC1",
            r"Software\Classes\CWSConvertor.STEP", r"Software\Classes\CWSConvertor.IFC",
            r"Software\Classes\SystemFileAssociations\.pdf\shell\CWSConvertor",
        ]
        remaining = []
        for subkey in keys:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey):
                    remaining.append(subkey)
            except FileNotFoundError:
                pass
        if remaining:
            raise AssertionError(f"Association keys remained after uninstall: {remaining}")
        print("windows_installer_association_smoke: uninstall cleanup OK")
        return 0

    runtime_dir = args.runtime_dir.resolve()
    executable = runtime_dir / "CWS_Convertor.exe"
    if not executable.is_file():
        raise AssertionError(f"Installed GUI executable is missing: {executable}")

    classes = r"Software\Classes"
    expected_extensions = {
        ".cwscproj": "CWSConvertor.Project",
        ".nc": "CWSConvertor.NC1",
        ".nc1": "CWSConvertor.NC1",
        ".step": "CWSConvertor.STEP",
        ".stp": "CWSConvertor.STEP",
        ".ifc": "CWSConvertor.IFC",
    }
    for extension, class_name in expected_extensions.items():
        found = _read_default(winreg, f"{classes}\\{extension}")
        if found != class_name:
            raise AssertionError(
                f"Association {extension} expected {class_name!r}, found {found!r}"
            )

    for class_name in sorted(set(expected_extensions.values())):
        found = _read_default(
            winreg, f"{classes}\\{class_name}\\shell\\open\\command"
        )
        _assert_open_command(class_name, found, executable)

    pdf_command = _read_default(
        winreg,
        rf"{classes}\SystemFileAssociations\.pdf\shell\CWSConvertor\command",
    )
    _assert_open_command("PDF context menu", pdf_command, executable)

    print("windows_installer_association_smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
