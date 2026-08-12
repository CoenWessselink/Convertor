# Levering CWS Convertor 0.6.0-beta en vervolg

## Wat deze levering bevat

- complete geïntegreerde broncode van het projectfundament;
- Canonical Project Model 2.0;
- draagbare `.cwscproj`-opslag met bronnen, previews, revisies en audit;
- deterministische IFC-/STEP-bronintake en routekeuze A/B/C;
- functioneel Project / Productie-tabblad;
- project-CLI en achtergrondjobservice;
- regressietests op één groot Tekla IFC2X3-model en drie echte AP242 STEP-bestanden;
- een echt voorbeeldproject met alle vier bronnen ingebed;
- validatierapport, ruwe meetresultaten, testlogs, screenshot en checksums;
- Windows buildconfiguratie, dependency locks en SPDX-SBOM.

## Releasebewijs

- phase-validation: 117/117 controles geslaagd;
- projecttests: 33/33 geslaagd;
- volledige beschikbare regressielog: `ALL TESTS PASSED`;
- `.cwscproj`-integriteit: manifest, SHA-256, CRC en SQLite `integrity_check` geslaagd;
- alle vier ingesloten bronnen zijn opnieuw geëxtraheerd en bytegelijk gecontroleerd;
- autosave en herstelproject zijn daadwerkelijk gemaakt en heropend;
- GUI is onder een virtueel scherm gestart en visueel vastgelegd.

## Niet als voltooid geclaimd

- volledige semantische populatie van het Tekla IFC-model;
- productieclassificatie en BOM uit complete modellen;
- per-part/per-merk productie-uitvoer;
- deduplicatie en revisievergelijking;
- optimalisatie, nesting, voorraad en machineaansturing;
- native Windows-binaries of een schone-machine-acceptatietest.

## Direct vervolg

De semantische importer moet eerst bewijzen dat IFC-relaties, placements, properties, materialen, bouten en lassen zonder verlies naar actieve ProjectModel-entiteiten worden overgezet. Daarna volgt STEP-product-/solidpopulatie, identiteit, classificatie en BOM. Machinefunctionaliteit blijft tot na deze poorten buiten scope.
