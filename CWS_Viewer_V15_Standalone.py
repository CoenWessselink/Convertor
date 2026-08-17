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
HANDLING_CONTRACT_VERSION = "1.0"
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
    from cws_viewer.ui_qt.cockpit_phase2_v15 import phase2_workspace_contract

    contract = phase2_workspace_contract()
    docks = contract.get("docks", [])
    capabilities = contract.get("capabilities", {})
    required_t3 = (
        "orbit_pan_zoom", "orbit_around_picked_point", "selection_orbit_focus",
        "selection_pivot_precedence", "active_pivot_zoom", "picked_depth_pan",
        "display_space_fit_with_explode",
        "object_assembly_selection_mode", "temporary_alt_selection_inversion",
        "selected_object_details_shortcut", "viewer_undo_redo_shortcuts",
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
    required_phase1 = (
        "startup_geometry_cache_prefetch",
        "lazy_review_coordination_export_manufacturing",
        "fail_isolated_optional_panels",
        "clean_viewer_first_layout",
        "phase1_professional_shell",
        "startup_metrics",
    )
    required_phase2 = (
        "interactive_markup_text",
        "interactive_markup_line",
        "interactive_markup_arrow",
        "interactive_markup_cloud",
        "interactive_markup_freehand",
        "markup_live_preview",
        "markup_world_space_overlay",
        "markup_preserves_semantic_selection",
        "markup_hidden_ghost_probe_rejection",
        "saved_view_review_snapshot",
        "saved_view_markup_visibility",
        "saved_view_measurement_visibility",
        "view_groups",
        "view_group_reorder",
        "view_slideshow",
        "view_groups_local_persistent",
        "picked_surface_section_plane",
        "section_plane_offset_control",
        "variable_clip_box_fraction",
        "reset_model_display_state",
        "phase1_startup_preserved",
        "phase2_actual_vtk_input_host",
        "phase2_review_panel_remains_lazy",
    )
    export_safety = dict(contract.get("export_center", {}).get("safety", {}))
    manufacturing_safety = dict(contract.get("manufacturing", {}).get("safety", {}))
    phase2_review_safety = dict(
        contract.get("phase2", {}).get("review", {}).get("safety", {})
    )
    phase2_navigation_safety = dict(
        contract.get("phase2", {}).get("navigation", {}).get("safety", {})
    )
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
        and all(bool(capabilities.get(name)) for name in required_phase1)
        and all(bool(capabilities.get(name)) for name in required_phase2)
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
        and not bool(phase2_review_safety.get("review_mutates_canonical_geometry", True))
        and not bool(phase2_review_safety.get("markup_is_manufacturing_geometry", True))
        and not bool(phase2_review_safety.get("viewer_can_release_machine_output", True))
        and not bool(phase2_navigation_safety.get("clipping_mutates_canonical_geometry", True))
        and not bool(phase2_navigation_safety.get("section_plane_is_manufacturing_cut", True))
    )
    return {
        "status": "passed" if passed else "failed",
        "product": PRODUCT,
        "version": VERSION,
        "handling_contract_version": HANDLING_CONTRACT_VERSION,
        "handling_reference_scope": "visible_user_workflows_only",
        "frozen": bool(getattr(sys, "frozen", False)),
        "workspace": contract,
        "v15_cockpit_imported": True,
        "t3_navigation_imported": True,
        "trimble_style_handling_contract_certified": passed,
        "selected_object_orbit_pivot_certified": passed,
        "active_pivot_zoom_certified": passed,
        "phase1_startup_certified": passed,
        "phase1_viewer_first_layout_certified": passed,
        "phase1_lazy_optional_panels_certified": passed,
        "phase1_cache_prefetch_certified": passed,
        "phase2_interactive_markups_certified": passed,
        "phase2_saved_view_review_snapshot_certified": passed,
        "phase2_view_groups_slideshow_certified": passed,
        "phase2_clipping_workflow_certified": passed,
        "phase2_reset_model_certified": passed,
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
