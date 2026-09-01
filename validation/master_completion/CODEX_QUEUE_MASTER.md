# CODEX QUEUE MASTER

Generated from `9ed87cb4da73e3f893f69e875422d09cb02d01a4` on branch `agent/cws-product-ui-reintegration-v1`. This ledger never converts missing external evidence into PASS.

| ID | Queue item | Dependencies | Status | Remaining |
|---|---|---|---|---|
| Q001 | Canonical repository, requirement sources and authority reconciliation | - | PASS | None |
| Q002 | Viewer Loader Engine V2 and cold-load performance closeout | Q001 | PARTIAL | A genuinely cacheless first IFC tessellation is 7.939 seconds and still exceeds the 3-5 second target. The checksum-bound exact warmstart is PASS at 3.264 seconds and native interaction is PASS at 28.85 ms p95. |
| Q003 | HVPC exact object and geometry completeness | Q001 | PASS | None |
| Q004 | Same-machine Trimble visual and object parity | Q002, Q003 | BLOCKED_EXTERNAL_EVIDENCE | Fresh desktop capture/control is blocked by Windows Graphics Capture access/monitor errors; no fabricated visual comparison is accepted. |
| Q005 | V5.2 light UI and reference-image visual fidelity | Q001 | PARTIAL | All 31 native HVPC-populated surfaces, all 25 supplied reference pairs and a native exact VTK framebuffer are captured; pixel-level SSOT fidelity remains HUMAN_REVIEW_REQUIRED. |
| Q006 | Production core, BOM, machines, workbench, nesting and converter | Q001 | PASS | None |
| Q007 | Manufacturing Geometry Interpreter V2 independent proof | Q006 | PASS | None |
| Q008 | Drawings, PDF, Print Center, Controle, Quality, Planning and Uitvoer | Q006 | PASS | None |
| Q009 | Fresh-checkout source and clean-runtime reproducibility | Q001 | PASS | None |
| Q010 | Dynamic total product acceptance | Q002, Q003, Q005, Q006, Q007, Q008, Q009 | FAIL | Master traceability contains 26 FAIL requirements. |
| Q011 | Exact-SHA one-folder, portable and installer release | Q010 | FAIL | Phase 4 gate and final Windows release are not PASS. |
| Q012 | Queue audit, resumable state and automatic continuation | Q001 | PASS | None |

Current technically logical non-PASS: **Q002**.
