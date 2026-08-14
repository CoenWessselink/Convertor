# CWS Viewer ProjectScene 1.0

`ProjectScene` is een immutable, renderer-onafhankelijk readmodel. Het is geen
tweede Canonical Project Model en bevat geen productiegeometrische waarheid.

## Identiteit

- `node_id`: stabiele viewer/scene-ID;
- `entity_id`: stabiele CWS Project Model-ID;
- `source_entity_id`: herkomst in IFC/STEP;
- `geometry_id`: afgeleid display-/exact-geometryresource;
- `geometry_hash` en `manufacturing_hash`: overgenomen CWS-identiteit.

Triangle- of rendererhandles mogen nooit buiten de backend duurzaam worden
opgeslagen.

## Geometrie

Payloads worden via URI-handles doorgegeven:

- `project://...` voor CWS read services;
- `cache://...` voor content-addressed derived cache;
- `memory://...` voor tests;
- `file://...` alleen via gecontroleerde resolver.

SHA-256 en optionele bytegrootte worden vóór gebruik gecontroleerd. De scene
accepteert analytisch/BREP/mesh/point-cloud als representation, maar V0 bouwt
alleen deferred handles.

## Validatie

- future major schema wordt geweigerd;
- dubbele stable IDs worden geweigerd;
- ontbrekende parents, geometry en styles worden geweigerd;
- parentcycli worden geweigerd;
- transforms moeten finite, affine, niet-singulier en rechtsgeldig zijn;
- payloadpadtraversal wordt geweigerd;
- `scene_hash` is deterministisch en verplicht.

De formele JSON Schema staat in:

`cws_viewer/schemas/project-scene-1.0.schema.json`.
