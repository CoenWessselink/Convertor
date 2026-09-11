from __future__ import annotations

"""Emit a conservative W03/W18 completion matrix for every BOM action.

This audit intentionally classifies routing/preparation as PARTIAL rather than
PASS. It is a development gap register, not a release-approval mechanism.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from cws_convertor.bom.production_hub import ACTION_DEFINITIONS


PASS_SOURCE = {
    # Viewer actions with direct controller post-condition.
    "viewer.zoom", "viewer.fit", "viewer.isolate", "viewer.ghost",
    "viewer.hide", "viewer.show_all",
    # Inspection opens a concrete detail surface over the exact selection.
    "inspect.properties", "inspect.source", "inspect.assembly",
    "inspect.hashes", "inspect.blockers",
    # Transactional matrix edits.
    "edit.mark", "edit.phase", "edit.classification", "edit.assembly_add",
    "edit.assembly_remove", "edit.orientation", "edit.revision", "edit.comment",
    # Drawing execution with a concrete generated/revision/release post-condition.
    "drawing.open_part", "drawing.generate", "drawing.regenerate",
    "drawing.open_assembly", "drawing.preview", "drawing.dimension_check",
    "drawing.revision", "drawing.approve", "drawing.batch_pdf",
    # Machine review/mutation actions.
    "machine.recommend", "machine.explain", "machine.assign",
    "machine.auto_accept", "machine.manual_lock", "machine.reset",
    "machine.validate", "machine.alternatives", "machine.blocker",
    # Production mutation with project state post-condition.
    "production.release", "production.withdraw",
    # Physical stock and procurement services.
    "stock.plan", "stock.assign", "stock.release", "stock.shortage",
    "purchase.generate", "purchase.edit", "purchase.release", "purchase.cancel",
    # Review exports create actual files and hashes.
    "export.review", "export.xlsx", "export.csv", "export.json",
    # Solvers are started on exact selected IDs and completion is recorded later.
    "optimize.profile", "optimize.plate", "optimize.trade_length", "optimize.stock",
}

PARTIAL = {
    # Routed to the correct workspace, but no requested tool post-condition yet.
    "viewer.section", "viewer.measure",
    "edit.profile", "edit.material", "edit.length",
    # These open/focus settings instead of proving a changed drawing contract.
    "drawing.setup", "drawing.format", "drawing.scale", "drawing.views",
    # Read-only workflow surfaces; no concrete requested result is verified here.
    "production.route", "production.operations", "production.nc_preview",
    # Settings are prepared; solve/export is not necessarily executed by this click.
    "optimize.remnants_include", "optimize.remnants_exclude", "optimize.kerf",
    # Profile compare exists, plate compare is not universally connected.
    "optimize.compare",
    # Export form is exact and preflighted, but Generate remains a second user step.
    "export.production", "export.grouping", "export.nc1", "export.step",
    "export.ifc", "export.dxf", "export.pdf", "export.package",
    "export.per_part", "export.per_mark", "export.per_assembly",
    "export.per_machine", "export.per_phase",
}

SAFE_REFUSAL = {
    # No canonical alternative-material/profile executor exists yet.
    "optimize.alternatives",
    # Exact occurrence-only export has no separate executor; broader export is refused.
    "export.occurrences",
}

EXTERNAL_ACCEPTANCE_REQUIRED = {
    # Headless CI can prove the PDF but cannot accept a physical/native printer dialog.
    "drawing.print",
}

RATIONALE = {
    "optimize.alternatives": "Dispatcher fails closed; Phase-3 profile command service has no alternatives operation.",
    "export.occurrences": "Dispatcher refuses unsupported export intent instead of broadening the scope.",
    "drawing.print": "Canonical PDF is generated; native Qt printer dialog requires interactive Windows/printer acceptance.",
    "optimize.compare": "Profile scenario compare exists; plate compare remains conditional on a canonical plate implementation.",
}


def classify(action_id: str) -> str:
    memberships = [
        ("PASS_SOURCE", action_id in PASS_SOURCE),
        ("PARTIAL", action_id in PARTIAL),
        ("SAFE_REFUSAL", action_id in SAFE_REFUSAL),
        ("EXTERNAL_ACCEPTANCE_REQUIRED", action_id in EXTERNAL_ACCEPTANCE_REQUIRED),
    ]
    selected = [name for name, present in memberships if present]
    if len(selected) > 1:
        raise RuntimeError(f"Action {action_id} has conflicting completion classes: {selected}")
    return selected[0] if selected else "MISSING"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="build/bom-action-completion.json")
    parser.add_argument("--fail-on-missing", action="store_true")
    args = parser.parse_args()

    definitions = tuple(ACTION_DEFINITIONS)
    ids = tuple(item.action_id for item in definitions)
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate action IDs in ACTION_DEFINITIONS")

    rows = []
    for definition in definitions:
        status = classify(definition.action_id)
        rows.append({
            "action_id": definition.action_id,
            "label": definition.label,
            "category": definition.category,
            "route": definition.route,
            "mutating": definition.mutating,
            "families": list(definition.families),
            "status": status,
            "rationale": RATIONALE.get(definition.action_id, ""),
        })
    counts = Counter(row["status"] for row in rows)
    payload = {
        "schema": "cws-bom-action-completion-audit-1",
        "action_count": len(rows),
        "counts": dict(sorted(counts.items())),
        "fully_closed": counts.get("MISSING", 0) == 0 and counts.get("PARTIAL", 0) == 0,
        "rows": rows,
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"action_count": len(rows), "counts": payload["counts"], "output": str(target)}, ensure_ascii=False))
    if args.fail_on_missing and counts.get("MISSING", 0):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
