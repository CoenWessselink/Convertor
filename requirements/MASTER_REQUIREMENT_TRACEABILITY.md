# CWS Convertor Master Requirement Traceability

Generated: `2026-08-31T21:29:57.003175+00:00`

Active requirements: **317**

## Status

| Status | Count |
|---|---:|
| NOT_TESTED | 317 |

## Requirement sources

- `CODEX_SUPERPROMPT_CWS_CONVERTOR_100PCT_FINAL_4_FASEN_2026-08-31.md`: PRESENT
- `CODEX_SUPERPROMPT_CWS_CONVERTOR_UNIFIED_3_FASEN_2026-08-27.md`: PRESENT
- `CODEX_SUPERPROMPT_CWS_COMPLETION_100PCT_3_FASEN_2026-08-28.md`: PRESENT
- `CODEX_SUPERPROMPT_CWS_FULL_PRODUCT_ACCEPTANCE_TEST_2026-08-28.md`: PRESENT
- `CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md`: PRESENT
- `CODEX_SUPERPROMPT_CWS_UI_MASTER_V5_COMPLETE_3_FASEN_2026-08-31.md`: PRESENT
- `CODEX_SUPERPROMPT_CWS_UI_MASTER_V5_1_FINAL_3_FASEN_2026-08-31.md`: PRESENT
- `CODEX_SUPERPROMPT_CWS_UI_CONTROLS_VISUAL_FIDELITY_V5_1_2026-08-31.md`: PRESENT
- `CODEX_SUPERPROMPT_CWS_UI_V5_2_CONTROL_BUILD_3_FASEN_2026-08-31.md`: PRESENT
- `CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md`: PRESENT
- `CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md`: PRESENT
- `CODEX_SUPERPROMPT_CWS_MANUFACTURING_GEOMETRY_INTERPRETER_V2_3_FASEN_2026-08-31.md`: PRESENT
- `CWS_CONVERTOR_COMPLETE_GAP_ANALYSIS_2026-08-31.md`: PRESENT
- `CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json`: PRESENT

## Core product requirements

