from __future__ import annotations

import json
import os


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tools.run_full_product_acceptance import (
    prepare_acceptance_project,
    runtime_inventory,
    source_inventories,
)


def main() -> int:
    _controls, functions = source_inventories()
    project, _fixture = prepare_acceptance_project(None)
    runtime_controls, result = runtime_inventory(project)
    active_classes = set(result.get("active_product_classes", ()))
    executed_functions = set(result.get("executed_product_functions", ()))
    executed_file_names = {
        (parts[0], parts[2])
        for entry in executed_functions
        if len(parts := entry.rsplit(":", 2)) == 3
    }
    uncovered = [
        item["id"]
        for item in functions
        if item["public"]
        and item["qualified_owner"] in active_classes
        and item["id"] not in executed_functions
        and (item["file"], item["name"]) not in executed_file_names
    ]
    payload = {
        "status": "PASS"
        if result.get("status") == "PASS" and runtime_controls and not uncovered
        else "FAIL",
        "runtime_control_count": len(runtime_controls),
        "active_product_class_count": len(active_classes),
        "executed_product_function_count": len(executed_functions),
        "uncovered_required": uncovered,
        "safe_method_errors": result.get("safe_method_errors", []),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if payload["status"] != "PASS":
        raise AssertionError(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
