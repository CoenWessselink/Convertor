"""Metadata or prepared routes cannot turn W18 acceptance green."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.audit_bom_w18_scenario_coverage import _matrix_module, build_catalog
from tools.master_requirements_v2 import SCENARIOS
from tools import audit_bom_w18_scenario_coverage as audit


def run():
    catalog = build_catalog()
    summary = catalog["summary"]
    assert summary["total"] == 87
    assert sum(summary[key] for key in ("complete", "partial", "open", "blocked_external")) == 87
    assert len({row["action_id"] for row in catalog["actions"]}) == 87
    assert summary["negative_postcondition"] == 0, "No negative runtime evidence supplied"
    assert summary["positive_postcondition"] == summary["complete"] == 0, "No runtime evidence supplied"
    assert all(row["expected_postcondition"] for row in catalog["actions"])
    assert all(set(row["scenarios"]) == set(SCENARIOS) for row in catalog["actions"])
    assert all(row["scenarios"]["stale"]["status"] == "PARTIAL" for row in catalog["actions"])
    assert {row["action_id"] for row in catalog["actions"] if row["status"] == "BLOCKED_EXTERNAL"} == {"drawing.print"}
    assert not catalog["installed_main_window_proven"]
    matrix = _matrix_module()
    report = {"schema": "cws-bom-w18-positive-matrix-1", "matrix_sha256": matrix.fingerprint(),
              "sources": {name: matrix.digest(ROOT / name) for name in matrix.SOURCE_FILES},
              "actions": matrix.scenario_catalog(), "external_acceptance_proven": False}
    with tempfile.TemporaryDirectory(prefix="cws-w18-inventory-", dir=ROOT) as folder:
        path = Path(folder) / "positive.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        assert build_catalog(path)["summary"]["positive_postcondition"] == 0
        def rejected(payload, reason):
            path.write_text(json.dumps(payload), encoding="utf-8")
            try:
                build_catalog(path)
            except ValueError:
                return
            raise AssertionError(reason)
        stale = deepcopy(report)
        stale["sources"][matrix.SOURCE_FILES[0]] = "stale"
        rejected(stale, "Changed source must invalidate old runtime proof")
        fake_negative = deepcopy(report)
        fake_negative["negative_matrix"] = {"result": "PASS", "returncode": 0,
            "scenario": "tests/bom_w18_negative_matrix_smoke.py", "source_sha256": matrix.digest(ROOT / "tests/bom_w18_negative_matrix_smoke.py"),
            "log": str(Path(folder) / "missing.txt"), "output_hash": "missing"}
        rejected(fake_negative, "Declared negative PASS without actual fresh log must fail closed")
        missing = deepcopy(report)
        missing["actions"].pop()
        rejected(missing, "Missing canonical action must fail closed")
        prepared = deepcopy(report)
        prepared["actions"][0].update(status="prepared", positive_postcondition=True, executed=True)
        rejected(prepared, "A prepared or navigation-only action is not positive evidence")
        widened = deepcopy(report)
        widened["actions"][0].update(status="PASS", positive_postcondition=True, executed=True,
                                     selected_ids=["P1"], selection_widened=True, nonselected_stable=True,
                                     checks=[{"name": "fake", "status": "PASS"}])
        rejected(widened, "Selection widening invalidates positive acceptance")
        one_path = deepcopy(report)
        one_path["source_unchanged_during_run"] = True
        one_path["actions"][0].update(status="PASS", positive_postcondition=True, executed=True,
            selected_ids=["P1"], selection_widened=False, nonselected_stable=True,
            restart=True, undo=True, checks=[{"name": "Unit fixture only: one exact positive result", "status": "PASS"}])
        retained = Path(folder) / "selected-output.json"
        retained.write_bytes(b'{"unit_fixture":true}')
        one_path["actions"][0]["artifacts"] = [{"path": retained.relative_to(ROOT).as_posix(), "sha256": matrix.digest(retained)}]
        one_path["output_hash"] = hashlib.sha256(json.dumps(one_path["actions"], sort_keys=True).encode()).hexdigest()
        path.write_text(json.dumps(one_path), encoding="utf-8")
        derived = build_catalog(path)
        first = derived["actions"][0]
        assert first["status"] == "PARTIAL" and derived["summary"]["complete"] == 0
        assert first["scenarios"]["valid_single"]["status"] == "PASS"
        assert all(first["scenarios"][name]["status"] == "PARTIAL" for name in ("valid_multiple", "stale", "invalid", "blocked", "release_invalidation"))
        assert all(first["scenarios"][name]["evidence"] for name in ("positive_postcondition", "exact_selected_ids", "save_reopen", "undo"))
        failed_scenario = deepcopy(one_path)
        failed_scenario["actions"][0].update(status="PARTIAL", positive_postcondition=False,
            proven_scenarios=["stale"], checks=[{"name": "Failed stale proof must not bind", "status": "FAIL"}])
        failed_scenario["output_hash"] = hashlib.sha256(json.dumps(failed_scenario["actions"], sort_keys=True).encode()).hexdigest()
        rejected(failed_scenario, "Nonpositive scenario cannot promote failed assertions")
        missing_artifact = deepcopy(failed_scenario)
        missing_artifact["actions"][0].update(checks=[{"name": "Claimed stale check", "status": "PASS"}],
            artifacts=[{"path": str(Path(folder) / "missing-proof.json"), "sha256": "0"*64}])
        missing_artifact["output_hash"] = hashlib.sha256(json.dumps(missing_artifact["actions"], sort_keys=True).encode()).hexdigest()
        rejected(missing_artifact, "Nonpositive scenario requires its actual bound artifact")
        stripped = deepcopy(one_path)
        export = next(row for row in stripped["actions"] if row["action_id"] == "export.review")
        export.update(status="PASS", positive_postcondition=True, executed=True, selected_ids=["P1"],
            selection_widened=False, nonselected_stable=True, restart=False,
            checks=[{"name": "Claimed actual export output", "status": "PASS"}], artifacts=[])
        stripped["output_hash"] = hashlib.sha256(json.dumps(stripped["actions"], sort_keys=True).encode()).hexdigest()
        rejected(stripped, "File-producing positive action cannot pass with stripped artifact list")
        # Copy a minimal validator fixture to a second root. Identical relative
        # reports must bind to the second copy, independent of process cwd.
        roots = [Path(folder) / name for name in ("copy-a", "copy-b")]
        for root in roots:
            (root / "proof").mkdir(parents=True)
            (root / "bound.py").write_bytes(b"# Validator fixture only\n")
            (root / "proof/selected-output.json").write_bytes(retained.read_bytes())
        moved = deepcopy(one_path)
        moved["sources"] = {"bound.py": matrix.digest(roots[0] / "bound.py")}
        moved["actions"][0]["artifacts"][0]["path"] = "proof/selected-output.json"
        moved["output_hash"] = hashlib.sha256(json.dumps(moved["actions"], sort_keys=True).encode()).hexdigest()
        stub = SimpleNamespace(SOURCE_FILES=("bound.py",), digest=matrix.digest,
            fingerprint=matrix.fingerprint, POSTCONDITIONS=matrix.POSTCONDITIONS,
            scenario_catalog=matrix.scenario_catalog)
        catalogs = []
        for root in roots:
            (root / "proof/result.json").write_bytes(json.dumps(moved).encode())
            with patch.object(audit, "ROOT", root), patch.object(audit, "_matrix_module", return_value=stub):
                catalogs.append(audit.build_catalog("proof/result.json"))
        assert catalogs[0] == catalogs[1], "Moving retained proof must not change catalog references or hashes"
        with patch.object(audit, "ROOT", roots[1]), patch.object(audit, "_matrix_module", return_value=stub):
            (roots[1] / "proof/selected-output.json").unlink()
            try:
                audit.build_catalog("proof/result.json")
            except ValueError:
                pass
            else:
                raise AssertionError("Missing artifact in moved checkout must not reuse intact original copy")
            moved["actions"][0]["artifacts"][0]["path"] = str(roots[0] / "proof/selected-output.json")
            moved["output_hash"] = hashlib.sha256(json.dumps(moved["actions"], sort_keys=True).encode()).hexdigest()
            (roots[1] / "proof/result.json").write_bytes(json.dumps(moved).encode())
            try:
                audit.build_catalog("proof/result.json")
            except ValueError:
                pass
            else:
                raise AssertionError("Absolute reference to a different checkout must be rejected")
    print("BOM_W18_COVERAGE_INVENTORY = PASS")
    print(summary)


if __name__ == "__main__":
    run()
