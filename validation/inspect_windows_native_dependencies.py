from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

import pefile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.product import APP_VERSION


CASADI_REQUIRED = {"libcasadi.dll", "libgcc_s_seh-1.dll", "libstdc++-6.dll", "libwinpthread-1.dll"}


def _imports(path: Path) -> list[str]:
    image = pefile.PE(str(path), fast_load=True)
    image.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
    return sorted(entry.dll.decode("ascii", errors="replace") for entry in getattr(image, "DIRECTORY_ENTRY_IMPORT", []))


def inspect(runtime_dir: Path) -> dict[str, object]:
    runtime_dir = runtime_dir.resolve()
    internal = runtime_dir / "_internal"
    native_files = sorted(path for path in internal.rglob("*") if path.suffix.lower() in {".pyd", ".dll"})
    filename_index: dict[str, list[str]] = {}
    for path in native_files:
        filename_index.setdefault(path.name.lower(), []).append(str(path.relative_to(runtime_dir)))
    casadi_dir = internal / "casadi"
    casadi_extension = internal / "_casadi.pyd"
    package_extension = casadi_dir / "_casadi.pyd"
    if not casadi_extension.is_file():
        raise AssertionError(f"Gebundelde _casadi.pyd ontbreekt: {casadi_extension}")
    if not package_extension.is_file():
        raise AssertionError(f"Gebundelde casadi._casadi ontbreekt: {package_extension}")
    missing = sorted(name for name in CASADI_REQUIRED if not (casadi_dir / name).is_file())
    if missing:
        raise AssertionError(f"Gebundelde CasADi-DLL's ontbreken: {missing}")
    extension_imports = _imports(casadi_extension)
    unresolved_casadi = sorted(
        name
        for name in extension_imports
        if name.lower() not in filename_index
        and not (Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / name).is_file()
    )
    if unresolved_casadi:
        raise AssertionError(f"Niet-opgeloste _casadi.pyd dependencies: {unresolved_casadi}")

    package_counts = Counter(
        path.relative_to(internal).parts[0] if len(path.relative_to(internal).parts) > 1 else "_internal"
        for path in native_files
    )
    return {
        "application_version": APP_VERSION,
        "status": "passed",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_directory": str(runtime_dir),
        "native_file_count": len(native_files),
        "pyd_count": sum(path.suffix.lower() == ".pyd" for path in native_files),
        "dll_count": sum(path.suffix.lower() == ".dll" for path in native_files),
        "native_files_by_top_level": dict(sorted(package_counts.items())),
        "casadi": {
            "extension": str(casadi_extension.relative_to(runtime_dir)),
            "package_extension": str(package_extension.relative_to(runtime_dir)),
            "extension_imports": extension_imports,
            "required_dll_locations": {
                name: str((casadi_dir / name).relative_to(runtime_dir)) for name in sorted(CASADI_REQUIRED)
            },
            "packaged_dll_count": len(list(casadi_dir.glob("*.dll"))),
            "unresolved_dependencies": unresolved_casadi,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspecteer native Windows-bestanden in een CWS onedir-build")
    parser.add_argument("runtime_dir", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args(argv)
    result = inspect(arguments.runtime_dir)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
