# Manufacturing Geometry Interpreter Closeout

Status: `PASS`

Queue item: `Q007`

## Acceptance

- Full interpreter corpus: 11 exact fixtures, 3 rigid/mirror transforms and 3 negative cases.
- Corpus gates: 13/13 `PASS`.
- False-ready count: 0.
- Additional manufacturing tests: 44 passed, 0 failed.
- Fase 1 scenario smoke: `PASS`.
- Fase 2 end-to-end and persistence: `PASS`.
- Unified manufacturing/scribing, Viewer V15 export and workbench roundtrip: `PASS`.

## Repair

- Circular and annular sections now obtain their exact diameter from the outer circular edge radius. Their previous start/end-point metric collapsed to zero.
- HEA, HEB and IPE corpus fixtures have identical synthetic geometry. The acceptance corpus now uses an explicit preferred designation to disambiguate them while the production recognizer remains fail-closed.

## Runtime image evidence

- `validation/manufacturing_workspace/machine_settings_workspace.png`
- `validation/manufacturing_workspace/profile_nesting_miter_interlock.png`
- `validation/manufacturing_workspace/plate_nesting_stock_layout.png`

## External evidence outside Q007

The separate vendor-machine XML roundtrip fixture points to `C:/Users/c.wesselink/Desktop/VB1250 Zaag - V631 Boor.xml`. That file is absent from the canonical repository, Downloads and Codex attachments, so that one workspace fixture remains `BLOCKED_EXTERNAL_EVIDENCE`. It is not an interpreter corpus requirement and is not counted as a Q007 pass.
