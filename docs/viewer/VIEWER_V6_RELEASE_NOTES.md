# CWS Viewer Core 0.7.0-dev0 — V6 Exact Part Workbench

## Nieuw

- exact STEP/BREP-catalogus met stabiele face-/edge-/vertex-ID's;
- native OCCT/AIS source/canonical overlay en exact subshape picking;
- analytische lijn-, cirkel-, boog- en cilinderevidence;
- rechterhandig productieframe en reference-face review;
- exact snapping;
- deterministische source/canonical compare;
- displaytessellatie op een kopie;
- begrensde plate/hole-editor met audit en undo/redo;
- `.cwspartreview.json` met checksum;
- ronde gaten, echte radii, sleufgat en polylinecontour;
- P1811- en asymmetrische-plaatroundtrips via STEP, NC1, IFC en Trusted PDF;
- format-specifieke gates;
- exacte BREP-scribingvoorstellen met review/audit en 3D-preview;
- V6 packaged/native Windows selftest en workflow.

## Beveiliging

- multi-solid/fused bron blijft blocked;
- gewijzigd gat wordt door geometry- en featuregate geblokkeerd;
- displayproxy/displaymesh is geen productie-evidence;
- scribing verandert geen productiegeometrie en is geen snijbewerking;
- viewer kan geen productie-PDF of machine-output vrijgeven;
- unsupported feature mag niet verdwijnen of als geslaagd worden gemarkeerd.

## Open

- exact IFC per-part BREP extraction uit complete projecten;
- volledige profielrebuild;
- algemene pockets/notches/chamfers/end cuts;
- V7 compare/revision workspace en robuustere subshape-correspondentie;
- gevalideerde DSTV-/machineadapter voor scribing;
- Windows packaged en portable bewijs.
