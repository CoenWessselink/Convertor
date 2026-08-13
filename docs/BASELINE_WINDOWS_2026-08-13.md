# Windows baseline v0.8.0-alpha-dev

Date: 2026-08-13  
Branch: `v0.8-codex-handover`  
Commit: `97d2b08c62ec2c7e10476884e4bbabcff22ea61f`  
Project Model schema: `2.3`

## Handover integrity

- Handover manifest verification: PASS, 315 files verified.
- Git bundle verification: PASS, complete history.
- ZIP SHA-256: `76063D483FD111B98227F04725B1ED9B7616DCFEC492A9207E308449728923E7`.
- Master prompt SHA-256: `2826B41FBB79EB1027B4ECEA7A4839054B39139DF5028C827A6703E8CC880E80`.
- The bundle checkout and active repository contain the same 202 tracked files after line-ending normalisation.

## Environment

- OS: Windows 10 Pro, build 26200, 64-bit.
- Python: CPython 3.12.0, 64-bit.
- `pip check`: PASS, no broken requirements.
- cadquery 2.8.0
- numpy 2.3.5
- PyMuPDF 1.26.7
- pypdf 5.9.0
- XlsxWriter 3.2.9
- reportlab 4.4.9
- ifcopenshell 0.8.5
- PyInstaller 6.15.0

The environment was installed from `requirements-runtime.lock.txt` and
`requirements-build.lock.txt` in a clean local `.venv`.

## Static verification

Command:

```powershell
.\.venv\Scripts\python.exe -m compileall -q -x "[\\/]\.venv[\\/]" .
```

Result: PASS.

## Smoke tests

All scripts were run independently against the active checkout. The packaged
`03_TEST_INPUTS/PROJECT_MODELS` directory was supplied through
`CWS_REFERENCE_ROOT`, so the large IFC and the three STEP reference tests were
executed instead of skipped.

| Script | Result | Seconds | Skipped tests |
| --- | --- | ---: | ---: |
| `analytic_fitting_smoke.py` | PASS | 1.669 | 0 |
| `dimension_graph_smoke.py` | PASS | 1.744 | 0 |
| `ifc_semantic_import_smoke.py` | PASS | 0.139 | 0 |
| `p21_graph_smoke.py` | PASS | 0.120 | 0 |
| `pdf_ai_smoke.py` | PASS | 2.934 | 0 |
| `pdf_review_smoke.py` | PASS | 2.168 | 2 |
| `production_export_negative_smoke.py` | PASS | 0.108 | 0 |
| `production_export_smoke.py` | PASS | 0.155 | 0 |
| `project_baseline_smoke.py` | PASS | 0.113 | 0 |
| `project_bom_smoke.py` | PASS | 0.179 | 0 |
| `project_classification_reference_smoke.py` | PASS | 0.113 | 3 |
| `project_classification_smoke.py` | PASS | 0.111 | 0 |
| `project_cli_smoke.py` | PASS | 1.790 | 0 |
| `project_jobs_smoke.py` | PASS | 0.140 | 0 |
| `project_model_smoke.py` | PASS | 0.120 | 0 |
| `project_reference_files_smoke.py` | PASS | 1.742 | 0 |
| `project_semantic_reference_smoke.py` | PASS | 12.544 | 0 |
| `project_semantic_service_smoke.py` | PASS | 1.653 | 0 |
| `project_service_smoke.py` | PASS | 0.322 | 0 |
| `project_storage_smoke.py` | PASS | 0.814 | 0 |
| `regression_smoke.py` | PASS | 2.254 | 0 |
| `review_workflow_smoke.py` | PASS | 1.688 | 0 |
| `step_semantic_import_smoke.py` | PASS | 1.581 | 0 |

Summary: 23/23 scripts passed, 0 failed, 5 individual tests skipped.

## Coverage gaps and discrepancies

- Two `pdf_review_smoke.py` tests were skipped because the test expects a real
  `P1811.nc1` at a legacy handover path that is not part of the active source
  checkout. Synthetic PDF review coverage did run.
- Three `project_classification_reference_smoke.py` tests were skipped because
  the handover does not contain the expected `.cwscproj` reference project.
- The code and handover status use Project Model schema `2.3`; parts of
  `README.md`, `docs/ARCHITECTURE_V0.7.md`, and
  `docs/CWSC_PROJECT_FORMAT.md` still describe the v0.7 schema `2.1` context.
- The Windows installer was not rebuilt during this baseline run.
- Production export remains intentionally blocked until Part Workbench feature
  validation and manufacturing data integrity checks are complete.
- Local confidential reference models remain outside Git and were not modified.
  Their expected results remain `manual_validation_required` until reliable
  values are supplied or independently established.

This report is the pre-feature baseline for the Part Workbench phase. A passing
script with skipped tests is not treated as complete coverage.
