# Part Workbench foundation

Status: geintegreerde Workbench plus eerste deterministic canonical rebuildlaag;
niet de volledige Part Workbench- of roundtripfase.

Project Model: `2.4`

Workbench-schema: `1.0`

## Gebouwd

- onveranderlijke verwijzing naar bronbestand en brongeometrie;
- bewerkbare analytische partrevisie met revisiesnapshots;
- gevalideerd rechterhandig lokaal productieframe;
- bevestigbare referentiezijden;
- outer/inner-contouren met lijn- en boogsegmenten;
- holes, slots, pockets, radii, arcs, chamfers en end cuts als featuretypen;
- veldprovenance met confidence, reviewer en tijdstip;
- blokkerende vragen en validatie-issues;
- gehasht commandolog met undo/redo en audit-events;
- review/validated/released-statussen;
- automatische herberekening van geometry/manufacturing hashes;
- invalidatie van afgeleide artefacten na een manufacturing-wijziging;
- opslag en heropening in `.cwscproj`;
- stateful `ProjectSession`- en stateless `ProjectService`-API's.
- expliciete lengte-, plaatdikte- en diameterwaarden in de werkrevisie;
- canonical solids voor rechte platen met binnencontouren en doorgaande gaten;
- canonical solids voor massief rond en exacte onbewerkte catalogusprofielen;
- vergelijking van volume, oppervlakte en bbox met tolerantie;
- exacte vergelijking van solidcount en geometrische geldigheid;
- gehasht rebuildrapport met manufacturing-hashkoppeling en invalidatie;
- geintegreerde UI met een afzonderlijk canonical vergelijkingstabblad.

## Harde controles

De fundering blokkeert of weigert onder meer:

- onbekende of ambigue onderdeelvorm;
- lage, onbevestigde herkenningsconfidence;
- linkshandige, geschaalde of scheve productie-assen;
- onbekende of onbevestigde referentiezijde;
- open of onderbroken contour;
- dubbel gat of gat buiten een rechte plaatcontour;
- niet-ondersteunde feature;
- onopgeloste blokkerende productievraag;
- gewijzigde brongeometriehash of corrupte commando-/revisiehash.

## Regressiedekking

`tests/part_workbench_smoke.py` en `tests/canonical_rebuild_smoke.py` dekken:

- rechte plaat met doorgaand gat;
- plaat met analytische boog;
- HEA/I-profiel en rondstaal D20 als ondersteunde vormen;
- negatieve geometrie-, feature-, confidence- en assenstelselgevallen;
- plaatsingsonafhankelijke en spiegelafhankelijke manufacturing identity;
- featurewijziging, artefactinvalidatie, undo en redo;
- audit, save/reopen en de stateless servicefacade.
- deterministische herhaalde rebuild en stabiele rapporthash;
- exact verwachte en gevonden meetwaarden voor een synthetische testplaat;
- afwijkingen, tolerantie en vermoedelijke oorzaak per eigenschap;
- `manual_validation_required` bij ontbrekende of niet-geisoleerde bronmetingen;
- automatische invalidatie bij wijziging van maakafmetingen;
- solid round bar en exacte `HEA240`-catalogusopbouw.

## Nog niet gebouwd

- automatische kandidaatherkenning vanuit echte BREP-geometrie;
- exacte source-BREP-isolatie en mesh/topologievergelijking per geselecteerd part;
- canonical rebuild van boogcontouren, custom doorsneden en profielbewerkingen;
- directe featurehighlighting tussen grids, 2D en 3D;
- volledige canonical naar NC1/STEP/IFC/PDF naar canonical roundtrips;
- performance- en geheugentests voor interactieve bewerking van grote modellen;
- vrijgave van productie-export;
- nieuwe Windows installer van deze wijziging en test op een schone Windows x64-machine.

Productie-export blijft gesloten totdat deze resterende stappen per ondersteund
onderdeeltype aantoonbaar zijn gevalideerd.

## Windows-validatie 2026-08-13

- `compileall`: PASS;
- smoke-scripts: 28 uitgevoerd, 28 PASS, 0 FAIL;
- Part Workbench: 6 tests PASS;
- canonical rebuild: 6 tests PASS;
- repository plus lokale referentiecatalogus: 481 modellen gekoppeld aan 481
  expected-results;
- inhoudelijk gevalideerde lokale golden baselines: 0;
- `manual_validation_required`: 481, bewust niet inhoudelijk vergeleken;
- bekende optionele fixture-skips: 9.
- grootste verpakte STEP-referentie: 9.224.690 bytes, 3,586 seconden en
  175,535 MB peak working set; alle functionele en performancechecks PASS.

De skips betreffen niet meegeleverde PDF-, classificatie- en grote semantische
referentiefixtures. De afzonderlijke large-modelvalidatie uit de vorige stabiele
Windows-ronde blijft als onafhankelijk bewijs bewaard.
Het machineleesbare large-modelresultaat staat in
`validation/results/v08-large-step-windows.json` (SHA-256
`2A1C29FF48AD88930F5CA818BC3A77CA20EAB14F850F82C3739D2B86BDB9317F`).

De canonical rebuild-evidence staat in
`validation/results/v08-canonical-rebuild-windows.json`. De bijbehorende
Windows-screenshot staat in
`validation/results/v08-canonical-rebuild-ui-windows.png`. De gebruikte plaat is
synthetisch en niet vertrouwelijk; dit resultaat valideert geen aangeleverd
referentiemodel en verhoogt de golden-baselinecount daarom niet.
