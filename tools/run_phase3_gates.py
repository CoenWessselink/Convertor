"""Run the complete local phase-3 evidence gate and write one manifest."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "build" / "evidence" / "phase3_gate_manifest.json"
SCRIPTS = (
    "tests/viewer_v15_marking_smoke.py",
    "tests/viewer_v15_machine_capability_smoke.py",
    "tests/viewer_v15_manufacturing_export_smoke.py",
    "tests/viewer_v15_export_center_smoke.py",
    "tests/viewer_v15_nesting_binding_smoke.py",
    "tests/phase3_completion_smoke.py",
    "tests/phase3_workspaces_gui_smoke.py",
)
EXPECTED_M18 = {
    "size": 233402,
    "sha256": "62c1a043a63dd0628769ad0e10d68afdf890406ca6f001cf354c2d6e84b94ae1",
}


def main() -> int:
    results: list[dict[str, object]] = []
    for relative in SCRIPTS:
        completed = subprocess.run(
            [sys.executable, str(ROOT / relative)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        results.append(
            {
                "script": relative,
                "passed": completed.returncode == 0,
                "returncode": completed.returncode,
                "stdout": completed.stdout[-4000:],
                "stderr": completed.stderr[-4000:],
            }
        )
    source = ROOT / "legacy" / "M18" / "CWS_M18_UI.py"
    installed = ROOT / "cws_convertor" / "manufacturing" / "m18_runtime.py"

    def evidence(path: Path) -> dict[str, object]:
        if not path.is_file():
            return {"path": str(path), "present": False, "exact": False}
        data = path.read_bytes()
        digest = sha256(data).hexdigest()
        return {
            "path": str(path),
            "present": True,
            "size": len(data),
            "sha256": digest,
            "exact": len(data) == EXPECTED_M18["size"] and digest == EXPECTED_M18["sha256"],
        }

    m18 = {"expected": EXPECTED_M18, "source": evidence(source), "installed": evidence(installed)}
    local_green = all(bool(item["passed"]) for item in results)
    authority_green = bool(m18["source"]["exact"] and m18["installed"]["exact"])
    manifest = {
        "schema": "cws-phase3-gate-1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "local_phase3_green": local_green,
        "authority_green": authority_green,
        "status": "GREEN" if local_green and authority_green else ("EXTERNAL_BLOCKED" if local_green else "RED"),
        "machine_transfer_enabled": False,
        "machine_polling_enabled": False,
        "remote_control_enabled": False,
        "tests": results,
        "m18": m18,
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ("status", "local_phase3_green", "authority_green")}, indent=2))
    print(EVIDENCE)
    return 0 if local_green else 1


if __name__ == "__main__":
    raise SystemExit(main())
