"""Build the current, conservative product requirements register.

Historical implementation/test links are candidates, never current acceptance.
The source register is intentionally usable without a CAD or Qt installation.
Every imported statement retains its original section and line or JSON pointer.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "cws-master-requirements-v2.0"
PROMPT = "requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md"
HISTORY = "requirements/MASTER_REQUIREMENT_TRACEABILITY.json"
ACTIONS = "cws_convertor/bom/production_hub.py"
FIELDS = (
    "requirement_id", "source", "category", "description", "applicable",
    "implementation", "test", "evidence", "source_commit", "installed_commit",
    "status", "blocker", "external_acceptance", "supersedes", "superseded_by",
)
STATUSES = {"PASS", "PARTIAL", "FAIL", "BLOCKED_EXTERNAL", "OUT_OF_SCOPE_APPROVED"}
DIMENSIONS = (
    "functional_built", "integration_tested", "installed_tested",
    "real_world_tested", "release_ready",
)
SCENARIOS = (
    "empty_selection", "valid_single", "valid_multiple", "mixed_selection",
    "wrong_family", "blocked", "stale", "invalid", "positive_postcondition",
    "exact_selected_ids", "no_unintended_widening", "non_selected_unchanged",
    "save_reopen", "undo", "release_invalidation",
)
BLOCK_CATEGORIES = {
    1: "requirements_bom", 2: "recognition_conversion", 3: "viewer_openbim",
    4: "drawings_change_impact", 5: "nesting_stock_purchase",
    6: "manufacturing_machines", 7: "production_shopfloor",
    8: "quality_planning_delivery", 9: "ui_performance_reporting",
    10: "installer_release_e2e",
}
# Original specifications and recent amendments. These sources contribute actual
# requirement statements; reports/old PASS percentages are not proof inputs.
TEXT_SOURCES = (
    (PROMPT, "PI", "product_integration"),
    ("docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md", "PDFUI3", "pdf_ui_v3"),
    ("docs/PDF_UI_V3_SPEC_REVIEW_20260911.md", "PDFUI3-REVIEW", "pdf_ui_v3"),
    ("docs/BOM_COMPLETE_IMPLEMENTATION.md", "BOM-SPEC", "bom"),
    ("docs/BOM_ACTION_GAP_REPAIR_20260911.md", "BOM-REPAIR", "bom"),
    ("docs/BOM_EXPORT_GAP_REPAIR_20260911.md", "BOM-EXPORT", "bom"),
    ("docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md", "BOM-REVIEW", "bom"),
    ("docs/BOM_DRAWING_BATCH_REPAIR_20260911.md", "BOM-DRAWING", "bom"),
    ("docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md", "VIEWER-ACCEPT", "viewer_openbim"),
    ("requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md", "VIEWER-V5", "viewer_openbim"),
    ("requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md", "VIEWER-PERF", "ui_performance_reporting"),
    ("requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md", "BOM-PARITY", "bom"),
    ("docs/REAL_FILE_RECOGNITION_REPAIR.md", "RECOGNITION-REAL", "recognition_conversion"),
    ("docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md", "RECOGNITION", "recognition_conversion"),
)
JSON_SOURCES = (
    (HISTORY, "requirements", "", "historical"),
    ("validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json", "requirements", "MGI3-", "manufacturing_machines"),
    ("validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json", "checks", "PDF-MATRIX-", "pdf_ui_v3"),
    ("docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json", "gaps", "VIEWER-GAP-", "viewer_openbim"),
    ("requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json", "domains", "DOMAIN-", "historical"),
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def canonical_actions(root: Path = ROOT) -> list[dict[str, Any]]:
    """Read the real ACTION_DEFINITIONS without importing GUI/CAD dependencies.

    Only constants, names of constants and BOMActionDefinition constructor calls
    are allowed. A future dynamic definition must get an explicit parser update.
    """
    module = ast.parse((root / ACTIONS).read_text(encoding="utf-8-sig"))
    constants: dict[str, Any] = {}
    fields = ("action_id", "label", "category", "families", "route", "mutating", "allow_blocked", "requires_production_ready")

    def literal(node: ast.AST) -> Any:
        return constants[node.id] if isinstance(node, ast.Name) else ast.literal_eval(node)

    for node in module.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        name = node.targets[0].id
        if name != "ACTION_DEFINITIONS":
            try:
                constants[name] = literal(node.value)
            except (ValueError, TypeError, KeyError):
                pass
            continue
        if not isinstance(node.value, (ast.Tuple, ast.List)):
            raise ValueError("ACTION_DEFINITIONS must be a literal sequence")
        actions = []
        for call in node.value.elts:
            if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != "BOMActionDefinition":
                raise ValueError("Unexpected canonical action definition")
            item = dict(zip(fields, [literal(arg) for arg in call.args]))
            item.update({kw.arg: literal(kw.value) for kw in call.keywords})
            for key in fields[5:]:
                item.setdefault(key, False)
            item["families"] = list(item["families"])
            actions.append(item)
        ids = [item["action_id"] for item in actions]
        if len(ids) != 87 or len(set(ids)) != 87:
            raise ValueError(f"Expected exactly 87 unique canonical actions; found {len(ids)}/{len(set(ids))}")
        return actions
    raise ValueError("Canonical ACTION_DEFINITIONS missing")


def statements(path: Path) -> list[dict[str, Any]]:
    """Extract individual bullets, numbered items, table rows and prose paragraphs.

    Inline numbered test lists are split too (including all 35 PDF GUI points).
    Paragraphs retain context; no acceptance requirement is inferred from code.
    """
    result: list[dict[str, Any]] = []
    headings: list[tuple[int, str]] = []
    paragraph: list[str] = []
    start = 0
    fenced = False
    lead = ""

    def emit(text: str, line: int, end: int, *, item: bool = False) -> None:
        nonlocal lead
        text = text.strip()
        if not text:
            return
        section = " > ".join(value for _, value in headings) or "Preamble"
        # A semicolon separates independent requirements in explicit lists only.
        parts = re.split(r";\s*(?=\d+\.\s)", text) if re.match(r"\d+\.\s", text) else [text]
        for part in parts:
            result.append({"text": part.strip(), "section": section, "line": line, "end_line": end, "context": lead if item else ""})
        if not item and text.endswith(":"):
            lead = text

    def flush(end: int) -> None:
        nonlocal paragraph
        if paragraph:
            emit(" ".join(paragraph), start, end)
            paragraph = []

    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        text = raw.strip()
        if text.startswith("```"):
            flush(number - 1)
            fenced = not fenced
            continue
        if fenced:
            # Commands/examples remain in the source manifest, not requirements.
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", text)
        if heading:
            flush(number - 1)
            level, title = len(heading[1]), heading[2]
            headings[:] = [(depth, value) for depth, value in headings if depth < level]
            headings.append((level, title))
            lead = ""
        elif not text or text == "---":
            flush(number - 1)
        elif re.match(r"^\|[\s|:\-]+\|$", text):
            continue
        elif text.startswith("|"):
            flush(number - 1)
            emit(" | ".join(value.strip() for value in text.strip("|").split("|")), number, number, item=True)
        elif re.match(r"^(?:[-*]\s+|\d+\.\s+)", text):
            flush(number - 1)
            value = re.sub(r"^[-*]\s+", "", text)
            emit(value, number, number, item=True)
        else:
            if not paragraph:
                start = number
            paragraph.append(text)
    flush(number if 'number' in locals() else 0)
    return result


def paths(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value] if isinstance(value, (list, tuple)) else []


def new_row(identifier: str, source: str, category: str, description: str, commit: str) -> dict[str, Any]:
    return {
        "requirement_id": identifier, "source": source, "source_section": "", "source_locator": "",
        "category": category, "description": description, "applicable": True,
        "implementation": {"state": "UNVERIFIED", "paths": []},
        "test": {"state": "NOT_RUN_CURRENT_SOURCE", "paths": []},
        "evidence": [], "source_commit": commit, "installed_commit": None,
        "status": "PARTIAL", "blocker": "CURRENT_SOURCE_ACCEPTANCE_NOT_PROVEN",
        "external_acceptance": {"required": False, "state": "NOT_REQUIRED", "reason": "", "evidence": []},
        "supersedes": [], "superseded_by": [],
        "dimensions": {key: {"state": "UNVERIFIED", "applicable": None, "applicability_reason": "Dimension applicability has not been reviewed", "evidence": []} for key in DIMENSIONS},
        "required_dimensions": [],
    }


def mark_external(row: dict[str, Any], reason: str) -> None:
    row["status"] = "BLOCKED_EXTERNAL"
    row["blocker"] = reason
    row["external_acceptance"] = {"required": True, "state": "PENDING", "reason": reason, "evidence": []}


def build_register(root: Path = ROOT, source_commit: str | None = None) -> dict[str, Any]:
    root = Path(root)
    commit = source_commit or git_head(root)
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("source_commit must be an exact 40-character Git SHA")
    rows: list[dict[str, Any]] = []
    source_paths = {path for path, *_ in TEXT_SOURCES + JSON_SOURCES}
    source_paths.update({ACTIONS, "requirements/SUPERSEDED_REQUIREMENTS.json"})
    history = read_json(root / HISTORY)
    source_paths.update(item["path"] for item in history.get("sources", []))

    for source, key, prefix, category in JSON_SOURCES:
        data = read_json(root / source)
        for index, original in enumerate(data[key]):
            identifier = str(original.get("requirement_id") or original.get("id") or f"{index + 1:03d}")
            description = original.get("description") or original.get("gap") or original.get("reason") or original.get("evidence")
            row = new_row(prefix + identifier, source, category, str(description), commit)
            row.update(source_section=original.get("source_section", key), source_locator=f"/{key}/{index}")
            row["original_source"] = original.get("source")
            row["historical_status"] = original.get("status")
            row["implementation"]["paths"] = paths(original.get("implementation_paths", original.get("implementation")))
            row["test"]["paths"] = paths(original.get("test_paths", original.get("tests")))
            row["historical_evidence"] = paths(original.get("evidence_paths", original.get("evidence")))
            row["historical_claims_accepted"] = False
            if original.get("status") in {"BLOCKED_EXTERNAL", "BLOCKED_EXTERNAL_EVIDENCE"}:
                mark_external(row, "Historical external acceptance still requires independent current evidence")
            rows.append(row)

    for source, prefix, category in TEXT_SOURCES:
        for index, statement in enumerate(statements(root / source), 1):
            block = re.search(r"BOUWBLOK (\d+)", statement["section"])
            resolved_category = BLOCK_CATEGORIES[int(block[1])] if source == PROMPT and block else category
            identifier = f"{prefix}-{index:04d}"
            row = new_row(identifier, source, resolved_category, statement["text"], commit)
            row.update(source_section=statement["section"], source_locator=f"L{statement['line']}", source_line=statement["line"], source_end_line=statement["end_line"], context=statement["context"])
            row["block"] = int(block[1]) if source == PROMPT and block else None
            row["statement_sha256"] = hashlib.sha256(statement["text"].encode()).hexdigest()
            if source == PROMPT and statement["text"] in {
                "Test BCF in onafhankelijke applicatie.", "Gebruik fysieke GPU voor final acceptance.",
                "physical validation.", "physical machine items BLOCKED_EXTERNAL totdat werkelijk gevalideerd;",
            }:
                mark_external(row, "Independent application, physical machine or physical GPU acceptance is required")
            if source == PROMPT and "9. WAT NIET GEBOUWD" in statement["section"] and statement["context"] == "Niet uitbreiden naar volledig:":
                row.update(applicable=False, status="OUT_OF_SCOPE_APPROVED", blocker="")
                row["scope_approval"] = {"source": PROMPT, "section": "9. WAT NIET GEBOUWD MOET WORDEN", "reason": "Explicit exclusion in current user instruction; integrations remain permitted"}
            rows.append(row)

    for definition in canonical_actions(root):
        action = definition["action_id"]
        row = new_row("W18-" + action, ACTIONS, "bom_w18", f"Execute {action}: {definition['label']}; prove exact selection and the action-specific result.", commit)
        row.update(source_section="ACTION_DEFINITIONS / W18 / 87 BOM-acties", source_locator=action, block=1, action_id=action, action_definition=definition)
        row["implementation"]["paths"] = [ACTIONS, "cws_convertor/ui_qt/bom_action_dispatch.py"]
        row["test"]["paths"] = ["tests/bom_w18_negative_matrix_smoke.py", "tests/bom_w18_coverage_inventory_smoke.py"]
        scenarios = {}
        for scenario in SCENARIOS:
            required = True
            reason = "Required by current W18 acceptance; no previous result is inherited"
            if scenario in {"save_reopen", "undo", "release_invalidation"}:
                # Definition flags are a lower bound: settings/export/drawing/view
                # actions can persist state even when their legacy flag is false.
                reason = "Must review actual persisted/mutating effects; legacy mutating flag alone cannot waive this scenario"
            if scenario == "mixed_selection" and len(definition["families"]) == 1:
                reason = "Mixed allowed/wrong-family selection must fail closed without widening"
            scenarios[scenario] = {"required": required, "state": "UNVERIFIED", "reason": reason, "evidence": []}
        row["scenarios"] = scenarios
        row["scenario_policy"] = "Conservative applicability: a reviewed NOT_APPLICABLE result requires an explicit reason and current evidence. Opening a workspace alone is not execution proof."
        if action == "drawing.print":
            mark_external(row, "Physical printer acceptance requires actual printed output and operator validation")
        rows.append(row)

    # Preserve explicitly superseded historical rows and make both ends navigable.
    indexed = {row["requirement_id"]: row for row in rows}
    for original in read_json(root / "requirements/SUPERSEDED_REQUIREMENTS.json")["requirements"]:
        replacement = original["superseded_by"]
        if replacement not in indexed:
            raise ValueError(f"Missing superseding historical requirement {replacement}")
        row = new_row(original["requirement_id"], "requirements/SUPERSEDED_REQUIREMENTS.json", "historical_superseded", original["description"], commit)
        row.update(applicable=False, status="OUT_OF_SCOPE_APPROVED", blocker="", superseded_by=[replacement], source_section="requirements", source_locator=original["requirement_id"])
        row["scope_approval"] = {"source": row["source"], "reason": "Explicit historical supersession retained; no PASS inherited"}
        indexed[replacement]["supersedes"].append(row["requirement_id"])
        rows.append(row)

    sources = []
    for source in sorted(source_paths):
        path = root / source
        present = path.is_file()
        sources.append({"path": source, "present": present, "sha256": sha256(path) if present else None, "role": "requirement_source_or_historical_reference"})
        if not present:
            identifier = "SOURCE-MISSING-" + hashlib.sha256(source.encode()).hexdigest()[:12]
            row = new_row(identifier, source, "source_availability", "Recover the required original source: " + source, commit)
            row.update(source_section="historical source manifest", source_locator=source)
            mark_external(row, "REQUIRED_SOURCE_MISSING")
            rows.append(row)
    for row in rows:
        dimension_applicability(row)
    register = {
        "schema": SCHEMA, "source_commit": commit, "installed_commit": None,
        "policy": {
            "historical_pass_inherited": False,
            "default_status": "PARTIAL means acceptance is unverified, not measured product failure",
            "default_dimensions": "Evidence and applicability are separate. Dimension applicability is true only where established below, otherwise unknown (null); unknown is not excluded or counted as a required/tested runtime scenario. PASS requires resolving every applicable dimension and every applicability question.",
            "source_commit_meaning": "Baseline inspected for this register; modified worktree execution must carry its own input hashes and is not installed release proof",
            "counts": "Counts are source assertions, including overlapping requirements; percentages are separate evidence dimensions and never a cosmetic product completion total",
        },
        "sources": sources, "requirements": rows,
    }
    register["summary"] = summarize(register)
    return register


def dimension_applicability(row: dict[str, Any]) -> None:
    """Establish known obligations without assigning irrelevant runtime tests.

    A requirement statement can apply while the need for installed or real-world
    testing still needs review. This is deliberately not an automatic exemption.
    """
    required = {
        "functional_built": "Every applicable requirement needs an implementation or completed process deliverable",
        "integration_tested": "Current instruction requires tests and integration evidence for completed requirements",
    }
    if row.get("block") in range(2, 11) or row.get("action_id"):
        required["installed_tested"] = "Product behavior in the current block requires applicable Windows/installed acceptance"
    text = (row["description"] + " " + row.get("source_section", "")).lower()
    if row.get("block") == 2 or re.search(r"\breal[- ](?:file|world)\b|\bhvpc\b|\brealistische bronbestanden\b|\bechte bronbestanden\b", text):
        required["real_world_tested"] = "This statement explicitly concerns real-file, real-world, corpus or representative-project validation"
    if row.get("block") == 10:
        required["release_ready"] = "Block 10 explicitly establishes final release acceptance"
    for key, reason in required.items():
        row["dimensions"][key].update(applicable=True, applicability_reason=reason)
    row["required_dimensions"] = list(required)


def summarize(register: dict[str, Any]) -> dict[str, Any]:
    rows = register["requirements"]
    active = [row for row in rows if row["applicable"]]
    dimensions = {}
    for key in DIMENSIONS:
        required = [row for row in active if key in row["required_dimensions"]]
        proven = sum(row["dimensions"][key]["state"] == "PASS" for row in required)
        dimensions[key] = {
            "proven": proven, "required": len(required),
            "unknown": sum(row["dimensions"][key]["state"] == "UNVERIFIED" for row in required),
            "applicability_unknown": sum(row["dimensions"][key].get("applicable") is None for row in active),
            "evidence_coverage_percent": round(100 * proven / len(required), 2) if required else None,
            "product_completion_percent": None,
        }
    actions = [row for row in rows if row.get("action_id")]
    return {
        "total": len(rows), "applicable": len(active), "status_counts": dict(sorted(Counter(row["status"] for row in rows).items())),
        "category_counts": dict(sorted(Counter(row["category"] for row in rows).items())),
        "historical_pass_requiring_revalidation": sum(row.get("historical_status") == "PASS" for row in rows),
        "mapped_implementation_candidates": sum(bool(row["implementation"]["paths"]) for row in active),
        "mapped_test_candidates": sum(bool(row["test"]["paths"]) for row in active),
        "dimensions": dimensions,
        "gaps": {
            "implemented": dimensions["functional_built"]["proven"],
            "partial": sum(row["status"] == "PARTIAL" for row in active),
            "missing_mapping": sum(not row["implementation"]["paths"] for row in active),
            "tested": dimensions["integration_tested"]["proven"],
            "installed": dimensions["installed_tested"]["proven"],
            "real_file": dimensions["real_world_tested"]["proven"],
            "external": sum(row["external_acceptance"]["required"] for row in active),
            "blockers": dict(sorted(Counter(row["blocker"] for row in active if row["blocker"]).items())),
        },
        "w18": {"total": len(actions), "unique": len({row["action_id"] for row in actions}), "scenario_proven": {key: sum(row["scenarios"][key]["state"] == "PASS" for row in actions) for key in SCENARIOS}},
    }


def validate_register(register: dict[str, Any], root: Path = ROOT, *, check_source_hashes: bool = True) -> list[str]:
    errors = []
    if register.get("schema") != SCHEMA:
        errors.append("Wrong register schema")
    commit = register.get("source_commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", str(commit)):
        errors.append("Invalid source_commit")
    rows = register.get("requirements", [])
    ids = [row.get("requirement_id") for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate requirement_id")
    expected_actions = {item["action_id"] for item in canonical_actions(root)}
    actual_actions = [row.get("action_id") for row in rows if row.get("category") == "bom_w18"]
    if len(actual_actions) != 87 or set(actual_actions) != expected_actions:
        errors.append("W18 must contain exactly the 87 canonical action IDs")
    expected_history = {item["requirement_id"] for item in read_json(root / HISTORY)["requirements"]}
    if not expected_history.issubset(set(ids)):
        errors.append("Missing historical requirement IDs")
    # Completeness is verified against sources, not a hardcoded current row count.
    for source, prefix, _ in TEXT_SOURCES:
        expected = {f"{prefix}-{index:04d}" for index, _ in enumerate(statements(root / source), 1)}
        if not expected.issubset(set(ids)):
            errors.append("Missing source statements: " + source)
    expected = build_register(root, commit if re.fullmatch(r"[0-9a-f]{40}", str(commit)) else None)
    expected_rows = {row["requirement_id"]: row for row in expected["requirements"]}
    if not set(expected_rows).issubset(set(ids)):
        errors.append("Missing imported source requirement IDs")
    if {item["path"] for item in register.get("sources", [])} != {item["path"] for item in expected["sources"]}:
        errors.append("Source manifest is incomplete or contains unexpected paths")
    for row in rows:
        identifier = row.get("requirement_id", "<missing>")
        missing = set(FIELDS) - set(row)
        if missing:
            errors.append(f"{identifier}: missing fields {sorted(missing)}")
            continue
        if not identifier or not row["description"] or not row["source"] or not row.get("source_section") or not row.get("source_locator"):
            errors.append(f"{identifier}: empty identity, description or source locator")
        if row["source_commit"] != commit:
            errors.append(f"{identifier}: source commit mismatch")
        original = expected_rows.get(identifier)
        if original and any(row.get(key) != original.get(key) for key in ("source", "source_section", "source_locator", "description")):
            errors.append(f"{identifier}: requirement source or statement changed")
        if row["status"] not in STATUSES:
            errors.append(f"{identifier}: invalid status")
        if type(row["applicable"]) is not bool:
            errors.append(f"{identifier}: applicable must be boolean")
        if row["status"] == "OUT_OF_SCOPE_APPROVED" and (row["applicable"] or not row.get("scope_approval")):
            errors.append(f"{identifier}: exclusion requires explicit source approval")
        for reference in row["supersedes"] + row["superseded_by"]:
            if reference not in ids:
                errors.append(f"{identifier}: unresolved supersession {reference}")
        # A referenced script or generic green report cannot promote an individual
        # requirement. Read the hashed report and require the requirement binding
        # and exact dimension/scenario outcomes inside the report itself.
        accepted_evidence: dict[str, dict[str, Any]] = {}
        for evidence in row["evidence"]:
            if not isinstance(evidence, dict):
                continue
            path = (root / str(evidence.get("path", ""))).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                continue
            if evidence.get("commit") != commit or evidence.get("result") != "PASS" or sha256(path) != evidence.get("sha256"):
                continue
            try:
                report = read_json(path)
                envelope_keys = ("commit", "app_version", "environment", "input_hash", "scenario", "result", "output_hash")
                bound = report.get("requirements", {}).get(identifier)
                if not isinstance(bound, dict) or any(report.get(key) != evidence.get(key) for key in envelope_keys):
                    errors.append(f"{identifier}: evidence report lacks matching requirement/envelope binding")
                    continue
                accepted_evidence[evidence["path"]] = bound
            except (OSError, ValueError, AttributeError):
                errors.append(f"{identifier}: evidence report is not valid bound JSON")
        for dimension in DIMENSIONS:
            entry = row.get("dimensions", {}).get(dimension, {})
            if entry.get("state") not in {"UNVERIFIED", "PASS", "FAIL", "NOT_APPLICABLE"}:
                errors.append(f"{identifier}: missing/invalid dimension {dimension}")
            if entry.get("applicable") is not None and type(entry["applicable"]) is not bool:
                errors.append(f"{identifier}: invalid applicability for {dimension}")
            if entry.get("applicable") is False and (not entry.get("applicability_reason") or entry.get("state") != "NOT_APPLICABLE"):
                errors.append(f"{identifier}: {dimension} exclusion requires a reviewed NOT_APPLICABLE result")
            if entry.get("state") == "PASS" and not entry.get("evidence"):
                errors.append(f"{identifier}: {dimension} PASS lacks evidence")
            elif entry.get("state") == "PASS" and any(accepted_evidence.get(item, {}).get("dimensions", {}).get(dimension) != "PASS" for item in entry["evidence"]):
                errors.append(f"{identifier}: {dimension} references unverified evidence")
            if entry.get("state") == "NOT_APPLICABLE" and (not entry.get("reason") or not entry.get("evidence")):
                errors.append(f"{identifier}: {dimension} applicability exemption needs reviewed evidence and reason")
        if row.get("action_id"):
            if set(row.get("scenarios", {})) != set(SCENARIOS):
                errors.append(f"{identifier}: incomplete W18 scenario matrix")
            for scenario, entry in row.get("scenarios", {}).items():
                if entry.get("state") in {"PASS", "NOT_APPLICABLE"} and not entry.get("evidence"):
                    errors.append(f"{identifier}: {scenario} has no current evidence")
                elif entry.get("state") in {"PASS", "NOT_APPLICABLE"} and any(accepted_evidence.get(item, {}).get("scenarios", {}).get(scenario) != entry["state"] for item in entry["evidence"]):
                    errors.append(f"{identifier}: {scenario} references unverified evidence")
                if not entry.get("required", True) and not entry.get("reason"):
                    errors.append(f"{identifier}: {scenario} applicability lacks reason")
        if row["status"] == "PASS":
            if row["blocker"] or not row["evidence"] or not row["implementation"]["paths"] or not row["test"]["paths"]:
                errors.append(f"{identifier}: unsupported PASS without implementation/test/evidence or with blocker")
            for dimension in row.get("required_dimensions", DIMENSIONS):
                if row["dimensions"].get(dimension, {}).get("state") != "PASS":
                    errors.append(f"{identifier}: PASS missing required dimension {dimension}")
            for dimension in DIMENSIONS:
                applicable = row["dimensions"].get(dimension, {}).get("applicable")
                if applicable is None:
                    errors.append(f"{identifier}: PASS has unresolved applicability for {dimension}")
                elif applicable and dimension not in row.get("required_dimensions", []):
                    errors.append(f"{identifier}: removed dimension {dimension} lacks reviewed exemption")
            if "installed_tested" in row.get("required_dimensions", []) and row["installed_commit"] != commit:
                errors.append(f"{identifier}: installed PASS must match exact source commit")
            if row["external_acceptance"]["required"] and (row["external_acceptance"]["state"] != "PASS" or not row["external_acceptance"]["evidence"]):
                errors.append(f"{identifier}: external acceptance not proven")
            for scenario, entry in row.get("scenarios", {}).items():
                if entry["required"] and entry["state"] != "PASS":
                    errors.append(f"{identifier}: PASS missing W18 scenario {scenario}")
        # Evidence is an execution envelope, not a path to a historical green log.
        for evidence in row["evidence"]:
            envelope = {"commit", "app_version", "environment", "input_hash", "scenario", "result", "output_hash", "path", "sha256"}
            if not isinstance(evidence, dict) or not envelope.issubset(evidence):
                errors.append(f"{identifier}: invalid evidence envelope")
                continue
            if evidence["commit"] != commit or any(not evidence[key] for key in envelope):
                errors.append(f"{identifier}: stale/empty evidence envelope")
            if not all(re.fullmatch(r"[0-9a-f]{64}", str(evidence[key])) for key in ("input_hash", "output_hash", "sha256")):
                errors.append(f"{identifier}: evidence hashes must be exact SHA256")
            path = (root / evidence["path"]).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file() or sha256(path) != evidence["sha256"]:
                errors.append(f"{identifier}: missing/changed evidence file")
    if check_source_hashes:
        for source in register.get("sources", []):
            path = root / source["path"]
            if source["present"] and (not path.is_file() or sha256(path) != source["sha256"]):
                errors.append("Source hash changed: " + source["path"])
    try:
        if register.get("summary") != summarize(register):
            errors.append("Summary does not match requirement rows")
    except (KeyError, TypeError):
        errors.append("Cannot summarize malformed requirement rows")
    return errors


def markdown(register: dict[str, Any]) -> str:
    summary = register["summary"]
    lines = ["# Master Requirements Register V2", "", f"Source baseline: `{register['source_commit']}`. Installed commit: **not proven**.", "", "Historical PASS results are not inherited. PARTIAL means current acceptance remains unverified. Existing paths are mapping candidates, not proof of behavior. Requirements from later blocks are registered now; their implementation remains subject to the mandatory block sequence.", "", f"{summary['total']} source assertions; {summary['applicable']} applicable; {summary['w18']['unique']} canonical W18 actions. Overlapping source assertions are retained with traceability, so these counts are not unique product features.", "", "Evidence coverage is not product completion: the actual built/tested product percentages remain unknown. Dimension applicability is separately recorded; an unknown need for installed/real-world testing is neither an exemption nor a required test counted in its denominator.", "", "| Evidence dimension | Proven | Known required | Applicability unknown | Evidence coverage % |", "|---|---:|---:|---:|---:|"]
    for key, value in summary["dimensions"].items():
        lines.append(f"| {key} | {value['proven']} | {value['required']} | {value['applicability_unknown']} | {value['evidence_coverage_percent']} |")
    lines += ["", f"Historical PASS rows requiring revalidation: **{summary['historical_pass_requiring_revalidation']}**. Implementation candidates: {summary['mapped_implementation_candidates']}; test candidates: {summary['mapped_test_candidates']}.", "", "W18 has 15 scenario dimensions per action. Applicability is conservative, including undo/persistence until the actual action effects have been reviewed. Printer acceptance remains external. No source-only result proves an installed build or a real-world corpus.", "", "Regenerate with `python tools/master_requirements_v2.py`; validate the checked-in inventory with `python tools/master_requirements_v2.py --check`. JSON carries every required field, source hash, historical link, scenario and evidence dimension.", "", "| Requirement | Category | Status | Description | Source |", "|---|---|---|---|---|"]
    for row in register["requirements"]:
        description = row["description"].replace("|", "\\|").replace("\n", " ")
        context = row.get("context", "").replace("|", "\\|")
        if context:
            description = context + " " + description
        lines.append(f"| {row['requirement_id']} | {row['category']} | {row['status']} | {description} | {row['source']} ({row['source_locator']}) |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit")
    parser.add_argument("--output", type=Path, default=ROOT / "requirements/MASTER_REQUIREMENTS_V2.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "requirements/MASTER_REQUIREMENTS_V2.md")
    parser.add_argument("--check", action="store_true", help="Validate existing output without rewriting")
    args = parser.parse_args()
    register = read_json(args.output) if args.check else build_register(source_commit=args.source_commit)
    errors = validate_register(register)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
        return 1
    if not args.check:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes((json.dumps(register, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_bytes(markdown(register).encode("utf-8"))
    print(json.dumps({"status": "PASS", "claim": "register structure and source coverage only; not product acceptance", "summary": register["summary"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
