"""Machine-readable W18 acceptance coverage for the 87 canonical BOM actions.

This audit is intentionally conservative. Presence in ACTION_DEFINITIONS or a
source handler is not treated as installed scenario proof. Each action receives
separate evidence dimensions so W18 cannot become green from a broad smoke alone.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.bom.production_hub import ACTION_DEFINITIONS

# Shipping Qt actions explicitly clicked by bom_action_evidence.py.
QT_EXECUTED = {
    "optimize.plate", "optimize.remnants_include", "optimize.remnants_exclude",
    "machine.recommend", "machine.validate", "machine.alternatives",
    "export.step", "export.ifc", "export.dxf", "export.per_machine",
    "drawing.batch_pdf", "export.xlsx", "export.csv", "export.json", "export.review",
}

# Exact downstream helpers exercised with real canonical/project state in focused
# regression tests. These are stronger than source inspection but are not labelled
# installed Qt interaction unless the QAction itself is clicked above.
INTEGRATION_EXECUTED = {
    "optimize.alternatives", "optimize.compare",
    "production.route", "production.operations",
    "viewer.section", "viewer.measure",
    "edit.profile", "edit.material", "edit.length",
    "drawing.print", "export.occurrences",
    "stock.plan", "stock.assign", "stock.release",
    "purchase.edit", "purchase.release", "purchase.cancel",
}

# Negative/fail-closed paths proven by current focused tests/evidence.
NEGATIVE_PROVEN = {
    "drawing.batch_pdf", "optimize.compare", "edit.profile", "edit.material", "edit.length",
    "production.route", "production.operations", "viewer.measure", "export.occurrences",
    "stock.assign", "stock.release",
}

# Persistence/restart evidence currently exists for project-owned stock allocation
# and canonical non-empty family state. Do not widen this set without a test.
RESTART_PROVEN = {"stock.plan", "stock.assign", "stock.release"}

# Undo proof is action-specific. Existing complete-hub tests prove transactional
# field/stock undo mechanics, but not every mutating QAction. Keep this strict.
UNDO_PROVEN = {"stock.assign"}

# Actions where a successful outcome depends on external operator/system authority
# and therefore cannot be completed solely by headless CI.
EXTERNAL_ACCEPTANCE = {"drawing.print"}

EVIDENCE_FILES = {
    "qt": "cws_convertor/ui_qt/bom_action_evidence.py",
    "routes": "tests/bom_action_routing_smoke.py",
    "final_routes": "tests/bom_w03_w18_final_routes_smoke.py",
    "families": "tests/bom_w18_nonempty_families_smoke.py",
    "exports": "tests/bom_w20_export_nonempty_smoke.py",
}


def _requirements(definition: Any) -> dict[str, bool]:
    # W18 asks positive+negative for every action. Restart matters when state or
    # downstream records are persisted; undo is required only for local mutable
    # actions that advertise mutating=True and are not external releases.
    mutating = bool(definition.mutating)
    return {
        "positive": True,
        "negative": True,
        "restart": mutating,
        "undo": mutating and definition.action_id not in {
            "purchase.release", "production.release",
        },
    }


def build_catalog() -> dict[str, Any]:
    definitions = tuple(ACTION_DEFINITIONS)
    ids = [item.action_id for item in definitions]
    if len(ids) != 87 or len(set(ids)) != 87:
        raise RuntimeError(f"Canonical action matrix changed: expected 87 unique actions, got {len(ids)}/{len(set(ids))}")

    rows = []
    for definition in definitions:
        action = definition.action_id
        required = _requirements(definition)
        evidence = {
            "qt_action_executed": action in QT_EXECUTED,
            "integration_executed": action in INTEGRATION_EXECUTED or action in QT_EXECUTED,
            "positive_postcondition": action in QT_EXECUTED or action in INTEGRATION_EXECUTED,
            "negative_postcondition": action in NEGATIVE_PROVEN,
            "restart": action in RESTART_PROVEN,
            "undo": action in UNDO_PROVEN,
            "external_acceptance": action in EXTERNAL_ACCEPTANCE,
        }
        missing = []
        if required["positive"] and not evidence["positive_postcondition"]:
            missing.append("positive_postcondition")
        if required["negative"] and not evidence["negative_postcondition"]:
            missing.append("negative_postcondition")
        if required["restart"] and not evidence["restart"]:
            missing.append("restart")
        if required["undo"] and not evidence["undo"]:
            missing.append("undo")
        if action in EXTERNAL_ACCEPTANCE:
            missing.append("external_acceptance")
        status = "COMPLETE" if not missing else "PARTIAL" if evidence["integration_executed"] else "OPEN"
        rows.append({
            "action_id": action,
            "label": definition.label,
            "category": definition.category,
            "families": list(definition.families),
            "route": definition.route,
            "mutating": bool(definition.mutating),
            "allow_blocked": bool(definition.allow_blocked),
            "requires_production_ready": bool(definition.requires_production_ready),
            "requirements": required,
            "evidence": evidence,
            "missing": missing,
            "status": status,
        })

    summary = {
        "total": len(rows),
        "complete": sum(row["status"] == "COMPLETE" for row in rows),
        "partial": sum(row["status"] == "PARTIAL" for row in rows),
        "open": sum(row["status"] == "OPEN" for row in rows),
        "qt_action_executed": sum(row["evidence"]["qt_action_executed"] for row in rows),
        "positive_postcondition": sum(row["evidence"]["positive_postcondition"] for row in rows),
        "negative_postcondition": sum(row["evidence"]["negative_postcondition"] for row in rows),
        "restart": sum(row["evidence"]["restart"] for row in rows),
        "undo": sum(row["evidence"]["undo"] for row in rows),
    }
    return {
        "schema": "cws-bom-w18-coverage-1.0",
        "claim": "coverage inventory only; COMPLETE requires all required evidence dimensions",
        "evidence_files": EVIDENCE_FILES,
        "summary": summary,
        "actions": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    catalog = build_catalog()
    text = json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    if args.require_complete and catalog["summary"]["complete"] != 87:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
