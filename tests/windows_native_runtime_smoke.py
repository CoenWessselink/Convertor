from __future__ import annotations

from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_diagnostics import run_native_self_test


def main() -> int:
    result = run_native_self_test()
    failures = [check for check in result["checks"] if check["status"] != "passed"]
    assert not failures, failures
    checks = {check["name"]: check["details"] for check in result["checks"]}
    assert Path(checks["casadi"]["native_module_path"]).name == "_casadi.pyd"
    assert checks["casadi"]["expression_result"] == 10.0
    assert checks["cadquery_ocp"]["valid_solid"] is True
    assert checks["cadquery_ocp"]["plate_bbox_mm"] == [100.0, 50.0, 10.0]
    assert checks["ifcopenshell"]["project_count"] == 1
    assert checks["pymupdf"]["page_count"] == 1
    assert checks["scientific_rendering"]["rendered_bytes"] > 0
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        assert checks["vtk_viewer"]["mode"] == "headless_ci_native_pipeline"
        assert checks["vtk_viewer"]["points"] == 3
        assert checks["vtk_viewer"]["cells"] == 1
    else:
        assert checks["vtk_viewer"]["mode"] == "offscreen_png_render"
        assert checks["vtk_viewer"]["png_bytes"] > 200
    assert checks["project_roundtrips"]["status"] == "passed"
    assert set(checks["project_roundtrips"]["formats"]) == {"nc1", "step", "ifc", "pdf"}
    assert checks["project_roundtrips"]["production_package"]["status"] == "passed"
    assert checks["project_roundtrips"]["production_package"]["checked_files"] >= 10
    print("windows_native_runtime_smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
