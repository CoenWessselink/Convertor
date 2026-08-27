from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import import_module
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.product import APP_NAME, APP_VERSION, PROJECT_SCHEMA_VERSION


def _git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else f"unavailable: {completed.stderr.strip()}"


def _dependency(name: str) -> dict[str, Any]:
    try:
        module = import_module(name)
        version = getattr(module, "__version__", None) or getattr(module, "VERSION", None) or "imported"
        if name == "PySide6":
            from PySide6.QtCore import qVersion
            version = qVersion()
        if name == "vtk":
            version = module.vtkVersion.GetVTKVersion()
        return {"status": "pass", "version": str(version)}
    except Exception as exc:
        return {"status": "fail", "error": f"{type(exc).__name__}: {exc}"}


def _fixture_hashes() -> dict[str, str]:
    candidates = (
        ROOT / "cws_viewer/fixtures/data/lo4_source_mesh_manifest.json",
        ROOT / "cws_viewer/fixtures/data/lo4_source_mesh.npz",
        ROOT / "CWS_CONVERTOR_COMPLETE_HANDOVER_0.10.3_V2/05_SAMPLE_FILES/Pr193.nc1",
        ROOT / "CWS_CONVERTOR_COMPLETE_HANDOVER_0.10.3_V2/05_SAMPLE_FILES/Pr193.step",
    )
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in candidates
        if path.is_file()
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-report", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "build/evidence/phase1_phase2_baseline.json")
    args = parser.parse_args()
    tests: dict[str, Any] = {"status": "not_run", "reason": "no test report supplied"}
    if args.test_report and args.test_report.is_file():
        tests = json.loads(args.test_report.read_text(encoding="utf-8"))
    payload = {
        "schema": "cws-current-authority-baseline-1.0",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "product": {"name": APP_NAME, "version": APP_VERSION, "project_schema": PROJECT_SCHEMA_VERSION},
        "git": {"branch": _git("branch", "--show-current"), "head": _git("rev-parse", "HEAD"), "working_tree": _git("status", "--short")},
        "runtime": {"python": platform.python_version(), "executable": sys.executable, "platform": platform.platform()},
        "dependencies": {name: _dependency(name) for name in ("PySide6", "vtk", "OCP", "cadquery", "ifcopenshell")},
        "fixture_sha256": _fixture_hashes(),
        "tests": tests,
        "safety": {"machine_observed_by_cws": False, "deployment_transport_authorized": False, "direct_machine_transfer": False, "machine_transfer_allowed": False},
    }
    target = args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown = target.with_suffix(".md")
    deps = "\n".join(f"| {name} | {item['status']} | {item.get('version', item.get('error', ''))} |" for name, item in payload["dependencies"].items())
    markdown.write_text(
        f"# CWS Convertor current baseline\n\n- Captured: `{payload['captured_at_utc']}`\n- Version: `{APP_VERSION}`\n- Project schema: `{PROJECT_SCHEMA_VERSION}`\n- Branch: `{payload['git']['branch']}`\n- HEAD: `{payload['git']['head']}`\n\n## Dependencies\n\n| Dependency | Status | Version |\n|---|---|---|\n{deps}\n\n## Test evidence\n\n```json\n{json.dumps(tests, indent=2, sort_keys=True)}\n```\n",
        encoding="utf-8",
    )
    print(target)
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
