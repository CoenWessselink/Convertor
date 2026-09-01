from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "validation" / "master_completion"
REQUIRED = (
    "CODEX_QUEUE_MASTER.json",
    "CODEX_QUEUE_MASTER.md",
    "CODEX_QUEUE_REQUIREMENTS.json",
    "CODEX_QUEUE_GAP_MATRIX.json",
    "CODEX_QUEUE_STATE.json",
    "SUPERSESSION_MATRIX.json",
    "SCREENSHOT_ACCEPTANCE_MATRIX.json",
    "CURRENT_TOTAL_ACCEPTANCE_MATRIX.json",
)
ALLOWED = {
    "PASS", "PARTIAL", "NOT_IMPLEMENTED", "NOT_INTEGRATED", "FAIL", "NOT_TESTED",
    "BLOCKED", "BLOCKED_EXTERNAL_EVIDENCE", "BLOCKED_QUEUE_SOURCE_UNAVAILABLE",
    "NOT_APPLICABLE", "SUPERSEDED",
}


def _tracked(path: str) -> bool:
    result = subprocess.run(
        ("git", "ls-files", "--error-unmatch", "--", path),
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    return result.returncode == 0


def main() -> int:
    checks: dict[str, bool] = {}
    checks["required_outputs"] = all((OUT / name).is_file() for name in REQUIRED)
    state = json.loads((OUT / "CODEX_QUEUE_STATE.json").read_text(encoding="utf-8"))
    queue = list(state.get("queue") or [])
    ids = {item.get("queue_id") for item in queue}
    checks["stable_unique_ids"] = len(ids) == len(queue) and len(queue) >= 12
    checks["valid_statuses"] = all(item.get("status") in ALLOWED for item in queue)
    checks["valid_dependencies"] = all(set(item.get("depends_on") or ()).issubset(ids) for item in queue)
    checks["queue_audit_source"] = (ROOT / "requirements" / "sources" / "CODEX_PROMPT_QUEUE_AUDIT_AND_AUTO_COMPLETE_100PCT_2026-08-31.md").is_file()
    checks["central_output_tracked"] = _tracked("cws_convertor/output/__init__.py") and _tracked("cws_convertor/output/document_output.py")
    from cws_convertor.output import DocumentOutputService
    checks["central_output_import"] = DocumentOutputService.shared() is DocumentOutputService.shared()
    requirements = json.loads((OUT / "CODEX_QUEUE_REQUIREMENTS.json").read_text(encoding="utf-8"))
    checks["requirements_decomposed"] = int(requirements.get("required_total") or 0) > 317
    checks["honest_nonpass"] = state.get("current_queue_item") == "Q002" and int(state.get("queue_status_counts", {}).get("FAIL", 0)) > 0
    result = {
        "schema": "cws.codex-queue-state-smoke.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
    }
    (OUT / "CODEX_QUEUE_STATE_SMOKE.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"CODEX_QUEUE_STATE_SMOKE={result['status']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
