# Changelog

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
