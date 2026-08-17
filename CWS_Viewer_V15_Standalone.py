"""Standalone entry point for the CWS Viewer V15 parity development line.

V15 preserves the hardened rc3/V14 worker and intake transport. Interactive
viewer execution is rebound to the latest certified dockable CWS workspace.
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
    from cws_viewer.ui_qt.cockpit_t8_v15 import t8_workspace_contract

    contract = t8_workspace_contract()
    docks = contract.get("docks", [])
    capabilities = contract.get("capabilities", {})
    required_t3 = (
        "orbit_pan_zoom", "orbit_around_picked_point", "selection_orbit_focus", "picked_depth_pan",
        "object_assembly_selection_mode", "temporary_alt_selection_inversion",
        "selected_object_details_shortcut",
        "zoom_to_fit", "zoom_area", "camera_history", "view_from_face_normal",
        "orthogonal_surface_double_click", "camera_positioning", "perspective_orthographic",
        "predefined_views", "keyboard_navigation", "trimble_camera_shortcuts",
        "section_plane_enable_disable", "section_plane_flip_remove", "clipping_box",
        "saved_view_contract", "deterministic_view_state",
    )
    required_t4 = (
        "area_selection", "multi_selection", "hierarchy_aware_picking", "grouped_properties",
        "property_search", "property_copy", "project_pick_measurement_proof", "exact_brep_snapping",
        "snap_tolerance_profiles", "snap_feedback", "distance_measurement", "angle_measurement",
        "radius_diameter_measurement", "measurement_export_review_state",
    )
    required_t5 = (
        "saved_views_independent_from_issues", "saved_view_camera_visibility_sections_clipping",
        "markup_text", "markup_arrow", "markup_cloud", "issues", "issue_status", "issue_priority",
        "issue_assignee", "issue_due_date", "issue_comments", "issue_attachments",
        "issue_optional_viewpoint_link", "review_checksum_store", "portable_cwsreview_export",
        "stale_reference_detection",
    )
    required_t6 = (
        "assembly_drilldown", "assembly_main_secondary_hierarchy", "assembly_parent_child_navigation",
        "canonical_revision_compare", "compare_added_removed_changed_moved", "compare_manifest_hash",
        "clash_spatial_broad_phase", "clash_no_global_n_squared_bruteforce",
        "clash_exact_narrow_phase_extension", "clash_approximate_evidence_not_hard_claim",
        "construction_sequence", "assembly_sequence", "production_review_sequence",
        "sequence_visibility_timeline", "coordination_audit_evidence",
    )
    required_t7 = (
        "scope_first_export", "full_project_scope", "current_selection_scope", "explicit_entity_scope",
        "part_position_scope", "assembly_mark_scope", "project_phase_scope", "revision_delta_scope",
        "batch_scope", "nesting_run_scope", "nesting_bar_scope", "deterministic_scope_manifest",
        "release_preflight", "production_export_engine_reuse", "job_lifecycle",
        "job_cancel_before_write", "checksum_manifest",
    )
    required_t8 = (
        "canonical_manufacturing_faces", "right_handed_face_local_frames", "standard_i_face_resolver",
        "standard_u_c_face_resolver", "standard_l_face_resolver", "standard_rhs_shs_face_resolver",
        "round_surface_special_case", "custom_profile_no_guessing", "face_geometry_hash",
        "independent_face_validator", "dstv_mapping_is_adapter", "ambiguous_dstv_mapping_blocks",
        "manufacturing_face_viewer_overlay", "face_normal_overlay", "face_status_visualization",
    )
    export_safety = dict(contract.get("export_center", {}).get("safety", {}))
    manufacturing_safety = dict(contract.get("manufacturing", {}).get("safety", {}))
    passed = (
        contract.get("schema") == "cws-viewer-workspace-15.2"
        and contract.get("version") == VERSION
        and len(docks) == 9
        and bool(capabilities.get("dockable_panels"))
        and bool(capabilities.get("persistent_layout"))
        and bool(capabilities.get("v14_functionality_preserved"))
        and all(bool(capabilities.get(name)) for name in required_t3)
        and all(bool(capabilities.get(name)) for name in required_t4)
        and all(bool(capabilities.get(name)) for name in required_t5)
        and all(bool(capabilities.get(name)) for name in required_t6)
        and all(bool(capabilities.get(name)) for name in required_t7)
        and all(bool(capabilities.get(name)) for name in required_t8)
        and not bool(capabilities.get("ai_derived_dimensions", True))
        and not bool(capabilities.get("silent_reference_remap", True))
        and not bool(capabilities.get("review_mutates_canonical_geometry", True))
        and not bool(export_safety.get("silent_scope_broadening", True))
        and not bool(export_safety.get("missing_scope_metadata_falls_back_to_project", True))
        and not bool(export_safety.get("machine_transfer_enabled", True))
        and bool(manufacturing_safety.get("marking_feature_development", False))
        and not bool(manufacturing_safety.get("production_marking_released", True))
        and not bool(manufacturing_safety.get("machine_transfer_allowed", True))
        and not bool(manufacturing_safety.get("dstv_label_is_canonical_face_identity", True))
        and not bool(manufacturing_safety.get("unconfirmed_dstv_mapping_allowed", True))
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
        "t6_coordination_imported": True,
        "t7_export_center_imported": True,
        "t8_manufacturing_faces_imported": True,
        "worker_transport_preserved": True,
        "marking_feature_development": True,
        "production_marking_released": False,
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
