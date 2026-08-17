"""Executable U0 baseline contract for the Viewer V15 + Convertor + M18 merge line.

This validator intentionally uses only the Python standard library. It proves
that the frozen U0 source identities remain recorded even after later unified
phases advance the live branch. Physical M18 delivery hashes were verified when
the audit was created; CI validates those immutable fingerprints and the hard
machine-transfer safety boundary.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / "unified" / "U0_BASELINE_AUDIT.json"


def constants(path: Path) -> dict[str, object]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value_node = node.value
        if value_node is None:
            continue
        try:
            value = ast.literal_eval(value_node)
        except Exception:
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                result[target.id] = value
    return result


def main() -> int:
    report: dict[str, object] = {
        "format": "CWS_UNIFIED_U0_RUNTIME_VALIDATION_V2",
        "checks": [],
        "status": "passed",
    }

    def check(name: str, condition: bool, details: object = None) -> None:
        entry = {"name": name, "passed": bool(condition)}
        if details is not None:
            entry["details"] = details
        report["checks"].append(entry)  # type: ignore[index]
        if not condition:
            report["status"] = "failed"

    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    product = constants(ROOT / "cws_convertor" / "product.py")
    viewer = constants(ROOT / "CWS_Viewer_V15_Standalone.py")

    check("audit_format", audit.get("format") == "CWS_UNIFIED_U0_BASELINE_AUDIT_V1")
    check("audit_phase", audit.get("phase") == "U0")
    check("convertor_version", product.get("APP_VERSION") == "0.9.0-alpha-dev", product.get("APP_VERSION"))

    github_source = audit.get("github_source", {})
    check(
        "frozen_github_project_schema",
        isinstance(github_source, dict) and github_source.get("project_schema_version") == "2.5",
        github_source.get("project_schema_version") if isinstance(github_source, dict) else None,
    )
    schema = audit.get("schema_reconciliation", {})
    check(
        "live_project_schema_matches_u1_target",
        isinstance(schema, dict)
        and product.get("PROJECT_SCHEMA_VERSION") == schema.get("planned_unified_target") == "2.25",
        product.get("PROJECT_SCHEMA_VERSION"),
    )
    check("viewer_version", viewer.get("VERSION") == "1.4.0-v15-preview.2", viewer.get("VERSION"))
    check(
        "viewer_handling_contract",
        viewer.get("HANDLING_CONTRACT_VERSION") == "1.2-trimble-feel-v2",
        viewer.get("HANDLING_CONTRACT_VERSION"),
    )
    check(
        "frozen_source_commit",
        isinstance(github_source, dict)
        and github_source.get("commit") == "6fd8fac7194196aa2fda7e89559000fb5012c926",
    )

    m18 = audit.get("m18_source", {})
    check("m18_project_schema", isinstance(m18, dict) and m18.get("project_schema_version") == "2.24")
    check(
        "m18_source_commit",
        isinstance(m18, dict)
        and m18.get("source_commit") == "b04b1c203583295e8c5ed018d75de68b2319c839",
    )
    hashes = m18.get("verified_artifacts", {}) if isinstance(m18, dict) else {}
    check(
        "m18_five_artifact_fingerprints_recorded",
        isinstance(hashes, dict)
        and len(hashes) == 5
        and all(isinstance(value, str) and len(value) == 64 for value in hashes.values()),
    )

    safety = audit.get("safety", {})
    check(
        "all_machine_transport_safety_flags_false",
        isinstance(safety, dict) and safety and all(value is False for value in safety.values()),
        safety,
    )

    expected_manufacturing = (
        "faces.py",
        "contact.py",
        "marking.py",
        "identification.py",
        "machine_capability.py",
        "nesting_binding.py",
        "neutral_job.py",
    )
    manufacturing_root = ROOT / "cws_convertor" / "manufacturing"
    missing = [name for name in expected_manufacturing if not (manufacturing_root / name).is_file()]
    check("github_m1_m7_overlap_present", not missing, {"missing": missing})

    check(
        "viewer_t8_gate_present",
        (ROOT / ".github" / "workflows" / "viewer-v15-t8-manufacturing.yml").is_file(),
    )
    check(
        "integrated_v9_workflow_present",
        (ROOT / ".github" / "workflows" / "build-windows-integrated-v9.yml").is_file(),
    )
    check(
        "u1_target_recorded",
        isinstance(schema, dict) and schema.get("planned_unified_target") == "2.25",
    )

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
