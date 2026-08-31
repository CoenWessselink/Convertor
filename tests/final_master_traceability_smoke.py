from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    subprocess.run([sys.executable, str(ROOT / "tools/build_master_requirement_traceability.py"), "--check-sources"], cwd=ROOT, check=True)
    trace = json.loads((ROOT / "requirements/MASTER_REQUIREMENT_TRACEABILITY.json").read_text(encoding="utf-8"))
    active = json.loads((ROOT / "requirements/ACTIVE_REQUIREMENTS.json").read_text(encoding="utf-8"))
    superseded = json.loads((ROOT / "requirements/SUPERSEDED_REQUIREMENTS.json").read_text(encoding="utf-8"))
    rows = trace["requirements"]
    required = {"requirement_id", "source", "source_section", "description", "priority", "superseded_by", "implementation_paths", "test_paths", "evidence_paths", "implemented", "integrated", "tested", "packaged_proven", "status"}
    assert trace["required_total"] == active["required_total"] == len(rows) >= 300
    assert len({row["requirement_id"] for row in rows}) == len(rows)
    assert all(required.issubset(row) for row in rows)
    assert all(item["present"] and item["sha256"] for item in trace["sources"])
    assert len(superseded["requirements"]) >= 4
    print(f"MASTER_TRACEABILITY_SMOKE=PASS requirements={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
