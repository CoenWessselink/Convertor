# CODEX QUEUE MASTER

Generated from `bcb2c874aedbd03eb6ff180773ceb4a2fd0a54b1` on branch `agent/cws-product-ui-reintegration-v1`. This ledger never converts missing external evidence into PASS.

| ID | Queue item | Dependencies | Status | Remaining |
|---|---|---|---|---|
| Q001 | Canonical repository, requirement sources and authority reconciliation | - | PASS | None |
| Q002 | Viewer Loader Engine V2 and cold-load performance closeout | Q001 | PARTIAL | HVPC first-cold exact load is 7.939 seconds and still exceeds the 3-5 second target; warm load is 0.075 seconds. Exact interactive rendering is 20.39 FPS / 50.66 ms p95 and does not meet the 30 FPS gate. |
| Q003 | HVPC exact object and geometry completeness | Q001 | PASS | None |
| Q004 | Same-machine Trimble visual and object parity | Q002, Q003 | BLOCKED_EXTERNAL_EVIDENCE | Fresh desktop capture/control is blocked by Windows Graphics Capture access/monitor errors; no fabricated visual comparison is accepted. |
| Q005 | V5.2 light UI and reference-image visual fidelity | Q001 | PARTIAL | All 31 native HVPC-populated surfaces and all 25 supplied reference pairs are captured, but pixel-level SSOT fidelity remains HUMAN_REVIEW_REQUIRED and the native VTK child needs separate framebuffer evidence. |
| Q006 | Production core, BOM, machines, workbench, nesting and converter | Q001 | PASS | None |
| Q007 | Manufacturing Geometry Interpreter V2 independent proof | Q006 | PASS | None |
| Q008 | Drawings, PDF, Print Center, Controle, Quality, Planning and Uitvoer | Q006 | PASS | None |
| Q009 | Fresh-checkout source and clean-runtime reproducibility | Q001 | PASS | None |
| Q010 | Dynamic total product acceptance | Q002, Q003, Q005, Q006, Q007, Q008, Q009 | FAIL | Master traceability contains 26 FAIL requirements. |
| Q011 | Exact-SHA one-folder, portable and installer release | Q010 | FAIL | Phase 4 gate and final Windows release are not PASS. |
| Q012 | Queue audit, resumable state and automatic continuation | Q001 | PASS | None |

Current technically logical non-PASS: **Q002**.
