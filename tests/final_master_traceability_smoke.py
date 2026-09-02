from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_master_requirement_traceability import build


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/build_master_requirement_traceability.py"),
                "--check-sources",
                "--output-dir",
                str(output),
            ],
            cwd=ROOT,
            check=True,
        )
        trace = json.loads((output / "MASTER_REQUIREMENT_TRACEABILITY.json").read_text(encoding="utf-8"))
        active = json.loads((output / "ACTIVE_REQUIREMENTS.json").read_text(encoding="utf-8"))
        superseded = json.loads((output / "SUPERSEDED_REQUIREMENTS.json").read_text(encoding="utf-8"))
        assert (output / "MASTER_REQUIREMENT_TRACEABILITY.md").is_file()
        rows = trace["requirements"]
        required = {"requirement_id", "source", "source_section", "description", "priority", "superseded_by", "implementation_paths", "test_paths", "evidence_paths", "implemented", "integrated", "tested", "packaged_proven", "status"}
        assert trace["required_total"] == active["required_total"] == len(rows) >= 300
        assert len({row["requirement_id"] for row in rows}) == len(rows)
        assert all(required.issubset(row) for row in rows)
        assert all(item["present"] and item["sha256"] for item in trace["sources"])
        assert len(superseded["requirements"]) >= 4
        print(f"MASTER_TRACEABILITY_SMOKE=PASS requirements={len(rows)}")

        evidence_root = output / "release_traceability"
        for phase in range(1, 5):
            gate = evidence_root / f"phase{phase}" / "PHASE_GATE.json"
            gate.parent.mkdir(parents=True, exist_ok=True)
            gate.write_text(
                json.dumps({"status": "PASS", "packaged_proven": True}),
                encoding="utf-8",
            )
        release_trace, _, _ = build(evidence_root)
        assert release_trace["required_total"] == len(release_trace["requirements"])
        assert release_trace["status_counts"] == {"PASS": release_trace["required_total"]}
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
