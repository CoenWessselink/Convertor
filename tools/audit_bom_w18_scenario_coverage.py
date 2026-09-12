"""Conservative source-bound W18 inventory for all 87 canonical BOM actions.

A source handler, prepared route, or stale report is never positive evidence.
Supply current matrix results to demonstrate source/component dimensions.
Installed product acceptance remains a distinct release gate.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from cws_convertor.bom.production_hub import ACTION_DEFINITIONS
from tools.master_requirements_v2 import SCENARIOS


def _matrix_module():
    spec = importlib.util.spec_from_file_location("cws_w18_positive_matrix", ROOT / "tests/bom_w18_positive_matrix_smoke.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXTERNAL_ACCEPTANCE = {"drawing.print"}
EVIDENCE_FILES = {"positive_matrix": "tests/bom_w18_positive_matrix_smoke.py",
                  "negative_matrix": "tests/bom_w18_negative_matrix_smoke.py",
                  "qt": "cws_convertor/ui_qt/bom_action_evidence.py"}

# Reviewed output contracts, independent of legacy `mutating` flags. These
# actions create a file, retained drawing, persisted edit, reservation or plan.
FILE_POSTCONDITIONS = set("""
export.production export.review export.grouping export.nc1 export.step export.ifc
export.dxf export.pdf export.xlsx export.csv export.json export.package
export.occurrences export.per_part export.per_mark export.per_assembly
export.per_machine export.per_phase production.nc_preview
drawing.open_part drawing.generate drawing.regenerate drawing.open_assembly
drawing.preview drawing.setup drawing.format drawing.scale drawing.views
drawing.dimension_check drawing.revision drawing.approve drawing.batch_pdf drawing.print
edit.profile edit.material edit.length edit.mark edit.phase edit.classification
edit.assembly_add edit.assembly_remove edit.orientation edit.revision edit.comment
machine.assign machine.auto_accept machine.manual_lock machine.reset
production.release production.withdraw stock.assign stock.release
purchase.generate purchase.edit purchase.release purchase.cancel
optimize.profile optimize.plate optimize.trade_length optimize.stock
optimize.remnants_include optimize.remnants_exclude optimize.kerf
""".split())


def evidence_path(value: Path | str) -> Path:
    """Resolve only this checkout; never fall back to an absolute sibling copy."""
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError("W18 evidence path is missing")
    text = str(value)
    if any(character in text for character in ("\0", "\n", "\r")) or ".." in Path(text).parts:
        raise ValueError("Invalid W18 evidence path: " + repr(text))
    path = Path(value)
    path = (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("W18 evidence path escapes the current checkout: " + text)
    return path


def evidence_reference(value: Path | str) -> str:
    return evidence_path(value).relative_to(ROOT.resolve()).as_posix()


def _scenario_states(definition, observed, bound, report_path):
    """Keep each requested dimension independent; a happy path proves no negatives."""
    states = {name: {"status": "PARTIAL", "applicable": True,
                    "reason": "No current executed proof for this action and scenario.", "evidence": []}
              for name in SCENARIOS}
    if bound is None:
        return states
    proof = {"kind": "source_component_runtime", "path": evidence_reference(report_path),
             "sha256": hashlib.sha256(evidence_path(report_path).read_bytes()).hexdigest(),
             "source": EVIDENCE_FILES["positive_matrix"], "action_id": definition.action_id,
             "checks": [check["name"] for check in observed.get("checks", ())]}
    def passed(name, evidence, reason="Executed and source-bound action-specific assertions passed."):
        states[name].update(status="PASS", reason=reason, evidence=[evidence])
    positive = observed.get("positive_postcondition") is True
    if positive:
        for name in ("positive_postcondition", "exact_selected_ids", "no_unintended_widening", "non_selected_unchanged"):
            passed(name, proof)
        # Aggregate report IDs can combine separate test cases. Only infer a
        # single/multiple input when this row represents one actual execution.
        if not observed.get("cases"):
            passed("valid_single" if len(observed["selected_ids"]) == 1 else "valid_multiple", proof)
        if observed.get("restart"):
            passed("save_reopen", proof)
        if observed.get("undo"):
            passed("undo", proof)
    if observed.get("executed") and observed.get("status") in {"PASS", "PARTIAL", "BLOCKED_EXTERNAL"}:
        for name in observed.get("proven_scenarios", ()):
            if name in SCENARIOS and (positive or name not in {"positive_postcondition", "valid_single", "valid_multiple"}):
                passed(name, proof)
    negative = bound.get("negative_matrix") or {}
    if negative.get("result") == "PASS":
        negative_proof = {"kind": "executed_negative_matrix", "source": negative["scenario"],
                          "path": evidence_reference(negative["log"]), "sha256": negative["output_hash"],
                          "action_id": definition.action_id}
        passed("empty_selection", negative_proof, "Fresh negative matrix rejects explicit empty selection for every canonical action.")
        all_families = {"parts", "assemblies", "purchase", "fasteners", "welds", "materials", "conflicts"}
        if all_families - set(definition.families):
            for name in ("wrong_family", "mixed_selection"):
                passed(name, negative_proof, "Fresh matrix rejects unsupported family alone and mixed with a supported row, without mutation.")
        if not definition.allow_blocked and "parts" in definition.families:
            passed("blocked", negative_proof, "Fresh negative matrix rejects a blocked selected part for this action.")
    freshness = bound.get("freshness_matrix") or {}
    if freshness.get("result") == "PASS":
        freshness_proof = {"kind": "executed_freshness_matrix", "source": freshness["scenario"],
            "path": evidence_reference(freshness["log"]), "sha256": freshness["output_hash"], "action_id": definition.action_id}
        passed("stale", freshness_proof, "Every real QAction rejects stale canonical source before its executor, with no project mutation.")
        passed("invalid", freshness_proof, "Every real QAction rejects missing source binding and corrupted snapshot content before its executor.")
    if definition.action_id in EXTERNAL_ACCEPTANCE:
        states["positive_postcondition"].update(status="BLOCKED_EXTERNAL",
            reason="Actual physical printer acceptance has not been performed.", evidence=[])
    return states


def _load_results(path: Path, matrix: Any):
    path = evidence_path(path)
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("schema") != "cws-bom-w18-positive-matrix-1":
        raise ValueError("Unsupported W18 positive evidence schema")
    if report.get("matrix_sha256") != matrix.fingerprint():
        raise ValueError("W18 evidence does not match current canonical actions")
    sources = report.get("sources", {})
    if set(sources) != set(matrix.SOURCE_FILES):
        raise ValueError("W18 evidence source binding is incomplete")
    for relative, expected in sources.items():
        if matrix.digest(ROOT / relative) != expected:
            raise ValueError("Stale W18 evidence: source changed: " + relative)
    negative = report.get("negative_matrix") or {}
    negative_proven = negative.get("result") == "PASS"
    if negative_proven:
        log = evidence_path(negative.get("log") or "")
        if (negative.get("returncode") != 0 or negative.get("scenario") != "tests/bom_w18_negative_matrix_smoke.py"
                or negative.get("source_sha256") != matrix.digest(ROOT / "tests/bom_w18_negative_matrix_smoke.py")
                or not log.is_file() or matrix.digest(log) != negative.get("output_hash")
                or "BOM_W18_EMPTY_SELECTION_NEGATIVE = 87/87 PASS" not in log.read_text(encoding="utf-8", errors="replace")):
            raise ValueError("W18 negative evidence is missing, stale, failed or corrupted")
    freshness = report.get("freshness_matrix") or {}
    if freshness.get("result") == "PASS":
        log = evidence_path(freshness.get("log") or "")
        markers = ["BOM_W18_FRESHNESS_" + mode + " = 87/87 PASS" for mode in ("STALE", "MISSING_BINDING", "CORRUPT_SNAPSHOT")]
        if (freshness.get("returncode") != 0 or freshness.get("scenario") != "tests/bom_w18_freshness_smoke.py"
                or freshness.get("source_sha256") != matrix.digest(ROOT / "tests/bom_w18_freshness_smoke.py")
                or not log.is_file() or matrix.digest(log) != freshness.get("output_hash")
                or not all(marker in log.read_text(encoding="utf-8", errors="replace") for marker in markers)):
            raise ValueError("W18 freshness evidence is missing, stale, failed or corrupted")
    actions = report.get("actions", [])
    canonical = {item.action_id for item in ACTION_DEFINITIONS}
    if len(actions) != 87 or {row.get("action_id") for row in actions} != canonical:
        raise ValueError("W18 evidence must have exactly one result per canonical action")
    if (negative_proven or freshness.get("result") == "PASS"
            or any(row.get("positive_postcondition") or row.get("proven_scenarios") for row in actions)):
        if report.get("source_unchanged_during_run") is not True:
            raise ValueError("W18 sources changed during execution")
        if report.get("output_hash") != hashlib.sha256(json.dumps(actions, sort_keys=True).encode()).hexdigest():
            raise ValueError("W18 observed result content hash is missing or corrupted")
    for row in actions:
        action = row["action_id"]
        if row.get("expected_postcondition") != matrix.POSTCONDITIONS[action]:
            raise ValueError("W18 postcondition mismatch: " + action)
        if set(row.get("proven_scenarios") or ()) - set(SCENARIOS) - {"actual_pdf_prepared"}:
            raise ValueError("Unknown W18 scenario claim: " + action)
        if row.get("proven_scenarios") and (not row.get("executed") or not row.get("checks")
                or any(check.get("status") != "PASS" for check in row["checks"])
                or row.get("status") not in {"PASS", "PARTIAL", "BLOCKED_EXTERNAL"}):
            raise ValueError("Unexecuted W18 scenario claims: " + action)
        if row.get("positive_postcondition"):
            if (row.get("status") not in {"PASS", "PARTIAL"} or row.get("executed") is not True
                    or not row.get("selected_ids") or row.get("selection_widened") is not False
                    or row.get("nonselected_stable") is not True or not row.get("checks")
                    or any(check.get("status") != "PASS" for check in row["checks"])):
                raise ValueError("Incomplete/failed/prepared evidence cannot assert a positive result: " + action)
            if action in EXTERNAL_ACCEPTANCE and not report.get("external_acceptance_proven"):
                raise ValueError("External acceptance cannot be inferred from headless source evidence: " + action)
        elif row.get("status") == "PASS":
            raise ValueError("W18 PASS requires an observed positive postcondition: " + action)
        if row.get("positive_postcondition") or row.get("proven_scenarios"):
            required_files = (row.get("positive_postcondition") and action in FILE_POSTCONDITIONS) or row.get("restart") or "save_reopen" in row.get("proven_scenarios", ())
            if required_files and not row.get("artifacts"):
                raise ValueError("W18 file/persistence postcondition requires retained artifacts: " + action)
            for artifact in row.get("artifacts") or ():
                artifact_path = evidence_path(artifact.get("path") or "")
                if not artifact_path.is_file() or matrix.digest(artifact_path) != artifact.get("sha256"):
                    raise ValueError("W18 output artifact is missing or corrupted: " + action)
    return {row["action_id"]: row for row in actions}, report


def build_catalog(positive_results: Path | str | None = None) -> dict[str, Any]:
    definitions = tuple(ACTION_DEFINITIONS)
    if len(definitions) != 87 or len({item.action_id for item in definitions}) != 87:
        raise RuntimeError("Canonical action matrix changed: expected 87 unique actions")
    matrix = _matrix_module()
    scenarios = {row["action_id"]: row for row in matrix.scenario_catalog()}
    bound = None
    if positive_results is not None:
        scenarios, bound = _load_results(Path(positive_results), matrix)
    rows = []
    for definition in definitions:
        action = definition.action_id
        scenario = scenarios[action]
        scenario_states = _scenario_states(definition, scenario, bound, positive_results)
        required = {name: value["applicable"] for name, value in scenario_states.items()}
        positive = bool(scenario.get("positive_postcondition"))
        evidence = {
            "qt_action_executed": bool(scenario.get("qt_action_executed")),
            "integration_executed": bool(scenario.get("executed")),
            "positive_postcondition": positive,
            "negative_postcondition": bool(bound and (bound.get("negative_matrix") or {}).get("result") == "PASS"),
            "restart": positive and bool(scenario.get("restart")),
            "undo": positive and bool(scenario.get("undo")),
            "external_acceptance": action in EXTERNAL_ACCEPTANCE,
            "selected_ids": list(scenario.get("selected_ids") or ()),
            "selection_widened": scenario.get("selection_widened"),
            "nonselected_stable": bool(scenario.get("nonselected_stable")),
            "runtime_bound": bound is not None,
        }
        missing = [name for name, value in scenario_states.items()
                   if value["status"] != "PASS" and not (value["status"] == "NOT_APPLICABLE" and value["applicable"] is False and value["reason"] and value["evidence"])]
        if action in EXTERNAL_ACCEPTANCE:
            missing.append("external_acceptance")
        status = ("BLOCKED_EXTERNAL" if action in EXTERNAL_ACCEPTANCE else
                  "COMPLETE" if not missing else "PARTIAL" if evidence["integration_executed"] else "OPEN")
        rows.append({"action_id": action, "label": definition.label, "category": definition.category,
            "families": list(definition.families), "route": definition.route,
            "mutating": bool(definition.mutating), "allow_blocked": bool(definition.allow_blocked),
            "requires_production_ready": bool(definition.requires_production_ready),
            "requirements": required, "expected_postcondition": scenario["expected_postcondition"],
            "scenario_status": scenario["status"], "scenario_reason": scenario.get("reason", ""),
            "scenarios": scenario_states, "evidence": evidence, "missing": missing, "status": status})
    summary = {"total": len(rows), **{name.lower(): sum(row["status"] == name for row in rows)
                                    for name in ("COMPLETE", "PARTIAL", "OPEN", "BLOCKED_EXTERNAL")}}
    for name in ("qt_action_executed", "positive_postcondition", "negative_postcondition", "restart", "undo"):
        summary[name] = sum(bool(row["evidence"][name]) for row in rows)
    summary["scenario_proven"] = {name: sum(row["scenarios"][name]["status"] == "PASS" for row in rows) for name in SCENARIOS}
    return {"schema": "cws-bom-w18-coverage-3.0",
        "claim": "Source/component coverage only. COMPLETE requires all 15 applicable scenarios; legacy mutating flags waive none. Installed main-window acceptance is separate.",
        "positive_results": evidence_reference(positive_results) if positive_results else None,
        "installed_main_window_proven": bool(bound and bound.get("installed_main_window")),
        "evidence_files": EVIDENCE_FILES, "summary": summary, "actions": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--positive-results", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    catalog = build_catalog(args.positive_results)
    content = json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes((content + "\n").encode("utf-8"))
    else:
        print(content)
    return 2 if args.require_complete and catalog["summary"]["complete"] != 87 else 0


if __name__ == "__main__":
    raise SystemExit(main())
