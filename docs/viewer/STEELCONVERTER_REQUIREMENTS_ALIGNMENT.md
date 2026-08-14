# SteelConverter-superprompt → CWS Convertor/CWS Viewer alignment

## Status

De op 13 augustus 2026 aangeleverde `STEELCONVERTER_SUPERPROMPT_MET_BIJLAGEN.zip` is als aanvullende productrequirement verwerkt. De tekst is ongewijzigd bewaard in:

- `docs/requirements/STEELCONVERTER_SUPERPROMPT.md`
- `docs/requirements/STEELCONVERTER_SUPERPROMPT_README.txt`
- `docs/requirements/STEELCONVERTER_CONCEPT_CONTACTSHEET.jpg`

Bronhashes:

- archive SHA-256: `737e411873b2c6f7e53e9aeda5e6b0732b4bbcf0a86c86edabf3722a44366f30`
- prompt SHA-256: `1d035e740bbf382325c5d972854e7d76a0a61d4e2499cafb38d1f64259e5bc73`
- contactsheet SHA-256: `e74edf1226725f27e6a3569a294b3025440d98841bdee1e4db40c53de4bd805e`

De 18 afbeeldingen zijn conceptuele UX- en functiereferenties. Zij zijn geen bewijs dat een functie technisch kan of moet worden geïmplementeerd; de geschreven requirements, veiligheidsregels en gevalideerde CWS-architectuur gaan voor.

## Terminologie en één waarheid

De superprompt gebruikt de naam **SteelConverter** en het model **SteelModel**. In deze repository blijven de geldende product- en modelnamen:

- product: **CWS Convertor**;
- viewermodule: **CWS Viewer**;
- centrale projectwaarheid: **Canonical Project Model**;
- centrale onderdeelwaarheid: **Canonical Part Model**.

`SteelModel` wordt daarom functioneel gemapt op het bestaande Canonical Project/Part Model. Er wordt geen tweede intern productiemodel geïntroduceerd.

## Bindende architectuurregels

De aanvullende prompt bevestigt en verscherpt de bestaande CWS-regels:

1. import- en vieweraccuracy vóór nieuwe productiefeatures;
2. displaymesh is afgeleid en nooit productiewaarheid;
3. source-ID → canonical entity-ID → scene node-ID → mesh-ID blijft traceerbaar;
4. onbekende gegevens blijven zichtbaar als REVIEW/BLOCKED;
5. originele bronbestanden worden niet overschreven;
6. productiegericht parametrisch bewerken, geen vrije CAD-modeler;
7. functies worden modulair toegevoegd rond één model;
8. rustige, contextuele UI met veel ruimte voor het model;
9. ieder gevonden geometrieprobleem wordt een permanente regression fixture;
10. geen vrijgaveclaim zonder meetbare resultaten en expliciete toleranties.

## Invloed op de viewerroadmap

### V4 — professionele bediening en Accuracy/Debug Mode

V4 omvat voortaan expliciet:

- render modes, kleurenschema's en achtergronden;
- transparency, hide/show/isolate/ghost;
- viewpoints en visibility sets;
- atomische, checksum-geverifieerde workspace persistence;
- Accuracy/Debug Mode met source/internal/scene/mesh-ID, units, transforms, bounding box, geometry hashes, mesh exactness, profile/material recognition en PASS/WARNING/FAIL;
- screenshots;
- geen technische hidden-line claim voordat hidden-line removal werkelijk is geïmplementeerd.

### V5 — sections en uitgebreide Measure-workspace

De eerdere basislijst wordt uitgebreid met:

- point-to-point;
- horizontale/verticale afstand;
- chain distance;
- point-to-object;
- driepunts- en lijn-/vlakhoek;
- slope/gradient;
- perpendicular check;
- radius/diameter;
- arc/chord length;
- center point;
- face/multiface/by-points/projected/surface area;
- object-/selectionvolume;
- count en groeperen op type/material/phase/bolts;
- total length/area/volume/weight/center of gravity;
- coordinate picker;
- endpoint/midpoint/center/perpendicular/intersection/nearest/node snaps;
- units, precisie, measurement list en export;
- stable anchors en invalidatie bij geometry-hashwijziging.

De compacte meetknoppen verschijnen contextueel zodat het 3D-model groot blijft.

### V6 — exact Part Workbench en scribing

V6 bevat nu een eerste exact-BREP scribingreviewmodule:

- contactlijnen/aansluitingen voorstellen via OCCT BREP-section;
- 3D-preview;
- confirm/reject/reset met audit;
- expliciet onderscheid scribe/mark versus cut;
- provenance/confidence;
- geen contact of multi-solid ambiguity leidt niet tot gegokte output;
- checksum-JSON voor latere gevalideerde DSTV/machine-adapters;
- geen machine- of productievrijgave vanuit de viewer.

### V8/V9 — grid en integratie

De professional property grid en hoofdapp-integratie moeten aansluiten op de conceptbeelden:

- draggable columns;
- sort/filter/group/field chooser;
- saved layouts;
- statuskleuren;
- compacte contexttools;
- linkse objecttree en rechter property/selection panel wanneer relevant;
- geen permanente overvolle toolbars.

## Wat niet uit de conceptbeelden wordt overgenomen

- logo's, iconen, huisstijl of assets van derden;
- inconsistente of visueel aantrekkelijke functies zonder technische specificatie;
- production-ready aanduidingen zonder gatebewijs;
- vrije solid modeling;
- proprietary Trimble-code of binaries;
- een tweede import- of cachewaarheid.

## Harde eerste mijlpaal

Conform de aanvullende prompt blijft de eerste viewer-/importmijlpaal:

- dezelfde bronmodellen reproduceerbaar laden;
- geen stil verdwenen objecten;
- correcte units en transforms;
- geometrie binnen vastgelegde toleranties;
- volledige ID-traceability;
- onbekende data zichtbaar;
- grote modellen stabiel;
- automatische regression suite;
- viewer betrouwbaar genoeg voor productieanalyse, maar nog niet zelf productievrijgevend.
