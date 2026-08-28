# CWS Convertor technical guide

## Canonical architecture

`CWSMainWindow` composes one `UnifiedApplicationContext`, `WorkspaceRouter`, `JobManager` and permanent Viewer host. `ProjectModel 2.25` and `Canonical Part 1.1` are the persistence authorities. Workbench commands, canonical rebuild, independent validation and roundtrip validation are the only production edit path.

Manufacturing uses canonical faces, contacts, marks, production-instance identity, nesting bindings, an operation DAG and a neutral manufacturing job. Export is scope-first and fail-closed. Quality uses `cws-quality-ledger-1.0`, binding inspection plans, measurements, NCR/rework, certificates and approvals to a release hash.

## Evidence hierarchy

- Phase checklists: `validation/phases/PHASE_N_CHECKLIST.json` and `.md`.
- Source gates: `PHASE_N_SOURCE_TEST_EVIDENCE.json`.
- Windows gates: `PHASE_N_WINDOWS_RUNTIME_EVIDENCE.json`.
- Exact prompt mapping: `ALL_PROMPTS_TRACEABILITY.json`.
- Final artifacts and hashes: `release/phase3/PHASE_3_RELEASE_MANIFEST.json` and `SHA256SUMS.txt`.

## Packaging

The canonical distribution remains one-folder because Qt, VTK, OCCT, IfcOpenShell and solver native libraries are runtime dependencies. The final GUI convenience executable is additionally built as a true PyInstaller one-file bundle and tested in an empty directory. The CLI remains part of the complete one-folder/portable/installed runtime.

## Safety

`machine_observed_by_cws`, `deployment_transport_authorized`, `direct_machine_transfer` and `machine_transfer.allowed` remain false. No software-only test qualifies a physical machine, controller, firmware or tooling combination.
