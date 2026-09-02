from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def _write_report(path: Path | None, *, mode: str, details: dict[str, object]) -> None:
    if path is None:
        return
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "cws-windows-association-evidence-1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "mode": mode,
        **details,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.expect_absent:
        if sys.platform != "win32":
            raise SystemExit("windows_installer_association_smoke requires Windows")

        import winreg

        extension_values = {
            r"Software\Classes\.cwscproj": "CWSConvertor.Project",
            r"Software\Classes\.nc": "CWSConvertor.NC1",
            r"Software\Classes\.nc1": "CWSConvertor.NC1",
            r"Software\Classes\.step": "CWSConvertor.STEP",
            r"Software\Classes\.stp": "CWSConvertor.STEP",
            r"Software\Classes\.ifc": "CWSConvertor.IFC",
        }
        owned_keys = [
            r"Software\Classes\CWSConvertor.Project", r"Software\Classes\CWSConvertor.NC1",
            r"Software\Classes\CWSConvertor.STEP", r"Software\Classes\CWSConvertor.IFC",
            r"Software\Classes\SystemFileAssociations\.pdf\shell\CWSConvertor",
        ]
        remaining_values = []
        for subkey, cws_value in extension_values.items():
            try:
                found = _read_default(winreg, subkey)
            except FileNotFoundError:
                continue
            if found == cws_value:
                remaining_values.append({"key": subkey, "value": found})
        remaining_keys = []
        for subkey in owned_keys:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey):
                    remaining_keys.append(subkey)
            except FileNotFoundError:
                pass
        if remaining_values or remaining_keys:
            raise AssertionError(
                "CWS associations remained after uninstall: "
                f"values={remaining_values}, keys={remaining_keys}"
            )
        _write_report(
            args.output,
            mode="uninstall_cleanup",
            details={
                "checked_extension_values": len(extension_values),
                "checked_owned_keys": len(owned_keys),
                "remaining_cws_values": [],
                "remaining_owned_keys": [],
            },
        )
        print("windows_installer_association_smoke: uninstall cleanup OK")
        return 0

    if args.runtime_dir is None:
        installer = (ROOT / "installer" / "CWS_Convertor.iss").read_text(
            encoding="utf-8"
        )
        if "Root: HKCR" in installer:
            raise AssertionError("Installer associations must not target HKCR directly")
        if installer.count('Root: HKA; Subkey: "Software\\Classes\\') != 20:
            raise AssertionError("Expected 20 installation-mode-aware association entries")
        _write_report(
            args.output,
            mode="source_configuration",
            details={"association_entries": 20, "registry_root": "HKA"},
        )
        print("windows_installer_association_smoke: source configuration OK")
        return 0

    if sys.platform != "win32":
        raise SystemExit("windows_installer_association_smoke requires Windows")

    import winreg

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

    _write_report(
        args.output,
        mode="installed",
        details={
            "runtime_dir": str(runtime_dir),
            "extensions": sorted(expected_extensions),
            "class_count": len(set(expected_extensions.values())),
            "pdf_context_menu": True,
        },
    )

    print("windows_installer_association_smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
