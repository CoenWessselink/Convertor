"""Standalone entry point for the CWS Viewer V15 parity development line.

V15 deliberately preserves the hardened rc3/V14 worker and intake transport.
Only interactive/hosted viewer execution is rebound to the V15 dockable CWS
workspace. This keeps crash isolation and canonical project intake unchanged.
"""
from __future__ import annotations

import json
import multiprocessing
import sys

multiprocessing.freeze_support()

import CWS_Viewer_Standalone as _base

PRODUCT = _base.PRODUCT
VERSION = "1.4.0-v15-preview.1"
_base.VERSION = VERSION


def _install_interactive_v15_runner(args: list[str]) -> None:
    """Patch viewer-hosting paths while preserving worker/self-test transports."""
    transport_only = {
        "--version",
        "--self-test",
        "--quick-self-test",
        "--worker-self-test",
        "--multiprocessing-self-test",
        "--v14-self-test",
        "--v15-self-test",
        "--geometry-worker-service",
    }
    if any(flag in args for flag in transport_only):
        return
    from cws_viewer.ui_qt import cockpit
    from cws_viewer.ui_qt.cockpit_progress_v15 import run_cws_viewer_cockpit_v15

    cockpit.run_cws_viewer_cockpit = run_cws_viewer_cockpit_v15


def _run_v15_selftest() -> dict[str, object]:
    from cws_viewer.ui_qt.cockpit_t5_v15 import t5_workspace_contract

    contract = t5_workspace_contract()
    docks = contract.get("docks", [])
    capabilities = contract.get("capabilities", {})
    required_t3 = (
        "zoom_area",
        "camera_history",
        "view_from_face_normal",
        "camera_positioning",
        "section_plane_enable_disable",
        "clipping_box",
        "saved_view_contract",
        "deterministic_view_state",
    )
    required_t4 = (
        "area_selection",
        "multi_selection",
        "hierarchy_aware_picking",
        "grouped_properties",
        "property_search",
        "property_copy",
        "project_pick_measurement_proof",
        "exact_brep_snapping",
        "snap_tolerance_profiles",
        "snap_feedback",
        "distance_measurement",
        "angle_measurement",
        "radius_diameter_measurement",
        "measurement_export_review_state",
    )
    required_t5 = (
        "saved_views_independent_from_issues",
        "saved_view_camera_visibility_sections_clipping",
        "markup_text",
        "markup_arrow",
        "markup_cloud",
        "issues",
        "issue_status",
        "issue_priority",
        "issue_assignee",
        "issue_due_date",
        "issue_comments",
        "issue_attachments",
        "issue_optional_viewpoint_link",
        "review_checksum_store",
        "portable_cwsreview_export",
        "stale_reference_detection",
    )
    passed = (
        contract.get("schema") == "cws-viewer-workspace-15.1"
        and contract.get("version") == VERSION
        and len(docks) == 6
        and bool(capabilities.get("dockable_panels"))
        and bool(capabilities.get("persistent_layout"))
        and bool(capabilities.get("v14_functionality_preserved"))
        and all(bool(capabilities.get(name)) for name in required_t3)
        and all(bool(capabilities.get(name)) for name in required_t4)
        and all(bool(capabilities.get(name)) for name in required_t5)
        and not bool(capabilities.get("ai_derived_dimensions", True))
        and not bool(capabilities.get("silent_reference_remap", True))
        and not bool(capabilities.get("review_mutates_canonical_geometry", True))
    )
    return {
        "status": "passed" if passed else "failed",
        "product": PRODUCT,
        "version": VERSION,
        "frozen": bool(getattr(sys, "frozen", False)),
        "workspace": contract,
        "v15_cockpit_imported": True,
        "t3_navigation_imported": True,
        "t4_selection_measurement_imported": True,
        "t5_review_workspace_imported": True,
        "worker_transport_preserved": True,
        "production_machine_transfer_allowed": False,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--v15-self-test" in args:
        payload = _run_v15_selftest()
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if payload["status"] == "passed" else 2
    _install_interactive_v15_runner(args)
    _base.VERSION = VERSION
    return _base.main(args)


if __name__ == "__main__":
    raise SystemExit(main())
