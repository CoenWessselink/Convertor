# Part Workbench foundation

Status: eerste backend-fundering, niet de volledige Part Workbench-fase.  
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

`tests/part_workbench_smoke.py` dekt:

- rechte plaat met doorgaand gat;
- plaat met analytische boog;
- HEA/I-profiel en rondstaal D20 als ondersteunde vormen;
- negatieve geometrie-, feature-, confidence- en assenstelselgevallen;
- plaatsingsonafhankelijke en spiegelafhankelijke manufacturing identity;
- featurewijziging, artefactinvalidatie, undo en redo;
- audit, save/reopen en de stateless servicefacade.

## Nog niet gebouwd

- geintegreerde Workbench-GUI met projectboom, property grid en featuretabs;
- interactieve 3D-bron/canonical-vergelijking en 2D-tekening;
- automatische kandidaatherkenning vanuit echte BREP-geometrie;
- deterministische canonical-solid rebuild vanuit de Workbench-revisie;
- volledige canonical naar NC1/STEP/IFC/PDF naar canonical roundtrips;
- performance- en geheugentests voor interactieve bewerking van grote modellen;
- screenshots van de uiteindelijke Workbench-UI;
- vrijgave van productie-export;
- nieuwe Windows installer en test op een schone Windows x64-machine.

Productie-export blijft gesloten totdat deze resterende stappen per ondersteund
onderdeeltype aantoonbaar zijn gevalideerd.

## Windows-validatie 2026-08-13

- `compileall`: PASS;
- smoke-scripts: 25 uitgevoerd, 25 PASS, 0 FAIL;
- Part Workbench: 6 tests PASS;
- repository plus lokale referentiecatalogus: 481 modellen gekoppeld aan 481
  expected-results;
- inhoudelijk gevalideerde lokale golden baselines: 0;
- `manual_validation_required`: 481, bewust niet inhoudelijk vergeleken;
- bekende skips: 5, gelijk aan de pre-feature baseline.
- grootste verpakte STEP-referentie: 9.224.690 bytes, 3,586 seconden en
  175,535 MB peak working set; alle functionele en performancechecks PASS.

De twee PDF-skips missen het verwachte echte P1811-pad. De drie
classificatiereferentieskips missen het niet meegeleverde `.cwscproj`-project.
De grote verpakte IFC- en drie STEP-referentietests zijn wel uitgevoerd.
Het machineleesbare large-modelresultaat staat in
`validation/results/v08-large-step-windows.json` (SHA-256
`2A1C29FF48AD88930F5CA818BC3A77CA20EAB14F850F82C3739D2B86BDB9317F`).
