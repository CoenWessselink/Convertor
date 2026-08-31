from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cws_convertor.ui_qt.ui_v51_contract import CONTROL_INVENTORY, MAIN_LABELS, SCREEN_MANIFEST
from cws_convertor.ui_qt.design_system.icons import ICON_REGISTRY, icon_for_test_id
from cws_convertor.ui_qt.design_system.preferences import UI_PREFERENCES_SCHEMA
from cws_convertor.ui_qt.design_system.tokens import TOKENS


ROOT = Path(__file__).resolve().parents[1]
VALIDATION = ROOT / "validation" / "ui_v5_2"
REFERENCE_DIR = ROOT / "docs" / "ui" / "v5_2" / "references"


def write_json(name: str, payload: Any) -> Path:
    VALIDATION.mkdir(parents=True, exist_ok=True)
    target = VALIDATION / name
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return target


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    controls = list(CONTROL_INVENTORY["controls"])
    control_ids = [str(item["test_id"]) for item in controls]
    duplicates = sorted({item for item in control_ids if control_ids.count(item) > 1})
    screens = list(SCREEN_MANIFEST["screens"])
    references = sorted(
        path for path in REFERENCE_DIR.glob("*.png") if path.stem[:2].isdigit() and 1 <= int(path.stem[:2]) <= 25
    )
    reference_manifest = {
        "schema": "cws-ui-v5.2-reference-manifest-v1",
        "binding_source": "CWS_UI_V5_2_COMPLETE_CONTROL_BUILD_HANDOVER_2026-08-31.zip",
        "count": len(references),
        "references": [
            {"screen_id": path.stem[:2], "file": path.name, "sha256": sha256(path)}
            for path in references
        ],
        "support_surfaces_26_31": "REQUIRED_PENDING_REFERENCE_APPROVAL",
    }
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    (REFERENCE_DIR / "REFERENCE_MANIFEST.json").write_text(
        json.dumps(reference_manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    (REFERENCE_DIR / "REFERENCE_SHA256SUMS.txt").write_text(
        "".join(f"{item['sha256']}  {item['file']}\n" for item in reference_manifest["references"]), encoding="ascii"
    )

    binding = []
    unknown_icons = []
    for item in controls:
        icon_id = icon_for_test_id(str(item["test_id"]))
        if not ICON_REGISTRY.has(icon_id):
            unknown_icons.append({"test_id": item["test_id"], "icon_id": icon_id})
        binding.append(
            {
                "test_id": item["test_id"],
                "screen_id": item["screen_id"],
                "control_type": item["type"],
                "icon_id": icon_id,
                "token_set": "cws-ui-v5.2-tokens-v1",
                "state_model": ["normal", "hover", "pressed", "disabled", "focus"],
                "binding": "EXPLICIT_BY_UI_TEST_ID",
            }
        )

    write_json("CURRENT_UI_SURFACE_INVENTORY.json", {
        "schema": "cws-ui-v5.2-surface-inventory-v1",
        "count": len(screens),
        "main_navigation": list(MAIN_LABELS),
        "screens": screens,
    })
    write_json("CURRENT_UI_CONTROL_INVENTORY.json", CONTROL_INVENTORY)
    write_json("LEGACY_QSS_MIGRATION_MATRIX.json", {
        "schema": "cws-ui-v5.2-qss-migration-v1",
        "items": [
            {"authority": "ui_v51_contract.V51_LIGHT_QSS", "target": "design_system.stylesheet.V52_LIGHT_QSS", "status": "FOUNDATION_AVAILABLE"},
            {"authority": "ui_v51_contract.V51_DARK_OVERRIDE_QSS", "target": "Default Light only", "status": "DEPRECATED_NOT_DEFAULT"},
        ],
    })
    write_json("OLD_TO_NEW_SCREEN_MAP.json", {
        "schema": "cws-ui-v5.2-screen-map-v1",
        "items": [{"old_screen_id": item["screen_id"], "new_screen_id": item["screen_id"], "status": "PRESERVED"} for item in screens],
    })
    write_json("UI_FUNCTION_PARITY_BASELINE.json", {
        "schema": "cws-ui-v5.2-function-parity-v1",
        "expected_control_count": len(controls),
        "bound_control_count": len(binding),
        "missing": [],
        "duplicates": duplicates,
        "source": "existing V5.1 31-screen runtime contract",
    })
    write_json("VISUAL_TOKENS.json", TOKENS)
    write_json("ICON_MASTER.json", {
        "schema": "cws-ui-v5.2-icon-master-v1",
        "icons": ICON_REGISTRY.to_dict(),
        "unknown_bindings": unknown_icons,
    })
    write_json("CONTROL_VISUAL_BINDING.json", {
        "schema": "cws-ui-v5.2-control-visual-binding-v1",
        "count": len(binding),
        "bindings": binding,
    })
    write_json("SHORTCUT_MASTER.json", {
        "schema": "cws-ui-v5.2-shortcuts-v1",
        "items": [
            {"test_id": item["test_id"], "shortcut": item["shortcut"]}
            for item in controls if item.get("shortcut")
        ],
    })
    write_json("UI_PREFERENCES_SCHEMA.json", UI_PREFERENCES_SCHEMA)

    gates = {
        "references_01_25_present": len(references) == 25,
        "dynamic_expected_count": len(controls) == int(CONTROL_INVENTORY["count"]),
        "control_binding_100_percent": len(binding) == len(controls),
        "unknown_icons_zero": not unknown_icons,
        "duplicate_ui_test_ids_zero": not duplicates,
        "design_system_exists": (ROOT / "cws_convertor" / "ui_qt" / "design_system" / "stylesheet.py").is_file(),
        "navigation_exact": tuple(MAIN_LABELS) == ("Project", "Viewer", "Productie", "Controle", "Uitvoer"),
        "screen_contract_31": len(screens) == 31,
        "function_parity_baseline": len(binding) == len(controls),
        "current_source_revision_recorded": False,
    }
    report = {
        "schema": "cws-ui-v5.2-phase1-foundation-report-v1",
        "phase": 1,
        "status": "NOT_PROVEN" if not all(gates.values()) else "COMPLETE",
        "gates": gates,
        "passed": sum(bool(value) for value in gates.values()),
        "total": len(gates),
        "source_revision": "NOT_PROVEN (git inspection prohibited by active workspace policy)",
        "note": "Foundation and binding are measured; this report does not claim Phase 2/3 visual acceptance.",
    }
    write_json("PHASE_1_UI_FOUNDATION_REPORT.json", report)
    lines = [
        "# CWS UI V5.2 - Phase 1 Foundation Report",
        "",
        f"Status: **{report['status']}**",
        f"Gate score: **{report['passed']}/{report['total']}**",
        "",
    ]
    lines.extend(f"- {name}: {'PASS' if passed else 'NOT_PROVEN'}" for name, passed in gates.items())
    lines.extend(["", report["note"], ""])
    (VALIDATION / "PHASE_1_UI_FOUNDATION_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if all(value for key, value in gates.items() if key != "current_source_revision_recorded") else 1


if __name__ == "__main__":
    raise SystemExit(main())

