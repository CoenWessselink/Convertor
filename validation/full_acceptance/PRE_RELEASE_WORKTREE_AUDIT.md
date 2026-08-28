# Pre-release worktree audit

Branch: `agent/cws-product-ui-reintegration-v1`
HEAD: `0100801087c431c72666b780782bb263d3e5ccec`
Parent: `a824b79a0d063e5f3f845711ca9187edb8884847`
Ahead/behind: `0/0`

| Path | Status | Classificatie | Reden |
| --- | --- | --- | --- |
| `.github/workflows/final-release-proof.yml` | `??` | `COMMIT_REQUIRED` | Required CI op exacte release-SHA |
| `.gitignore` | ` M` | `COMMIT_REQUIRED` | Reproduceerbare product/buildconfiguratie |
| `CWS_Convertor.spec` | ` M` | `COMMIT_REQUIRED` | Reproduceerbare product/buildconfiguratie |
| `CWS_Convertor_Phase3.exe` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Niet-commitgebonden lokaal buildproduct |
| `CWS_Convertor_Setup_0.10.18-beta-dev_x64.exe` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Niet-commitgebonden lokaal buildproduct |
| `build_windows_exe.bat` | ` M` | `COMMIT_REQUIRED` | Reproduceerbare product/buildconfiguratie |
| `converter.py` | ` M` | `COMMIT_REQUIRED` | Reproduceerbare product/buildconfiguratie |
| `cws_convertor/integration/ui_context.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/integration/workspace.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/manufacturing/export_scope_matrix.py` | `??` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/manufacturing/m18_authority_runtime.b64` | `??` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/manufacturing/m18_authority_runtime.manifest.json` | `??` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/manufacturing/m18_authority_runtime.zip` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/optimization/plate_nesting/__init__.py` | `??` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/optimization/plate_nesting/core.py` | `??` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/optimization/profile_nesting/__init__.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/optimization/profile_nesting/command_service.py` | `??` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/optimization/profile_nesting/phase2.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/optimization/profile_nesting/snapshot.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/production_export/release.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/project/service.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/project/storage.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/quality/__init__.py` | `??` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/quality/model.py` | `??` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/ui_qt/__init__.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/ui_qt/functional_workspaces.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/ui_qt/main_window.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/ui_qt/phase3_workspaces.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/ui_qt/product_workspaces.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/ui_qt/project_workspace.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_convertor/ui_qt/u4_shell.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_viewer/adapters/project_model.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_viewer/adapters/project_scene_loader.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_viewer/adapters/source_geometry.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_viewer/adapters/source_style_scene.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_viewer/backends/vtk_project_mesh.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_viewer/backends/vtk_project_mesh_adaptive.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_viewer/backends/vtk_project_mesh_feel_v2.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_viewer/contracts/geometry.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_viewer/contracts/state.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_viewer/core/controller.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_viewer/geometry/frozen_worker.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_viewer/geometry/ifc_provider.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_viewer/geometry/isolated.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_viewer/math3d.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_viewer/ui_qt/cockpit_trimble_feel_v2.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `cws_viewer/ui_qt/trimble_navigation_overlay.py` | ` M` | `COMMIT_REQUIRED` | Productbron of gebundelde runtime-authority |
| `docs/CWS_CONVERTOR_FINAL_CONTINUATION_PROMPT.md` | `??` | `COMMIT_REQUIRED` | Release-, gebruikers- of packagingdocumentatie |
| `docs/CWS_CONVERTOR_FORMAT_FEATURE_MACHINE_MATRIX.md` | `??` | `COMMIT_REQUIRED` | Release-, gebruikers- of packagingdocumentatie |
| `docs/CWS_CONVERTOR_KNOWN_LIMITATIONS.md` | `??` | `COMMIT_REQUIRED` | Release-, gebruikers- of packagingdocumentatie |
| `docs/CWS_CONVERTOR_PROMPT_TRACEABILITY.md` | `??` | `COMMIT_REQUIRED` | Release-, gebruikers- of packagingdocumentatie |
| `docs/CWS_CONVERTOR_SUPPORT_PACK.md` | `??` | `COMMIT_REQUIRED` | Release-, gebruikers- of packagingdocumentatie |
| `docs/CWS_CONVERTOR_TECHNICAL_GUIDE.md` | `??` | `COMMIT_REQUIRED` | Release-, gebruikers- of packagingdocumentatie |
| `docs/CWS_CONVERTOR_USER_GUIDE.md` | `??` | `COMMIT_REQUIRED` | Release-, gebruikers- of packagingdocumentatie |
| `docs/unified/U2_M18_GITHUB_SEMANTIC_MERGE_MATRIX.json` | ` M` | `COMMIT_REQUIRED` | Release-, gebruikers- of packagingdocumentatie |
| `github/workflows/build-windows-exe.yml` | `M ` | `REVIEW_REQUIRED` | Niet automatisch geclassificeerd |
| `installer/CWS_Convertor.iss` | ` M` | `COMMIT_REQUIRED` | Release-, gebruikers- of packagingdocumentatie |
| `requirements-runtime.lock.txt` | ` M` | `COMMIT_REQUIRED` | Reproduceerbare product/buildconfiguratie |
| `runtime_diagnostics.py` | ` M` | `COMMIT_REQUIRED` | Reproduceerbare product/buildconfiguratie |
| `tests/edit_workspace_ui_smoke.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/full_acceptance_ifc_batch_smoke.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/full_acceptance_project_cancel_smoke.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/full_acceptance_qt_progressive_exact_smoke.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/full_acceptance_qt_viewer_visual_smoke.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/full_acceptance_stress_matrix.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/full_acceptance_workspace_screenshots.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/phase1_phase2_context_e2e_gui_smoke.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/phase1_profile_nesting_command_service_smoke.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/phase2_export_scope_matrix_smoke.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/phase2_m18_packaged_gate_smoke.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/phase2_manufacturing_e2e_smoke.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/phase2_manufacturing_persistence_smoke.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/phase2_plate_nesting_smoke.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/phase3_quality_inspection_smoke.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/phase3_real_file_matrix.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/phase3_soak_smoke.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/phase3_visual_dpi_smoke.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/product_full_acceptance.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/project_classification_smoke.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/project_cli_smoke.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/steel_model_foundation_smoke.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/unified_production_workflow_u4_smoke.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/unified_ui_shell_u3_gui_smoke.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/unified_viewer_v15_u3_smoke.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/viewer_profile_proxy_visibility_smoke.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/viewer_v15_layout_navigation_acceptance.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/viewer_v15_trimble_feel_v2_smoke.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/viewer_v1_vtk_smoke.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/viewer_v4_windows_config_smoke.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/viewer_v9_packaging_config_smoke.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/viewer_v9_qt_contract_smoke.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/viewer_v9_workspace_navigation_smoke.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/viewer_visual_geometry_regression_smoke.py` | `??` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tests/windows_installer_association_smoke.py` | ` M` | `COMMIT_REQUIRED` | Regression- of acceptancetest |
| `tools/audit_release_worktree.py` | `??` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `tools/build_phase1_real_evidence.py` | `??` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `tools/build_phase1_validation.py` | ` M` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `tools/build_phase1_windows_release.py` | ` M` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `tools/build_phase2_validation.py` | `??` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `tools/build_phase2_windows_release.py` | `??` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `tools/build_phase3_validation.py` | `??` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `tools/build_phase3_windows_release.py` | `??` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `tools/build_superprompt_acceptance_report.py` | `??` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `tools/finalize_commit_bound_release.py` | `??` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `tools/finalize_phase_acceptance.py` | `??` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `tools/finalize_windows_release.py` | `??` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `tools/restore_m18_authority.py` | ` M` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `tools/run_full_product_acceptance.py` | `??` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `tools/run_phase1_unified_gates.py` | ` M` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `tools/run_phase2_unified_gates.py` | `??` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `tools/run_phase3_gates.py` | ` M` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `validation/full_acceptance/ACCEPTANCE_ENVIRONMENT.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/DYNAMIC_UI_RUNTIME_COVERAGE.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/FILE_FORMAT_MATRIX.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/FIXTURE_CATALOG.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/FULL_ACCEPTANCE_CHECKLIST.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/FULL_ACCEPTANCE_CHECKLIST.md` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/FULL_ACCEPTANCE_REPORT.md` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/FULL_PRODUCT_ACCEPTANCE_CHECKLIST.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/FULL_PRODUCT_ACCEPTANCE_REPORT.md` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/FULL_PRODUCT_ACCEPTANCE_SUMMARY.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/FULL_PRODUCT_ACCEPTANCE_SUMMARY.md` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/FUNCTION_INVENTORY.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/FUNCTION_INVENTORY.md` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/GUI_TEST_RESULTS.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/IFC_BATCH_RESULTS.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/INSTALLER_TEST_RESULTS.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/NEGATIVE_TEST_MATRIX.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/OUTPUT_ARTIFACT_MANIFEST.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/PERFORMANCE_RESULTS.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/PERSISTENCE_MATRIX.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/PHASE_GATE_RESULTS.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/PORTABLE_TEST_RESULTS.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/PROJECT_CANCEL_RESULTS.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/QT_PROGRESSIVE_EXACT_RESULTS.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/QT_VIEWER_VISUAL_RESULTS.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/REAL_GEOMETRY_EVIDENCE.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/SCREENSHOT_MANIFEST.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/SOURCE_TEST_RESULTS.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/STRESS_MATRIX_RESULTS.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/STRESS_RESULTS.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/UI_CONTROL_INVENTORY.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/UI_CONTROL_INVENTORY.md` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/WINDOWS_EXE_TEST_RESULTS.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/WORKFLOW_MATRIX.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/WORKSPACE_SCREENSHOT_RESULTS.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/_exact_baseline_probe.py` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/exact_baseline_stderr.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/logs/SUPERPROMPT_AUDIT.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/run_phase1_unified_gates.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/run_phase2_unified_gates.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/run_phase3_gates.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/CWS_Convertor_Phase3_DPI_100.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/CWS_Convertor_Phase3_DPI_125.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/CWS_Convertor_Phase3_DPI_150.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/CWS_Convertor_Phase3_DPI_200.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/progressive_first_frame.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/progressive_first_frame_vtk.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/qt_progressive_exact.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/qt_viewer_opaque_selected.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/workspace-00-rapport.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/workspace-01-inlezen.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/workspace-02-viewer.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/workspace-03-bewerken.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/workspace-04-converteren.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/workspace-05-controleren.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/workspace-06-pdf-tekening.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/workspace-07-scribing.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/workspace-08-bom-hoeveelheden.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/workspace-09-optimaliseren.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/workspace-10-productieworkflow.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/full_acceptance/screenshots/workspace-11-exporteren.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/PHASE_3_SHORT_SOAK_EVIDENCE.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/PHASE_3_SOURCE_TEST_EVIDENCE.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/VIEWER_V9_FULL_SMOKE_SUMMARY.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/analytic_fitting_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/canonical_rebuild_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/core_phase0_baseline_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/dimension_graph_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/edit_workspace_ui_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/full_acceptance_ifc_batch_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/full_acceptance_qt_progressive_exact_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/full_acceptance_qt_viewer_visual_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/ifc_semantic_import_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/manufacturing_contact_core_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/manufacturing_face_core_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/p21_graph_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/packaged_runtime_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/part_drawing_standard_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/part_workbench_roundtrip_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/part_workbench_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/part_workbench_ui_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/pdf_ai_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/pdf_review_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/phase1_context_job_contract_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/phase1_phase2_completion_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/phase1_phase2_context_e2e_gui_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/phase2_export_scope_matrix_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/phase2_m18_packaged_gate_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/phase2_manufacturing_e2e_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/phase2_manufacturing_persistence_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/phase2_plate_nesting_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/phase3_completion_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/phase3_quality_inspection_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/phase3_soak_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/phase3_visual_dpi_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/phase3_workspaces_gui_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/production_editor_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/production_export_negative_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/production_export_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/production_release_package_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/progressive_viewer_loading_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/project_baseline_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/project_bom_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/project_classification_reference_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/project_classification_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/project_cli_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/project_jobs_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/project_model_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/project_reference_files_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/project_semantic_reference_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/project_semantic_service_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/project_service_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/project_storage_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/reference_models_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/regression_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/review_workflow_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/source_geometry_resolution_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/steel_model_foundation_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/step_semantic_import_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/unified_manufacturing_scribing_u2_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/unified_production_workflow_u4_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/unified_project_schema_u1_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/unified_u4_gui_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/unified_ui_context_u3_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/unified_ui_shell_u3_gui_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/unified_viewer_v15_u3_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_ci_headless_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_contract_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_mesh_renderer_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_profile_proxy_visibility_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_project_adapter_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_runtime_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_coordination_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_export_center_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_feel_fix_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_identification_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_interaction_foundation_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_machine_capability_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_manufacturing_export_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_marking_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_navigation_contract_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_nesting_binding_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_neutral_job_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_phase2_parity_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_review_workspace_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_selection_measurement_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_selection_pivot_parity_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_trimble_feel_v2_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_trimble_input_contract_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v15_workspace_contract_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v1_decision_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v1_fixture_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v1_occt_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v1_qt_contract_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v1_vtk_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v2_core_controller_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v2_qt_contract_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v2_scene_index_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v2_validation_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v2_vtk_core_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v3_geometry_contract_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v3_project_catalog_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v3_project_scene_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v3_search_properties_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v3_vtk_real_mesh_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v4_color_accuracy_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v4_color_schemes_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v4_qt_contract_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v4_validation_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v4_vtk_controls_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v4_vtk_modes_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v4_windows_config_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v4_workspace_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v5_history_explode_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v5_measurements_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_ambiguity_identity_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_compare_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_contours_features_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_display_isolation_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_editor_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_exact_catalog_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_integration_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_main_app_controls_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_occt_exact_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_occt_selection_contract_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_qt_contract_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_review_store_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_roundtrip_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_scribing_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_snapping_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_tk_exact_integration_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_windows_config_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v6_workbench_gate_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v7_correspondence_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v7_deviation_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v7_exact_bundle_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v7_impact_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v7_manifest_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v7_project_revision_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v7_qt_contract_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v7_scribing_revalidation_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v7_view_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v7_windows_config_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v7_workspace_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v8_bridge_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v8_export_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v8_grid_query_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v8_layout_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v8_qt_contract_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v8_real_project_grid_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v8_windows_config_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v9_controller_rebind_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v9_display_tools_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v9_integration_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v9_launcher_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v9_measurement_export_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v9_packaging_config_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v9_qt_contract_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v9_reference_project_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v9_smoke_runner_reporting_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v9_workbench_persistence_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_v9_workspace_navigation_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_visual_geometry_regression_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/viewer_workspace_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/windows_installer_association_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/windows_native_runtime_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/phase3/source-smokes/logs/windows_release_config_smoke.log` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase2/fresh-cli.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase2/fresh-gui.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase2/one-folder-cli.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase2/one-folder-gui.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase2/phase2-fresh-portable-gui-smoke.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase2/phase2-fresh-portable-native-selftest.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase2/phase2-fresh-portable-packaged-runtime.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase2/phase2-one-folder-gui-smoke.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase2/phase2-one-folder-native-selftest.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase2/phase2-one-folder-packaged-runtime.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase2/standalone-create-project.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase2/standalone-gui-smoke.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase2/standalone-gui.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase3/phase3-dist-gui-smoke.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase3/phase3-dist-native-selftest.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase3/phase3-dist-packaged-runtime.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase3/phase3-installed-gui-smoke.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase3/phase3-installed-native-selftest.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase3/phase3-installed-packaged-runtime.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase3/phase3-portable-gui-smoke.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase3/phase3-portable-native-selftest.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase3/phase3-portable-packaged-runtime.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase3/phase3-standalone-gui-smoke.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/results/windows-runtime-phase3/phase3-standalone-native-selftest.json` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/run_all_smokes_v9.py` | ` M` | `COMMIT_REQUIRED` | Reproduceerbare acceptance/buildworkflow |
| `validation/unified/U2_MANUFACTURING_SCRIBING_STATUS.md` | ` M` | `REVIEW_REQUIRED` | Niet automatisch geclassificeerd |
| `validation/viewer_repair_diagnostic/all-default.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/all-fixed-colour.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/all-masking-off.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/all-technical.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/glyph-points-only.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/glyph-with-vertices.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/isolated-default.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/proxy-cleaned.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/proxy-normal32.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/proxy-raw32.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/proxy-raw64.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/proxy-triangulated.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/repository-v15-cockpit-before.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/single-direct.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/single-glyph.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/source-frame-after.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/source-frame-before.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/source-frame-final.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/source-window-after.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/source-window-before.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
| `validation/viewer_repair_diagnostic/source-window-final.png` | `!!` | `GENERATED_ARTIFACT_DO_NOT_COMMIT` | Door acceptance-runner reproduceerbare evidence |
