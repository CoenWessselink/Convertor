# CWS Convertor — Codex handover status

## Snapshot identity

- Product: **CWS Convertor**
- Integration snapshot: **0.8.0-alpha-dev**
- Project Model schema: **2.3**
- Git branch: `v0.8-codex-handover`
- Based on verified history through tag `v0.7.0-alpha`
- Added overlays:
  - v0.7 classification/BOM draft
  - v0.8 production-package export draft

This is a development handover, not a production release. No Windows installer has been built or clean-machine tested in this environment.

## What was reconstructed

The previously announced v0.8 handover archive was not present in the runtime and its upload failed. This snapshot was reconstructed transparently from:

1. the actual v0.7 Git bundle and full v0.7 source;
2. the physically present v0.7 classification/BOM overlay files;
3. the physically present v0.8 production-export overlay files;
4. small integration repairs required to import and test the merged tree.

## Integration repairs made for this handover

- central version changed to `0.8.0-alpha-dev`;
- Project Model version reconciled to schema `2.3`;
- missing `cws_convertor.production_export.utils` added;
- production-export public API completed;
- dataclass field-name collision in `production_export.models` fixed;
- BOM public API added;
- circular BOM/project-service imports changed to lazy imports;
- exact version/schema assertions in the integrated tests updated.

These repairs are committed separately so Codex can inspect them.

## Verified in the reconstructed tree

The following test scripts ran successfully in this environment:

- `analytic_fitting_smoke.py`
- `dimension_graph_smoke.py`
- `ifc_semantic_import_smoke.py`
- `p21_graph_smoke.py`
- `pdf_ai_smoke.py`
- `pdf_review_smoke.py` (2 real-file tests skipped because the binary fixture was not mounted)
- `production_export_smoke.py`
- `production_export_negative_smoke.py`
- `project_baseline_smoke.py`
- `project_bom_smoke.py`
- `project_classification_smoke.py`
- `project_classification_reference_smoke.py`
- `project_cli_smoke.py`
- `project_jobs_smoke.py`
- `project_model_smoke.py`
- `project_reference_files_smoke.py`
- `project_semantic_reference_smoke.py`
- `project_semantic_service_smoke.py`
- `project_service_smoke.py`
- `project_storage_smoke.py`
- `regression_smoke.py`
- `review_workflow_smoke.py`
- `step_semantic_import_smoke.py`

## Current functional boundary

Present:

- NC1/DSTV ↔ STEP regression core;
- converter-owned IFC exact payload roundtrip;
- Trusted Converter PDF and guarded external vector-PDF review foundation;
- semantic IFC/STEP project import;
- Project Model and `.cwscproj` storage;
- deterministic classification and BOM draft;
- guarded per-part/per-mark package export draft;
- GUI/CLI foundations.

Not yet complete:

- Part Workbench for local axes, reference faces, contours, holes and production-feature review;
- reliable general external IFC/STEP-solid → complete canonical manufacturing model;
- complete technical part/assembly drawings;
- real LO4 PDF binary regression in this runtime;
- revision comparison UI;
- cutting-stock optimization, plate nesting, stock, machines and postprocessors;
- native Windows installer and clean Windows test;
- full production release.

## Mandatory next phase

Build the **Part Workbench** before optimization or machine work. It must let a user inspect and correct one imported part, define local production axes and reference faces, edit analytical contours and holes, preserve provenance/audit/undo-redo, validate canonical roundtrips, and only then unlock the existing production-package exporter.
