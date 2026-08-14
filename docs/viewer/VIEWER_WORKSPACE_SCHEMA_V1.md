# CWS Viewer workspace schema 1.0

## Doel

Een `.cwsview.json` bewaart uitsluitend display- en reviewstate:

- camera/projectie;
- selectie;
- hide/show/isolate/ghost;
- transparantie en kleurassignments;
- render mode, kleurenschema en achtergrond;
- section/clippingstate zodra V5 die activeert;
- viewpoints;
- visibility sets;
- Accuracy/Debug Mode.

Het bestand bevat nooit canonical geometry, manufacturing readiness of een productie-vrijgavebesluit.

## Integriteit

- deterministische `state_hash` over de inhoud;
- extern SHA-256-sidecarbestand;
- atomisch schrijven via tijdelijk bestand en `os.replace`;
- maximaal 32 MiB;
- unsupported future major schema wordt geweigerd;
- project-ID moet exact overeenkomen;
- scenehash moet exact overeenkomen, tenzij de gebruiker expliciet een veilige subset-restore van dezelfde projectrevisielijn toestaat;
- niet-bestaande node-ID's worden gerapporteerd als `dropped_node_ids`, niet stil hergebruikt.

## Scheiding van waarheid

De workspace is een viewersetting. Een kleur, verborgen object, bookmark of Accuracy-paneel verandert nooit:

- geometry hash;
- manufacturing hash;
- profiel/materiaal;
- features;
- export gate;
- productieartefact.

Machineleesbaar schema: `cws_viewer/schemas/viewer-workspace-1.0.schema.json`.
