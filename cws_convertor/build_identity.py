"""Commit-bound identity embedded by both existing Windows PyInstaller specs."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
from cws_convertor.product import APP_VERSION

FILENAME = "cws-build-identity.json"
SCHEMA = "cws-build-identity-v1"


def _git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=root,
                                   text=True, encoding="utf-8").strip()


def checkout_identity(root: Path) -> dict[str, Any]:
    return {
        "source_commit": _git(root, "rev-parse", "HEAD"),
        "source_tree": _git(root, "rev-parse", "HEAD^{tree}"),
        "tracked_dirty": bool(_git(root, "status", "--porcelain=v1", "--untracked-files=no")),
    }


def write_build_identity(root: Path) -> Path:
    """Refuse dirty or untracked application code before either EXE is built."""
    root = Path(root).resolve()
    identity = checkout_identity(root)
    if identity["tracked_dirty"]:
        raise RuntimeError("Build geweigerd: vastgelegde broncode bevat lokale wijzigingen")
    untracked = _git(root, "ls-files", "--others", "--exclude-standard").splitlines()
    unsafe = [name for name in untracked if Path(name).suffix in {".py", ".pyw", ".spec"}
              and (len(Path(name).parts) == 1
                   or Path(name).parts[0] in {"cws_convertor", "cws_viewer"})]
    if unsafe:
        raise RuntimeError(f"Build geweigerd: niet-vastgelegde programmacode: {unsafe}")
    payload = {
        "schema": SCHEMA, "application_version": APP_VERSION,
        **identity, "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version, "build_platform": sys.platform,
    }
    target = root / "build" / FILENAME
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def read_build_identity() -> dict[str, Any]:
    if not getattr(sys, "frozen", False):
        root = Path(__file__).resolve().parents[1]
        return {"schema": SCHEMA, "application_version": APP_VERSION,
                "frozen": False, **checkout_identity(root)}
    target = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / FILENAME
    payload = json.loads(target.read_text(encoding="utf-8"))
    if payload.get("schema") != SCHEMA or payload.get("application_version") != APP_VERSION:
        raise RuntimeError("Ongeldige of afwijkende ingebouwde bronidentiteit")
    for field in ("source_commit", "source_tree"):
        if not re.fullmatch(r"[0-9a-f]{40}", str(payload.get(field, ""))):
            raise RuntimeError(f"Ingebouwde bronidentiteit mist {field}")
    if payload.get("tracked_dirty") is not False:
        raise RuntimeError("EXE is niet uit een schone vastgelegde bronversie gebouwd")
    return {**payload, "frozen": True}
