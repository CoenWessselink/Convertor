from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.master_release_gate import load_master_traceability_gate, require_master_traceability_pass


def write_traceability(root: Path, statuses: list[str]) -> None:
    target = root / "requirements" / "MASTER_REQUIREMENT_TRACEABILITY.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "schema": "test",
                "source_authority": "test",
                "required_total": len(statuses),
                "requirements": [
                    {"requirement_id": f"REQ-{index:03d}", "status": status}
                    for index, status in enumerate(statuses, start=1)
                ],
            }
        ),
        encoding="utf-8",
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        write_traceability(root, ["PASS", "PASS"])
        passed = require_master_traceability_pass(root)
        assert passed["status"] == "PASS"
        assert passed["counts"] == {"PASS": 2, "FAIL": 0, "BLOCKED": 0, "NOT_TESTED": 0}

        write_traceability(root, ["PASS", "NOT_TESTED"])
        failed = load_master_traceability_gate(root)
        assert failed["status"] == "FAIL"
        assert failed["counts"]["NOT_TESTED"] == 1
        try:
            require_master_traceability_pass(root)
        except RuntimeError as exc:
            assert "NOT_TESTED=1" in str(exc)
        else:
            raise AssertionError("Release gate accepted a NOT_TESTED requirement")

    print("final phase4 master release gate smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
