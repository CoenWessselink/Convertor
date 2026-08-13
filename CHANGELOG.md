# Changelog

## 0.8.0-alpha-dev - Part Workbench foundation

- Versioned Part Workbench state added with immutable source geometry references.
- Analytical part forms, production frame, reference sides, contours and features added.
- Field provenance, validation issues, audit, undo/redo and artifact invalidation added.
- Project Model schema raised to 2.4 with migration and save/reopen coverage.
- Integrated Part Workbench added to the existing Project / Productie screen.
- Synchronized part selection, sortable grid, property/validation panels and required detail tabs added.
- Source-envelope and analytical 3D/2D comparison added without claiming an exact source BREP.
- Plate bounding-box candidate and through-hole editing use one atomic service update.
- GUI regression covers start, apply, validate, undo and redo; release remains roundtrip-blocked.
- Windows build workflow now runs every `tests/*_smoke.py` file.
- Windows release configuration smoke prevents non-numeric Inno version metadata.
- Explicit reviewed length, plate thickness and diameter values added to Workbench revisions.
- Deterministic canonical-solid rebuild added for straight plates with inner contours and through holes, solid round bars and unworked exact catalogue profiles.
- Source comparison added for volume, area and bounding dimensions with tolerances, plus exact solid-count and validity checks.
- Missing or non-part-scoped source measurements now produce `manual_validation_required` instead of invented expectations.
- Hashed rebuild reports are persisted beside the revision and invalidated when the manufacturing hash changes.
- Canonical comparison tab added with expected, found, delta, result and blocking reason reporting.
- Six canonical rebuild regressions and updated GUI validation added; all 28 smoke scripts pass locally on Windows.
- Production release remains blocked pending exact source isolation and NC1/STEP/IFC/PDF roundtrip validation.
- Canonical builder loading is lazy so the packaged project CLI does not initialize CadQuery/CasADi for non-geometry commands.
- Native Windows workflow 31685684421 passed PyInstaller, Inno Setup, installed-app smoke without Python on PATH, project storage, uninstall, checksums and artifact upload.

## 0.7.0-alpha — Semantische IFC/STEP-projectimport

- Gedeelde, dependency-light ISO-10303-21-grafiekkern toegevoegd voor IFC en STEP.
- IFC2X3/IFC4 assemblies, parts, fasteners, lassen, placements, properties, materialen en relaties als actieve Project Model-entiteiten gematerialiseerd.
- STEP AP203/AP214/AP242 product definitions, occurrences, placements en BREP-roots gematerialiseerd zonder fictieve opsplitsing.
- Stabiele bron-ID, geometry hash en manufacturing hash per onderdeel toegevoegd en over opslaan/herimport getest.
- Semantische import transactioneel gemaakt met bronhashcontrole, bronpurge en rollback bij fouten.
- Project Model opgehoogd naar schema 2.1 en projecthashing geoptimaliseerd voor grote modellen.
- `.cwscproj`-manifest uitgebreid met semantic, content, revision-content en manufacturing-state hashes.
- CLI-opdrachten `project-import`, `project-tree`, `project-list-parts` en `project-list-assemblies` toegevoegd.
- Project/Productie-GUI uitgebreid met echte semantische import, interne voortgang en materialisatiecounts.
- Tekla-referentie gematerialiseerd als 353 assemblies, 2.429 parts, 723 fasteners en 2.654 lassen.
- Drie echte AP242 STEP-referenties elk als precies één product/solid/part geïmporteerd.
- Productiegate bewust gesloten gehouden tot classificatie, featureherkenning en roundtripvalidatie.
- Windows-buildstraat en installerconfiguratie bijgewerkt naar 0.7.0-alpha.
- STEP-route `C_fused_review` toegevoegd voor bronnen zonder betrouwbare solid-root; er wordt geen geometrie, occurrence, assembly of opsplitsing verzonnen.
- Coöperatief annuleren toegevoegd aan Part 21-parser, importers, projectservice en GUI, met volledige transactionele rollback.
- Canonical JSON-hashing en grote-projectopslag versneld zonder het bestaande hashcontract te wijzigen.
- Vrijgavevalidatie uitgebreid naar 82/82 controles; referentiematerialisatie 14,20 s en geverifieerd opslaan/openen 13,01 s in de huidige Linuxomgeving.

## 0.6.0-beta — Project Foundation

- Productnaam en zichtbare distributie hernoemd naar **CWS Convertor**.
- Centrale product- en versieconstanten toegevoegd.
- Canonical Project Model 2.0 toegevoegd met project-, assembly-, part-, inkoop-, fastener-, weld-, voorraad-, operatie- en machine-entiteiten.
- Stabiele bronidentiteit, placement-onafhankelijke geometry hash en manufacturing hash toegevoegd.
- Draagbaar `.cwscproj`-formaat gebouwd op ZIP + SQLite met manifest, SHA-256, CRC, integriteitscontrole en veilige extractie.
- Projectpreviews worden hash-gecontroleerd bewaard bij openen/opslaan, autosaveherstel en pakketmigratie.
- Atomisch opslaan, backups, revisies, auditlog, lichtgewicht autosave, herstel en read-only/migratieroute toegevoegd.
- Deterministische IFC/STEP-nulmeting en selectie van importstrategie A/B/C toegevoegd.
- Productiepoort toegevoegd: complete-model-export blijft geblokkeerd zolang semantische import/validatie niet is afgerond.
- Functioneel **Project / Productie**-tabblad toegevoegd.
- Project-CLI toegevoegd voor maken, importnulmeting, informatie, bronnen, verificatie, JSON-export, extractie, herstel en migratie.
- Annuleerbare achtergrondjobmanager toegevoegd.
- Regressietests toegevoegd voor model, opslag, baseline, CLI, jobs, service en de vier echte referentiemodellen.
- Windows PyInstaller/Inno Setup-build hernoemd en uitgebreid met projecttests, `.cwscproj`-associatie en installatiesmoke.
- Reproduceerbare directe dependency locks en SPDX-SBOM toegevoegd.
- Bestaande NC1/STEP/IFC/PDF-kern en legacy payloadcompatibiliteit behouden.
- Project Foundation-validatie: 117/117 controles geslaagd op het Tekla IFC-model en drie AP242 STEP-modellen.

## 0.5.1 — PDF review en maatgrafiek

- Deterministische feature-gekoppelde maatgrafiek toegevoegd.
- Interactieve PDF-review met bronbewijs, correcties, bevestigingen en audit toegevoegd.
- Begrensde AI-laag voor semantische voorstellen geïntegreerd.
- Trusted Converter PDF en synthetische LO4-keten uitgebreid en getest.

## 0.5.0 — Trusted PDF en AI-fundament

- Trusted Converter PDF met embedded canoniek model en hashes toegevoegd.
- Externe vector-PDF-analyse en veilige reviewbasis toegevoegd.

## 0.4.0 — Canonieke IFC-roundtrip

- Canoniek onderdeelmodel en lossless converter-eigen IFC-payload toegevoegd.
- Focusroundtrips voor NC1/STEP/IFC hersteld.