| ID | Phase | Status | Requirement |
|---|---:|---|---|
| F1-001 | 1 | NOT_TESTED | All active requirement sources are versioned and reconciled without silent deletion |
| F1-002 | 1 | NOT_TESTED | Canonical product authorities remain unique and no parallel Viewer/Project/BOM engines are introduced |
| F1-003 | 1 | NOT_TESTED | IFC geometry uses a bounded persistent process worker pool with recovery and clean shutdown |
| F1-004 | 1 | NOT_TESTED | Geometry priority is dynamic, viewport-aware, hysteretic and starvation-safe |
| F1-005 | 1 | NOT_TESTED | MeshCache V2 persists complete mesh payloads atomically and rejects corruption |
| F1-006 | 1 | NOT_TESTED | Scene uploads are generation-safe and bounded by per-frame time budgets |
| F1-007 | 1 | NOT_TESTED | ViewerPerformanceGovernor controls interaction, recovery and idle rendering quality including MSAA |
| F1-008 | 1 | NOT_TESTED | Packaged cold, warm and same-session metrics include first usable, exact milestones, p95/p99 and memory/process counts |
| F1-009 | 1 | NOT_TESTED | A real ten-minute OpenGL Viewer soak proves bounded actors, workers and memory |
| F1-010 | 1 | NOT_TESTED | Viewer interaction, selection, visibility, section, measurement and saved-view behavior remains functional |
| F1-011 | 1 | NOT_TESTED | Unified intake handles IFC, STEP, NC1, Trusted PDF, External PDF and project packages fail-closed |
| F1-012 | 1 | NOT_TESTED | Project state and user preferences are versioned, separated and recover safely |
| F1-013 | 1 | NOT_TESTED | The exact primary navigation is Project, Viewer, Productie, Controle, Uitvoer |
| F1-014 | 1 | NOT_TESTED | V5.2 design system is light-first with a dark preference smoke path and yellow whole-object selection |
| F1-015 | 1 | NOT_TESTED | Owned controls use stable ui_test_id identity and central control/icon registries |
| F2-001 | 2 | NOT_TESTED | BOM is the immutable quantity truth with exact reconciliation and full traceability |
| F2-002 | 2 | NOT_TESTED | BOM and Machines joins production state through canonical IDs |
| F2-003 | 2 | NOT_TESTED | Machine routing has one versioned AUTO/MANUAL assignment authority |
| F2-004 | 2 | NOT_TESTED | Invalid machine overrides remain REVIEW/BLOCKED and never authorize transfer |
| F2-005 | 2 | NOT_TESTED | Machine library validates ranges, tools, operations, priorities and active state |
| F2-006 | 2 | NOT_TESTED | Workbench remains the single transactional write path with rollback and undo/redo |
| F2-007 | 2 | NOT_TESTED | Canonical rebuild and roundtrip invalidate stale derivatives |
| F2-008 | 2 | NOT_TESTED | Manufacturing Geometry Interpreter V2 uses source topology, hypotheses and independent reconstruction |
| F2-009 | 2 | NOT_TESTED | Interpreter exact READY requires two-way BREP proof and false READY remains zero |
| F2-010 | 2 | NOT_TESTED | Existing faces, contact, scribing, identification, capability and neutral-job chain remains authoritative |
| F2-011 | 2 | NOT_TESTED | Profile nesting preserves machine/tool/stock/remnant constraints and deterministic proof |
| F2-012 | 2 | NOT_TESTED | Plate nesting supports polygon geometry, holes, grain, rotations, remnants, locks and exact validation |
| F2-013 | 2 | NOT_TESTED | Converter capability registry blocks every feature not proven by serializer and reimport comparator |
| F2-014 | 2 | NOT_TESTED | Productie screens and controls operate on the same canonical project and selection |
| F2-015 | 2 | NOT_TESTED | Routing, nesting and production state survive save and reopen |
| F3-001 | 3 | NOT_TESTED | One production drawing engine emits vector geometry, dimensions, annotations and title blocks |
| F3-002 | 3 | NOT_TESTED | Production drawing PDF remains sharp at 800 percent and is not a full-page raster |
| F3-003 | 3 | NOT_TESTED | Drawing linter blocks incomplete, stale, clipped or raster-only production pages |
| F3-004 | 3 | NOT_TESTED | Trusted PDF payload and hash verification fails closed on tamper |
| F3-005 | 3 | NOT_TESTED | External PDF remains evidence/confidence gated and REVIEW_REQUIRED until proven |
| F3-006 | 3 | NOT_TESTED | One DocumentOutputService owns preview, print and batch output |
| F3-007 | 3 | NOT_TESTED | Ctrl+P opens the context Print Center and printer failure is fail-closed |
| F3-008 | 3 | NOT_TESTED | Controle exposes validation, compare, manufacturability, geometry, evidence and PDF review |
| F3-009 | 3 | NOT_TESTED | Problem Center reports blockers, errors and warnings without false green |
| F3-010 | 3 | NOT_TESTED | Quality inspection supports plans, measurements, NCR, rework, reinspection and release blocking |
| F3-011 | 3 | NOT_TESTED | Planning owns resources, work centers, shifts, requirements, orders and scheduled operations |
| F3-012 | 3 | NOT_TESTED | Finite-capacity scheduling respects availability, maintenance, material, priority and due dates |
| F3-013 | 3 | NOT_TESTED | Shopfloor transitions and quality hooks remain bounded and auditable |
| F3-014 | 3 | NOT_TESTED | Export uses Scope to Formats to Preflight to Generate to Verify to Package without scope broadening |
| F3-015 | 3 | NOT_TESTED | Readiness joins geometry, manufacturing, routing, nesting, drawing, quality and planning gates |
| F3-016 | 3 | NOT_TESTED | All 25 reference and 6 support surfaces are functional in the real Qt runtime |
| F4-001 | 4 | NOT_TESTED | Dynamic full acceptance is generated from this master traceability |
| F4-002 | 4 | NOT_TESTED | Runtime owned-control scan proves no missing, duplicate, dead or wrong-handler controls |
| F4-003 | 4 | NOT_TESTED | Visual acceptance covers required resolutions and DPI with light primary and dark smoke |
| F4-004 | 4 | NOT_TESTED | Full IFC, STEP, NC1, Trusted PDF and External PDF workflows are tested end to end |
| F4-005 | 4 | NOT_TESTED | Negative file, cache, worker, cancellation, stale-state and capacity paths fail closed |
| F4-006 | 4 | NOT_TESTED | Stress suite proves bounded workspace, selection, camera, save, import/export and optimization behavior |
| F4-007 | 4 | NOT_TESTED | Final Viewer cold/warm/same-session, interaction and resource metrics are packaged evidence |
| F4-008 | 4 | NOT_TESTED | One-folder black-box runtime works without developer Python PATH |
| F4-009 | 4 | NOT_TESTED | Fresh portable black-box runtime works without developer Python PATH |
| F4-010 | 4 | NOT_TESTED | Fresh installer black-box runtime works and preserves file associations |
| F4-011 | 4 | NOT_TESTED | Source zip, git bundle, checksums, SBOM and manifests bind to one exact source SHA |
| F4-012 | 4 | NOT_TESTED | Required FAIL, BLOCKED and NOT_TESTED counts are zero with false green zero |
| F4-013 | 4 | NOT_TESTED | Physical machine transfer remains blocked pending external qualification |
| F4-014 | 4 | NOT_TESTED | Release evidence and binaries are rebuilt after every code change and name the exact SHA |
