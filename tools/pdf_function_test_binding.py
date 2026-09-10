"""Bind each PDF requirement to executed, non-skipped regression test methods."""
from __future__ import annotations
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import importlib
import io
import json
import unittest

ENGINE='tests.production_drawing_engine_smoke.ProductionDrawingEngineTests.'
EDITOR='tests.interactive_dimension_editor_v2_acceptance_smoke.InteractiveDimensionV2AcceptanceTests.'
TRUSTED='tests.pdf_review_smoke.TrustedPDFTests.'
EXTERNAL='tests.pdf_review_smoke.ExternalPDFAndAITests.'
BASE=ENGINE+'test_document_is_single_versioned_authority_for_all_content'
BINDINGS={f'PDF-{n:02d}':[BASE] for n in range(1,44)}
for n in (1,8,36):BINDINGS[f'PDF-{n:02d}']=[ENGINE+'test_pdf_preview_and_embedded_document_are_the_same_content']
for n in (2,3):BINDINGS[f'PDF-{n:02d}']=[ENGINE+'test_all_iso_sheet_sizes_and_orientations_use_physical_dimensions']
for n in (4,5,6):BINDINGS[f'PDF-{n:02d}']=[EDITOR+'test_sheet_orientation_scale_view_and_unit_pairwise_coverage']
for n in (7,26):BINDINGS[f'PDF-{n:02d}']=[ENGINE+'test_iso_and_3d_are_distinct_projections',ENGINE+'test_native_occt_hlr_and_trusted_pdf_bind_the_same_document']
BINDINGS['PDF-12']=[EDITOR+'test_every_required_dimension_kind_reaches_vector_document']
for n in (19,20,23,25):BINDINGS[f'PDF-{n:02d}']=[ENGINE+'test_native_occt_hlr_and_trusted_pdf_bind_the_same_document']
BINDINGS['PDF-21']=[ENGINE+'test_coplanar_mesh_diagonal_is_not_a_drawing_edge']
BINDINGS['PDF-24']=[BASE,EDITOR+'test_section_and_detail_dimensions_render_on_their_own_sheet']
BINDINGS['PDF-31']=[ENGINE+'test_large_dimension_schedule_creates_continuation_sheets']
BINDINGS['PDF-32']=[EDITOR+'test_assembly_component_snaps_preserve_child_entity_identity',ENGINE+'test_mesh_fallback_is_explicitly_fail_closed']
BINDINGS['PDF-34']=[ENGINE+'test_release_ready_requires_and_accepts_all_exact_gates']
BINDINGS['PDF-35']=[ENGINE+'test_linter_detects_clipping_and_annotation_collision']
BINDINGS['PDF-37']=[TRUSTED+'test_corrupted_model_attachment_is_rejected']
BINDINGS['PDF-38']=[TRUSTED+'test_visible_tamper_is_rejected_and_not_downgraded_to_external_pdf']
BINDINGS['PDF-39']=[TRUSTED+'test_nc1_to_trusted_pdf_to_nc1_restores_exact_source_bytes']
BINDINGS['PDF-40']=[EXTERNAL+'test_synthetic_lo4_vector_fields_geometry_and_review_gate']
BINDINGS['PDF-41']=['tests.unified_ui_shell_u3_gui_smoke.UnifiedUiShellU3GuiTests.test_default_shell_uses_one_context_for_viewer_scribing_bom_and_export']
BINDINGS['PDF-42']=['tests.production_release_package_smoke.ProductionReleasePackageTests.test_stale_release_and_duplicate_visible_mark_are_blocked']
# PDF-43 additionally requires verified distinct packaged processes in the caller.
BINDINGS['PDF-43']=[ENGINE+'test_embedded_drawing_document_tamper_is_rejected']

def run_bound_tests(output:Path)->dict:
    records={}
    for name in sorted({test for tests in BINDINGS.values() for test in tests}):
        module_name,class_name,method=name.rsplit('.',2)
        cls=getattr(importlib.import_module(module_name),class_name)
        stream=io.StringIO()
        with redirect_stdout(stream),redirect_stderr(stream):
            result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite([cls(method)]))
        records[name]={'passed':result.wasSuccessful() and result.testsRun==1 and not result.skipped,
                       'tests_run':result.testsRun,'skipped':len(result.skipped),'failures':len(result.failures),
                       'errors':len(result.errors),'log':stream.getvalue()}
    rows={key:{'tests':names,'passed':all(records[n]['passed'] for n in names)} for key,names in BINDINGS.items()}
    output.write_text(json.dumps({'requirements':rows,'test_executions':records},indent=2),encoding='utf-8')
    failed=[key for key,value in rows.items() if not value['passed']]
    if failed:raise RuntimeError('PDF requirement tests failed/skipped: '+', '.join(failed))
    return rows
