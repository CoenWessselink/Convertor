# Complete Codex prompt — CWS Convertor continuation

## Role

You are the primary senior software engineer responsible for taking over and completing **CWS Convertor**. Work in the supplied repository. Do not replace the existing converter with a new mock-up, demo, dashboard-only implementation, or a separate greenfield application.

## Start here

Read in this exact order:

1. `docs/CODEX_HANDOVER_STATUS.md`
2. `docs/NEXT_PHASE_PART_WORKBENCH.md`
3. this complete prompt
4. `README.md`
5. `docs/ARCHITECTURE_V0.7.md`
6. `docs/CWSC_PROJECT_FORMAT.md`
7. `cws_convertor/product.py`
8. `cws_convertor/project/model.py`
9. `cws_convertor/project/service.py`
10. semantic importers under `cws_convertor/importers/`
11. classification/BOM under `cws_convertor/project/classification.py` and `cws_convertor/bom/`
12. production package export under `cws_convertor/production_export/`
13. all tests before changing code.

The handover archive also contains the untouched v0.7 base source and the two physical overlay trees. Use these only for forensic comparison. The active starting point is the Git branch `v0.8-codex-handover` or the corresponding integrated worktree.

## Current technical identity

- Product name: **CWS Convertor**
- Development snapshot: `0.8.2-alpha-dev`
- Canonical Project Model schema: `2.3`
- Stable Git history exists through `v0.7.0-alpha`
- The handover integration commit merges classification/BOM and production-package export drafts and fixes their immediate import defects.

This is not yet a production release. Do not claim that the installer, arbitrary external IFC/STEP → NC1, full drawings, optimization, or machine output are complete unless you implement and test them.

## First mandatory action: establish a reproducible baseline

Before feature work:

1. Verify the handover manifest and SHA-256 checksums.
2. Inspect `git status`, branches, tags and last commits.
3. Create a clean Python 3.12 development environment.
4. Install dependencies from the repository lock/requirements files.
5. Run `python -m compileall`.
6. Run every smoke test and record pass/fail/skip with exact commands, platform and dependency versions.
7. Set `CWS_REFERENCE_ROOT` to the supplied `reference_inputs` directory for real IFC/STEP tests.
8. Do not weaken tests or tolerances to force green output.
9. Commit the baseline report before starting the next phase.

## Immediate development objective

Build **CWS Convertor Part Workbench** as the next phase. This must close the gap between semantic project import and safe production export.

### Required outcome

A user can select an imported IFC/STEP part, isolate it, define or correct local production axes and reference faces, review/edit analytical contours and features, rebuild a deterministic canonical solid, compare that canonical solid with the source, save all corrections with provenance/audit/undo-redo, and unlock only those export formats whose validation gates pass.

### Mandatory Part Workbench scope

- local right-handed production coordinate system;
- reference side/face selection;
- plate/profile identification and confirmation;
- analytical outer and inner contours;
- lines, arcs, circles and radii without coarse polygon substitution;
- holes, slots, pockets, notches, chamfers and supported end operations;
- feature side/orientation;
- material, profile, quantity, mark and assembly relation;
- field-level provenance and confidence;
- explicit unresolved questions;
- review status and authorized release;
- deterministic geometry rebuild;
- source-vs-canonical comparison for volume, area, bounding dimensions, topology and features;
- NC1/STEP/IFC/PDF roundtrip validation;
- manufacturing hash recalculation and invalidation of dependent outputs;
- save/reopen in `.cwscproj` without loss.

### UI requirements

Integrate into the existing application. The product must remain **CWS Convertor**.

Create a visually attractive industrial desktop interface with:

- project tree and part list;
- a modern, high-density property grid with draggable columns, sorting, grouping, field chooser, saved layouts and export;
- synchronized 3D source/canonical comparison;
- tabs for General, Extra information, Operations, Angles/Contours, Holes, Codes/Marks, Prices, Operation times, Provenance/Validation;
- scroll zoom, pan, orbit, fit, standard views, isolate, transparency and comparison modes;
- 2D analytical feature preview;
- direct selection/highlighting between grid, feature table, 2D and 3D views;
- green validated, orange review, red blocked and blue active selection;
- background jobs, progress and cancellation;
- undo/redo and audit trail;
- no visual mock-up without functional backing code.

Use the supplied UI reference document to understand the required feature tabs and sortable property list, but redesign it coherently for CWS Convertor rather than copying an old application pixel-for-pixel.

### AI rules

AI may assist with:

- classification;
- interpreting labels, metadata, title blocks and drawing semantics;
- suggesting profile/material aliases;
- detecting conflicts and generating review questions;
- suggesting views and layout.

AI may never directly generate or silently alter:

- NC1/DSTV lines;
- exact coordinates;
- canonical production contours;
- STEP/IFC BREP geometry;
- machine code;
- production release status.

All exact geometry and export must be deterministic and validated. Cloud AI must be optional, require explicit consent, use no retention where supported, and have an audit log. Local-first operation is mandatory.

## Safety and architecture rules

1. Maintain one canonical truth for parts and projects.
2. Preserve the existing NC1 ↔ STEP regression core.
3. Preserve converter-owned IFC exact payload roundtrips.
4. Do not turn analytical circles/cylinders/arcs into coarse meshes when exact definitions are known.
5. Do not fabricate a STEP assembly tree.
6. Do not split a fused solid based only on its filename.
7. Keep confidence separate from geometric proof.
8. Block production when critical data are missing, conflicting or unsupported.
9. Never bypass strict validation in production CLI or GUI paths.
10. Keep review documents clearly separate from released production documents.
11. Every artifact must be traceable to project, part, revision, source entity and hash.
12. All file writes and package exports must be atomic and checksum-verified.
13. Make migrations explicit and reject unsupported future schemas.
14. Maintain transactional project operations and rollback on cancellation/failure.
15. Do not build optimization or machine control before the Part Workbench and production-feature validation are reliable.

## Required regression data

Use all supplied legacy NC1/STEP focus and complete datasets plus:

- the Tekla IFC model;
- `Samenstel nieuw - 11864_Predeterminado (1).step`;
- `Samenstel nieuw - 11881_Predeterminado (1).step`;
- `Samenstel nieuw - 2x voetplaat hoog.step`.

The real binary `Pos LO4 - LOSSE PLAAT.pdf` is not embedded in this runtime package. Its expected fields and prior synthetic fixture are present. Request/add the original PDF before claiming the true LO4 binary regression complete.

The older master requirements also name `Samenstel nieuw - D1500-0190_Predeterminado (1).step` and `Staalconstructie bordes c04 - Part 18.step`. They were not available as binary files in this runtime handover. Do not substitute different files silently; add them when supplied and retain the stated one-product/one-solid expectations.

## Acceptance tests for the immediate phase

At minimum add and pass:

1. plate with straight contour and through holes;
2. plate with true arcs/radii;
3. I/HEA profile;
4. D20 round bar;
5. ambiguous/fused solid remains blocked;
6. right-handed-axis validation and left-handed rejection;
7. reference-face confirmation;
8. hole inside/outside/duplicate validation;
9. contour closure/self-intersection validation;
10. source placement change does not change manufacturing identity;
11. material/profile/feature/mirror change does change manufacturing identity where required;
12. undo/redo and audit persistence;
13. project save/reopen preserves canonical edits;
14. format-specific gate behavior;
15. canonical → NC1 → canonical comparison;
16. canonical → STEP → canonical comparison;
17. canonical → IFC → canonical comparison;
18. canonical → Trusted PDF → canonical comparison;
19. unsupported feature cannot disappear silently;
20. all old regression tests continue to pass.

Report per real test part:

- part/profile/material;
- contour count and analytical segment types;
- holes and dimensions;
- local axes/reference sides;
- volume, area and principal dimensions;
- source/canonical deltas;
- roundtrip deltas;
- gate decision and exact blocking codes.

## Windows distribution requirement

The final end user must not need Python, pip, a virtual environment or terminal commands.

Eventually deliver:

- one Windows x64 installer EXE;
- bundled Python runtime and dependencies;
- portable ZIP;
- file associations;
- uninstaller;
- code signing when available;
- SHA-256 checksums and SBOM;
- clean Windows x64 installation/start/CLI/uninstall test with no Python installed.

Do not claim this complete until the actual Windows artifacts exist and the clean-machine test has been run.

## Working protocol

For every phase:

1. inspect first;
2. write/update tests before or with code;
3. implement in small coherent commits;
4. run the relevant focused tests after each change;
5. run the full baseline before release;
6. verify generated ZIPs/checksums;
7. update architecture, status, migration and user docs;
8. provide an honest completed/not-completed table;
9. never report a generated file unless it physically exists and its checksum was verified.

## Required phase deliverables

- complete integrated source;
- Git commits/tags or a bundle;
- migration notes;
- automated tests and fixtures;
- actual test logs and machine-readable results;
- running GUI screenshot(s);
- sample project and review/output package;
- updated user/technical docs;
- checksums and SBOM;
- explicit remaining limitations.

---

# Full product requirements

The following is the full supplied product master prompt. It remains binding unless the more specific current-state safety instructions above are stricter.

# Masterprompt — AI-ondersteunde PDF-, NC1-, IFC- en STEP-converter met automatische werktekeningen

## 1. Rol en opdracht

Neem het bestaande project **NC1 ↔ STEP ↔ IFC Converter** over en breid het product uit met een volledige, bidirectionele tekeningenmodule. Bouw geen losstaand proefproject en vervang de bestaande werkende conversiekern niet. Integreer de nieuwe functionaliteit in hetzelfde canonieke onderdeelmodel, dezelfde profielendatabase, dezelfde materiaalbibliotheek, dezelfde validatielaag, dezelfde viewer, GUI, CLI en Windows-installer.

De applicatie moet twee hoofdrichtingen ondersteunen:

1. **Technische PDF/tekening → NC1/DSTV, IFC en STEP**
2. **NC1/DSTV, IFC en STEP → technische PDF/werkplaatstekening**

De PDF-functionaliteit moet AI-ondersteund zijn, maar de uiteindelijke geometrie, maatvoering, hoeveelheden en productie-export moeten deterministisch worden berekend en gevalideerd. Een taal- of visionmodel mag nooit rechtstreeks ongecontroleerde NC1-regels of productiegeometrie genereren.

Werk zelfstandig door tot een aantoonbaar werkende release. Maak geen claims zonder tests op echte bestanden.

---

## 2. Projectcontext en referentietekening

Gebruik de meegeleverde tekening `Pos LO4 - LOSSE PLAAT.pdf` als functionele en visuele referentie voor een losse onderdelentekening.

De voorbeeldtekening bevat onder meer:

- een losse plaat/strip als primair onderdeel;
- een maatgevoerde hoofdprojectie;
- positie-/onderdeelnummer `LO4`;
- profiel `STRIP5*120`;
- materiaal `S235JR`;
- lengte `160`;
- aantal `4`;
- merk `MLO4`;
- totaalaantal `4`;
- één gat met aanduiding `1*Ø14`;
- twee contourradii `R 13,5`;
- maatketens en totale afmetingen;
- schaal `1:2`;
- A4-formaat;
- een titelblok met project, opdrachtgever, onderwerp, datum, tekenaar en tekeninggegevens;
- een stukregel met de kolommen Pos, Profiel, Materiaal, Lengte, Aantal en Merk.

Gebruik niet automatisch de bedrijfsnaam, projectnaam of vormgeving van deze referentie als universele standaard. Maak de titelblok- en huisstijlvelden configureerbaar per bedrijf. Gebruik de referentie vooral om de gewenste informatiedichtheid, leesbaarheid, maatvoering, onderdeeltabel en bladindeling te begrijpen.

---

## 3. Niet-onderhandelbare ontwerpprincipes

### 3.1 Eén canoniek intern onderdeelmodel

Alle importers en exporters moeten via één canoniek intern model lopen:

```text
PDF / NC1 / IFC / STEP
        ↓
Canonical Part Model
        ↓
NC1 / IFC / STEP / PDF / Excel
```

Gebruik geen afzonderlijke, onderling afwijkende geometrische waarheid per bestandsformaat.

### 3.2 AI interpreteert; geometriekern rekent

Gebruik AI voor:

- documentclassificatie;
- titelblok- en tabelinterpretatie;
- herkenning van aanzichten;
- semantische koppeling van maatvoering aan geometrie;
- herkenning van profielbenamingen, materiaalteksten en symbolen;
- conflictdetectie en het formuleren van gerichte controlevragen;
- automatische bladindeling en maatplaatsing als voorstel.

Gebruik deterministische software voor:

- exacte geometrie;
- coördinaten;
- profielopbouw;
- gaten, uitsparingen, radii, bogen en afschuiningen;
- volume, oppervlak, massa en hoeveelheden;
- NC1/DSTV-serialisatie;
- IFC- en STEP-geometrie;
- projecties, zichtbare lijnen en verborgen lijnen;
- maatwaarden;
- roundtripvergelijkingen en exportvrijgave.

### 3.3 Geen stilzwijgend gokken

Kritische ontbrekende of tegenstrijdige gegevens mogen niet worden verzonnen. Bij onzekerheid moet de applicatie:

1. het betreffende element markeren;
2. de waarschijnlijke interpretaties tonen;
3. een confidence-score geven;
4. een concrete vraag aan de gebruiker stellen;
5. productie-export blokkeren totdat het probleem is bevestigd.

### 3.4 Veiligheidscontrole behouden

Behoud de bestaande strikte geometrische veiligheidscontrole. Een bestand mag niet als succesvol worden geëxporteerd wanneer profiel, contouren, gaten, hoofdmaten, volume of kritische metadata buiten de ingestelde toleranties afwijken.

### 3.5 Twee typen PDF onderscheiden

Maak een expliciet onderscheid tussen:

- **Trusted Converter PDF**: een PDF die door deze applicatie zelf is gemaakt en exacte machineleesbare modeldata bevat;
- **External Drawing PDF**: een externe vector-PDF, scan of foto zonder gegarandeerde exacte data.

Een Trusted Converter PDF moet vrijwel lossless opnieuw naar NC1, IFC en STEP kunnen worden geconverteerd. Een externe PDF vereist AI-herkenning en gebruikerscontrole.

---

## 4. Ondersteunde conversierichtingen

Ondersteun minimaal:

```text
PDF  → NC1/DSTV
PDF  → IFC
PDF  → STEP

NC1/DSTV → PDF
IFC       → PDF
STEP      → PDF
```

Behoud daarnaast de bestaande richtingen:

```text
NC1/DSTV ↔ STEP
NC1/DSTV ↔ IFC
IFC ↔ STEP
IFC/STEP → Excel
```

Ondersteun batchverwerking en meerdere onderdelen per IFC of PDF-set.

---

## 5. Canonical Part Model

Ontwerp een versieerbaar intern model met minimaal de volgende gegevens.

### 5.1 Identiteit en herkomst

- schema-versie;
- onderdeel-ID;
- positie;
- merk;
- projectnummer;
- ordernummer;
- assembly-ID;
- bronbestand;
- bronformaat;
- bronhash;
- importdatum;
- importmethode: exact, vector, OCR, AI of handmatig;
- provenance per veld;
- confidence per veld;
- gebruiker die een interpretatie heeft bevestigd.

### 5.2 Productgegevens

- onderdeelnaam;
- aantal;
- materiaalcode;
- materiaalkwaliteit;
- dichtheid;
- coating/oppervlaktebehandeling;
- profielcategorie;
- profielserie;
- profielbenaming;
- profielstandaard;
- lengte;
- plaatdikte;
- hoofdafmetingen;
- massa per stuk;
- totale massa;
- oppervlakte per stuk;
- totaal oppervlak.

### 5.3 Geometrie

- lokale rechterhandige assen;
- exacte BREP-/solidrepresentatie;
- analytische lijnen, cirkels, cilinders, bogen en vlakken;
- buitencontouren;
- binnencontouren;
- profieldoorsnede;
- uiteinden;
- gaten;
- sleufgaten;
- pockets;
- inkepingen;
- kopbewerkingen;
- afschuiningen;
- laskanten;
- markeringen;
- referentiezijden;
- toleranties.

### 5.4 Tekeninggegevens

- beschikbare aanzichten;
- projectierichting;
- view bounding boxes;
- schaal;
- maatobjecten;
- maatketens;
- annotations;
- symbolen;
- opmerkingen;
- titelblokvelden;
- revisies;
- bladformaat;
- bladnummer;
- templates en huisstijl.

### 5.5 Validatiegegevens

- warnings;
- errors;
- unresolved questions;
- geometrische vergelijking;
- featurevergelijking;
- exportstatus;
- vrijgavegebruiker;
- vrijgavedatum.

---

## 6. Trusted Converter PDF: exacte roundtrip mogelijk maken

Wanneer het programma zelf een PDF maakt, voeg dan naast de zichtbare tekening een machineleesbare laag toe.

### 6.1 In te sluiten data

Neem minimaal op:

- het volledige canonieke onderdeelmodel als versieerbare JSON;
- schema-versie;
- bronhash;
- geometriehash;
- profiel-ID;
- materiaal-ID;
- eenheden;
- onderdeel-ID;
- lijst met features;
- alle relevante oorspronkelijke metadata;
- hash van de zichtbare tekening;
- softwareversie.

### 6.2 Technische opslag in PDF

Gebruik bij voorkeur meerdere mechanismen:

- een embedded/associated file, bijvoorbeeld `converter-model.json`;
- XMP-metadata met schema-versie, part-ID en hashes;
- optioneel de originele bron als ingesloten bestand;
- optioneel een QR-code of compacte identifier die naar een lokaal/online jobrecord verwijst;
- vectorgeometrie in de PDF, geen gerasterde hoofdtekening.

### 6.3 Importprioriteit

Bij PDF-import:

1. controleer of embedded converterdata aanwezig is;
2. valideer schema en hashes;
3. bouw het onderdeelmodel exact uit de embedded data;
4. vergelijk de embedded data met de zichtbare tekening;
5. gebruik AI alleen voor ontbrekende of beschadigde delen.

Markeer zo'n import als `trusted_exact` wanneer alle controles slagen.

---

## 7. External Drawing PDF → NC1, IFC en STEP

Bouw een robuuste hybride importpipeline.

### 7.1 Invoertypen

Ondersteun:

- vector-PDF uit Tekla, AutoCAD, Advance Steel, Revit of andere CAD-software;
- hybride PDF met vectorlijnen en rasterafbeeldingen;
- gescande technische tekening;
- foto van een tekening als conceptmodus;
- enkelvoudige en meervoudige pagina's;
- één onderdeel per blad en meerdere onderdelen per blad;
- losse onderdelentekeningen en, later, eenvoudige samenstellingstekeningen.

### 7.2 Eerste classificatie

Bepaal per pagina:

- vector, raster of hybride;
- taal;
- eenheden;
- bladformaat;
- oriëntatie;
- schaal;
- tekeningtype;
- titelbloklocatie;
- stuklijstlocatie;
- aantal vermoedelijke onderdelen;
- aanwezige aanzichten;
- kwaliteitsscore.

### 7.3 Vectorextractie

Bij vector-PDF:

- lees lijnen, polylijnen, bogen, Bézierpaden, cirkels, tekst, lijnstijlen, kleuren en lagen uit;
- behoud exacte PDF-coördinaten;
- onderscheid geometrie, maatlijnen, hulplijnen, hartlijnen, verborgen lijnen, kaders en titelblokken;
- groepeer segmenten tot contouren;
- vereenvoudig collineaire segmenten;
- pas cirkel- en boogfitting toe waar tekenpaden gefragmenteerd zijn.

### 7.4 Raster- en scananalyse

Bij scans:

- deskew;
- perspectiefcorrectie;
- ruisonderdrukking;
- lokale contrastcorrectie;
- lijn- en boogdetectie;
- OCR met behoud van bounding boxes;
- herkenning van diameter-, radius-, hoek-, las- en tolerantie-symbolen;
- confidence per herkend teken.

OCR mag alleen tekst voorstellen. De maatwaarde moet vervolgens geometrisch aan de juiste maatlijn en feature worden gekoppeld.

### 7.5 Titelblok en tabellen

Herken en structureer:

- project;
- werk;
- opdrachtgever;
- onderwerp;
- tekeningnummer;
- positie;
- merk;
- profiel;
- materiaal;
- lengte;
- aantal;
- totaal aantal;
- schaal;
- datum;
- tekenaar;
- revisie;
- status;
- algemene notities;
- lasnotities;
- materiaalnotities.

Ondersteun bedrijfsspecifieke titelblokken via configureerbare templates.

### 7.6 Aanzichtherkenning

Detecteer en classificeer:

- vooraanzicht;
- bovenaanzicht;
- onderaanzicht;
- linker-/rechterzijaanzicht;
- doorsnede;
- detailaanzicht;
- isometrisch aanzicht;
- profieldoorsnede.

Koppel aanzichten aan elkaar op basis van orthografische uitlijning, maatvoering, hartlijnen en herkenbare features.

### 7.7 Dimension graph

Bouw een semantische maatgrafiek:

- maatwaarde;
- eenheid;
- tekstpositie;
- maatlijn;
- hulplijnen;
- begin- en eindanker;
- bijbehorende feature;
- maatsoort: lineair, hoek, radius, diameter, booglengte, hoogte, coördinaat;
- tolerantie;
- bronaanzicht;
- confidence.

Controleer maatketens:

- totaalmaten versus deelmaten;
- dubbele maten;
- tegenstrijdige maten;
- ontbrekende ankermaten;
- schaalmaat versus geschreven maat;
- relatieve versus absolute maatvoering.

Geschreven maatwaarden hebben bij externe PDF's in beginsel voorrang boven gemeten papierschaal, maar alleen wanneer de maatkoppeling betrouwbaar is.

### 7.8 Featureherkenning

Herken minimaal:

- buitencontour;
- binnencontour;
- ronde gaten;
- sleufgaten;
- rechthoekige uitsparingen;
- radii;
- afgeronde hoeken;
- inkepingen;
- kopuitsparingen;
- afschuiningen;
- verzinkingen;
- tapgaten;
- referentie- en hartlijnen;
- markeringen;
- profielzijde.

Verbind dezelfde feature over meerdere aanzichten.

### 7.9 Profielherkenning

Gebruik de profielendatabase om:

- expliciete profielteksten direct te mappen;
- profielen op gemeten doorsnede te herkennen;
- toleranties toe te passen;
- alternatieve matches te tonen;
- confidence te berekenen.

Voorbeeld:

```text
Tekst: HEA140
Geometrische match: HEA140
Confidence: 100%
Status: bevestigd
```

of:

```text
Gemeten h: 179,8 mm
Gemeten b: 70,2 mm
Gemeten tw: 6,4 mm
Beste match: UPN180
Confidence: 86%
Actie: gebruiker moet bevestigen
```

### 7.10 Interactieve correctie

Toon links de bron-PDF en rechts de gereconstrueerde 2D/3D-geometrie.

Gebruiker moet kunnen:

- lijnen opnieuw classificeren;
- maatteksten aan andere features koppelen;
- contourpunten verslepen of numeriek aanpassen;
- profiel kiezen;
- materiaal kiezen;
- eenheden en schaal corrigeren;
- aanzichttype corrigeren;
- ontbrekende maten invullen;
- onjuiste AI-herkenning afwijzen;
- wijzigingen als bedrijfstemplate opslaan.

### 7.11 Exportstatussen

Gebruik minimaal:

- **Groen — gevalideerd**: alle kritische gegevens bevestigd;
- **Oranje — handmatige controle vereist**: export als concept mogelijk, productie-export geblokkeerd;
- **Rood — onvoldoende bepaald**: geen NC1/IFC/STEP-productie-export.

---

## 8. PDF → NC1/DSTV

### 8.1 Vereiste gegevens

Voor NC1-export moeten minimaal bekend zijn:

- onderdeel-ID/positie;
- profiel of plaatgeometrie;
- lengte;
- eenheden;
- lokale oriëntatie;
- materiaal of expliciete gebruikerskeuze;
- gesloten buitencontour;
- gaten en uitsparingen;
- referentiezijden;
- aantal;
- kritische toleranties.

### 8.2 Schrijfwijze

Schrijf NC1 vanuit het canonieke model, niet vanuit vrije AI-tekst.

Ondersteun relevante DSTV-blokken en profielzijden. Schrijf compacte contouren:

- collineaire punten samenvoegen;
- echte bogen als bogen opslaan waar het formaat dit ondersteunt;
- cirkels niet als honderden segmenten schrijven;
- dubbele features verwijderen;
- consistente lokale assen gebruiken.

### 8.3 Veiligheidsroundtrip

Voer vóór vrijgave uit:

```text
Canonical Model → NC1 → opnieuw inlezen → reconstructie
```

Vergelijk:

- profiel;
- lengte;
- buitencontour;
- binnencontouren;
- gaten;
- gatdiameters;
- gatposities;
- zijden;
- volume;
- oppervlak;
- hoofdmaten;
- materiaal;
- aantal;
- onderdeelnummer.

Blokkeer export bij kritische afwijkingen.

---

## 9. PDF → STEP

Maak een echte CAD-solid/BREP, geen STL of uitsluitend triangulated mesh.

Vereisten:

- analytische vlakken, cirkels, cilinders en bogen behouden;
- profiel uit database exact opbouwen;
- features als echte booleaanse bewerkingen modelleren;
- lokale productiecoördinaten consistent toepassen;
- part name, material, mark en projectmetadata opnemen waar STEP-variant dit ondersteunt;
- exportcontrole uitvoeren door STEP opnieuw in te lezen en geometrisch te vergelijken.

---

## 10. PDF → IFC

Maak semantische IFC-objecten en geen generiek meshobject wanneer een betere mapping mogelijk is.

Gebruik waar passend:

- IfcPlate;
- IfcBeam;
- IfcColumn;
- IfcMember;
- IfcBuildingElementProxy alleen als fallback.

Voeg toe:

- GlobalId;
- Name;
- Tag/mark;
- materiaal;
- profiel/type;
- hoeveelheid;
- project/assemblyrelaties;
- Qto-hoeveelheden;
- propertysets;
- bron-PDF en confidence-informatie;
- exacte converterpayload in een eigen propertyset of associated document;
- schema-versie en hashes.

Gebruik analytische of gesweepte geometrie waar mogelijk. Vermijd onnodige triangulatie.

---

## 11. NC1, IFC en STEP → technische PDF

### 11.1 Doel

Genereer automatisch een leesbare, vectoriële werkplaats-/onderdelentekening met maatvoering, aantallen, materiaaleigenschappen, titelblok en relevante aanzichten.

### 11.2 Geometrieanalyse

Bij import:

- herken onderdeeltype;
- bepaal lokale hoofdassen;
- herken profiel en lengte;
- identificeer gaten, contouren, uitsparingen, radii, afschuiningen en uiteinden;
- lees materiaal, onderdeelnummer, mark, aantal en projectmetadata;
- bereken volume, oppervlak en massa;
- bepaal welke aanzichten nodig zijn.

### 11.3 Aanzichtkeuze

Genereer afhankelijk van onderdeeltype:

#### Plaat
- primair vooraanzicht loodrecht op plaatvlak;
- boven- of zijaanzicht om dikte te tonen wanneer relevant;
- detail- of doorsnedeaanzicht voor verzinking, pocket of laskant;
- isometrisch alleen wanneer dit extra begrip geeft.

#### I-, U-, L-, T- of kokerprofiel
- hoofdaanzicht langs de lengte;
- bovenaanzicht;
- zijaanzicht;
- eind-/doorsnedeaanzicht;
- detailaanzichten voor complexe kopbewerkingen;
- optioneel isometrisch overzicht.

#### Rondstaal of buis
- lengteaanduiding;
- eindaanzicht met diameter en wanddikte;
- doorsnede indien nodig;
- gat- en contourdetails.

Onderdruk redundante aanzichten. Voeg geen bovenaanzicht toe wanneer dit exact dezelfde informatie geeft en de tekening daardoor onnodig druk wordt. Voeg het juist wel toe wanneer dikte, profielzijde of bewerking anders niet eenduidig is.

### 11.4 Projecties

Gebruik echte geometrische projecties:

- zichtbare randen;
- verborgen randen als configureerbare streeplijnen;
- hartlijnen;
- symmetrieassen;
- snijlijnen;
- detailverwijzingen;
- lijngewichten per functie.

De tekening moet vectorieel blijven zodat inzoomen scherp blijft.

### 11.5 Automatische maatvoering

Genereer minimaal:

- totale lengte;
- totale breedte;
- totale hoogte;
- plaatdikte;
- profielbenaming;
- gatdiameters;
- gatposities vanaf stabiele referentieranden of assen;
- steekmaten;
- radii;
- hoeken;
- uitsparingsmaten;
- eindbewerkingsmaten;
- profielzijde indien relevant;
- aantallen identieke features, bijvoorbeeld `4× Ø18`;
- toleranties indien bekend.

Regels:

- geef niet dezelfde maat onnodig meerdere keren;
- dimensioneer vanaf stabiele productiereferenties;
- vermijd gesloten/overbepaalde maatketens tenzij als controlemaat gemarkeerd;
- plaats maten buiten de contour waar mogelijk;
- voorkom overlap van tekst, maatlijnen en geometrie;
- groepeer gatpatronen logisch;
- gebruik detailaanzichten wanneer maatvoering anders onleesbaar wordt;
- toon eenheden en decimale precisie volgens bedrijfsinstellingen;
- markeer afgeleide of niet-bevestigde maten op concepttekeningen.

### 11.6 Stukregel en hoeveelheden

Maak een tabel met minimaal:

- Pos;
- Profiel;
- Materiaal;
- Lengte;
- Aantal;
- Merk.

Optioneel configureerbaar:

- massa per stuk;
- totale massa;
- oppervlakte;
- coating;
- revisie;
- assembly;
- zaaglengte;
- opmerkingen.

Toon daarnaast het totaal aantal keer uit te voeren.

Bij IFC met meerdere onderdelen:

- maak optioneel één PDF per onderdeel;
- maak optioneel een gecombineerde PDF-set;
- maak een inhoudsopgave;
- maak een totale stuklijst en hoeveelhedenstaat;
- groepeer identieke onderdelen op profiel, geometrie en materiaal.

### 11.7 Titelblok

Ondersteun configureerbare velden:

- bedrijfslogo;
- project;
- werk;
- opdrachtgever;
- onderwerp;
- tekeningnummer;
- positie;
- status;
- formaat;
- schaal;
- datum;
- getekend door;
- gecontroleerd door;
- revisie;
- projectie-symbool;
- algemene materiaalnotities;
- algemene lasnotities;
- softwareversie;
- bronbestand.

Maak templates per bedrijf en per bladformaat.

### 11.8 Bladformaat en schaal

Ondersteun minimaal A4, A3, A2 en A1, liggend en staand.

Kies automatisch de grootste praktische schaal waarbij:

- geometrie en maatvoering volledig op het blad passen;
- teksthoogte leesbaar blijft;
- titelblok en tabellen niet worden overlapt;
- details voldoende ruimte krijgen.

Laat de gebruiker schaal en formaat forceren. Toon een waarschuwing wanneer het gekozen formaat onleesbaar wordt.

### 11.9 Automatische layout met AI

AI mag voorstellen:

- welke aanzichten worden opgenomen;
- waar aanzichten worden geplaatst;
- welke details apart worden uitvergroot;
- welke maatketens logisch zijn;
- waar maattekst het best past;
- welk bladformaat passend is.

Daarna moet een deterministische layoutengine:

- overlap controleren;
- minimale afstanden handhaven;
- view- en maatbounding boxes berekenen;
- tekstbotsingen oplossen;
- views op raster uitlijnen;
- titelblokruimte reserveren;
- een reproduceerbare PDF maken.

### 11.10 Tekeningstatus

Ondersteun:

- concept;
- ter controle;
- vrijgegeven;
- vervallen.

Concepttekeningen met onopgeloste gegevens moeten zichtbaar een status/watermerk krijgen en mogen niet stilzwijgend als productie-vrijgegeven worden geëxporteerd.

---

## 12. Review- en vergelijkingsinterface

Voeg een tabblad **PDF / Tekening** toe.

### 12.1 PDF → model

Links:

- bron-PDF;
- pan en scrollzoom;
- pagina's;
- laagfilters;
- OCR-/vectoroverlay;
- herkende titelblokken, tabellen, maatlijnen en aanzichten.

Rechts:

- 2D-reconstructie;
- 3D-model;
- profielweergave;
- featurelijst;
- confidence en waarschuwingen.

### 12.2 Model → PDF

Links:

- 3D bronmodel;
- selecteerbaar aanzicht;
- featureboom.

Rechts:

- live PDF-bladpreview;
- maatvoering;
- titelblok;
- tabellen;
- bladgrenzen;
- printpreview.

### 12.3 Interacties

Ondersteun:

- scrollzoom;
- pan;
- orbit in 3D;
- fit-to-view;
- maat verplaatsen;
- maattekst verplaatsen;
- maat opnieuw ankeren;
- maat verbergen/tonen;
- aanzicht toevoegen/verwijderen;
- detailaanzicht tekenen;
- schaal wijzigen;
- bladformaat wijzigen;
- titelblokvelden bewerken;
- screenshot/PDF-preview;
- undo/redo;
- reset naar automatische layout.

Elke maat in de PDF-preview moet gekoppeld zijn aan een echt geometrisch element. Bij klikken moet de betreffende feature in de 3D-viewer oplichten.

---

## 13. Confidence, provenance en menselijke controle

Geef ieder herkend gegeven:

- waarde;
- bronpagina;
- bronpositie;
- herkenningsmethode;
- confidence;
- status: automatisch, bevestigd, gecorrigeerd of afgeleid.

Voorbeeld:

```text
Profiel: STRIP5*120
Bron: stukregel, pagina 1
Confidence: 99%
Status: automatisch herkend
```

```text
Gatpositie X: 20 mm
Bron: maatlijn in hoofdaanzicht
Confidence: 84%
Status: gebruiker moet bevestigen
```

Stel drempels configureerbaar in, bijvoorbeeld:

- ≥ 95%: automatisch geaccepteerd indien geometrisch consistent;
- 80–95%: waarschuwing en review;
- < 80%: verplichte bevestiging;
- ontbrekend of tegenstrijdig: exportblokkade.

Een confidence-score alleen is nooit voldoende. Combineer die altijd met geometrische consistentiecontroles.

---

## 14. Validaties

### 14.1 Documentvalidatie

- schaal gevonden;
- eenheden gevonden;
- titelblok gelezen;
- positie/mark gevonden;
- materiaal gevonden of expliciet ingevoerd;
- aantal gevonden;
- alle kritische aanzichten aanwezig;
- alle maatteksten gekoppeld;
- geen tegenstrijdige maatketens.

### 14.2 Geometrievalidatie

- gesloten contouren;
- geen zelfkruisingen;
- gaten binnen materiaal;
- geen dubbele gaten;
- radii geometrisch mogelijk;
- profielafmetingen matchen database;
- plaatdikte bekend;
- hoofdmaten consistent;
- featurezijden bekend;
- geen niet-manifold solid;
- volume positief;
- massa plausibel.

### 14.3 Tekeningvalidatie

- geen overlappende maatteksten;
- geen afgesneden views;
- schaal leesbaar;
- titelblok volledig;
- stukregel consistent met model;
- aantal en totale hoeveelheid consistent;
- alle productiefeatures minimaal eenmaal eenduidig aangegeven;
- geen dubbele of conflicterende kritische maatvoering;
- PDF vectorieel en doorzoekbaar.

### 14.4 Roundtripvalidatie

Test minimaal:

```text
External PDF → Canonical Model → NC1 → Model
External PDF → Canonical Model → STEP → Model
External PDF → Canonical Model → IFC → Model

NC1 → PDF → NC1
STEP → PDF → STEP
IFC → PDF → IFC
```

Voor door het programma gemaakte Trusted Converter PDF's moet de terugweg primair via embedded exact data verlopen.

Vergelijk semantisch en geometrisch, niet byte-voor-byte:

- onderdeel-ID;
- profiel;
- materiaal;
- aantal;
- lengte;
- dikte;
- hoofdmaten;
- aantal gaten;
- gatdiameters;
- gatposities;
- contouren;
- radii;
- volume;
- oppervlak;
- massa;
- lokale oriëntatie;
- kritische metadata.

---

## 15. Specifieke acceptatietest met de voorbeeldtekening

Gebruik `Pos LO4 - LOSSE PLAAT.pdf` als verplichte regressietest.

De importer moet minimaal herkennen en tonen:

- positie `LO4`;
- profiel `STRIP5*120`;
- materiaal `S235JR`;
- lengte `160`;
- aantal `4`;
- merk `MLO4`;
- totaal aantal `4`;
- gatcallout `1*Ø14`;
- twee radii `R 13,5`;
- schaal `1:2`;
- A4;
- onderwerp `LOSSE PLAAT`;
- maatvoering en hoofdcontour uit het getoonde aanzicht.

Controleer expliciet of alle contourmaten voldoende zijn om een gesloten, eenduidige geometrie te maken. Als een dikte, referentiezijde of andere kritische productiedata niet betrouwbaar uit de PDF volgt, moet de software dit vragen en niet zelf verzinnen.

Maak vervolgens:

1. een concept-NC1;
2. een STEP-solid;
3. een semantisch IFC-element;
4. een nieuw gegenereerde PDF-tekening.

Vergelijk de nieuw gegenereerde PDF met de bron op:

- informatie-inhoud;
- maatwaarden;
- gat- en radiusaanduidingen;
- positie-/stukregel;
- schaal en bladindeling;
- leesbaarheid.

De layout hoeft niet pixel-identiek te zijn, maar moet technisch gelijkwaardig en duidelijk zijn.

---

## 16. Bedrijfstemplates en lerend gedrag

Ondersteun per organisatie:

- titelbloktemplates;
- logo;
- standaardnotities;
- maatstijl;
- decimale precisie;
- standaard projectiemethode;
- lijngewichten;
- standaard bladformaten;
- standaard materiaalwaarden;
- profielaliasnamen;
- PDF-importtemplates;
- herkenningsregels voor vaste tekenhoofden.

Sla gebruikerscorrecties als gestructureerde regels op, bijvoorbeeld:

- titelblokveldlocatie;
- tabelkolomnaam;
- profielalias;
- gebruikelijke aanzichtplaats;
- projectspecifieke notatie.

Gebruik correcties niet automatisch als globale waarheid voor andere bedrijven. Houd tenantdata gescheiden.

---

## 17. Lokale AI, cloud-AI en privacy

Ontwerp local-first:

- vectoranalyse lokaal;
- geometriekern lokaal;
- profielendatabase lokaal;
- validatie lokaal;
- NC1/STEP/IFC/PDF-export lokaal.

Ondersteun optioneel cloud-AI voor moeilijke scans en semantische interpretatie, maar alleen na expliciete toestemming.

Vereisten:

- duidelijke melding wanneer bestanden extern worden verwerkt;
- configureerbare dataretentie;
- geen training op klantbestanden zonder toestemming;
- auditlog;
- mogelijkheid om cloud-AI volledig uit te schakelen;
- offline basisfunctionaliteit;
- gevoelige project- en bedrijfsgegevens beschermen.

---

## 18. GUI, CLI en automatisering

### 18.1 GUI

Voeg conversiekeuzes toe:

- PDF → NC1;
- PDF → STEP;
- PDF → IFC;
- NC1 → PDF;
- STEP → PDF;
- IFC → PDF.

Voeg een wizard toe:

```text
Bestand kiezen
→ analyse
→ herkende gegevens
→ visuele controle
→ ontbrekende gegevens invullen
→ validatie
→ uitvoer kiezen
→ rapport en bestanden
```

### 18.2 CLI

Ondersteun bijvoorbeeld:

```text
converter pdf-to-nc1 input.pdf -o output/
converter pdf-to-step input.pdf -o output/
converter pdf-to-ifc input.pdf -o output/
converter nc1-to-pdf input.nc1 -o output.pdf
converter step-to-pdf input.step -o output.pdf
converter ifc-to-pdf input.ifc -o output/
```

CLI moet JSON-rapportage, exitcodes en batchverwerking ondersteunen.

### 18.3 API/jobmodel

Maak de module geschikt voor later online gebruik:

- job aanmaken;
- bestand uploaden;
- analyse starten;
- vragen/ambiguïteiten ophalen;
- correcties opslaan;
- export starten;
- status volgen;
- rapport downloaden;
- auditlog.

---

## 19. Rapportage

Maak per conversie een rapport met:

- bronbestand;
- uitvoerbestanden;
- gebruikte methode;
- gedetecteerde onderdelen;
- profiel en materiaal;
- aantallen;
- hoeveelheden;
- confidence;
- gebruikerscorrecties;
- warnings en errors;
- roundtripresultaten;
- volume-/oppervlak-/maatverschillen;
- exportstatus;
- softwareversie;
- hashes.

Bij meerdere IFC-onderdelen moet het log per onderdeel laten zien welk NC1-, STEP- en PDF-bestand is gemaakt of waarom een onderdeel is overgeslagen.

---

## 20. Installatie en distributie

De eindgebruiker mag geen Python, pip, virtual environment of terminal nodig hebben.

Lever:

- één Windows-installer-EXE;
- meegeleverde runtime en dependencies;
- portable fallback ZIP;
- automatische installatie van benodigde lokale modellen/data;
- stille of eenvoudige updateoptie;
- SHA-256-checksums;
- duidelijke versie-informatie.

De gebruiker moet de applicatie met één dubbelklik kunnen installeren en starten.

---

## 21. Teststrategie

### 21.1 Unit tests

Test afzonderlijk:

- vectorpadextractie;
- OCR-parsing;
- symboolherkenning;
- maatgrafiek;
- cirkelfitting;
- contourvereenvoudiging;
- profielmatching;
- viewprojectie;
- maatberekening;
- PDF-layout;
- embedded payload;
- NC1/STEP/IFC-export.

### 21.2 Regressietests

Gebruik:

- bestaande NC1- en STEP-dataset;
- bestaande IFC-roundtripdataset;
- `Pos LO4 - LOSSE PLAAT.pdf`;
- extra vector-PDF's van platen en profielen;
- gescande varianten;
- tekeningen met ontbrekende gegevens;
- tekeningen met tegenstrijdige maten;
- meerdere onderdelen per IFC.

### 21.3 Negatieve tests

Controleer dat export wordt geblokkeerd bij:

- onbekende schaal én onvoldoende maatvoering;
- ontbrekende plaatdikte;
- ambigu profiel;
- open contour;
- conflicterende maatketen;
- onduidelijke gatdiameter;
- onbekende referentiezijde;
- slechte scan;
- beschadigde embedded payload;
- mismatch tussen embedded data en zichtbare PDF.

---

## 22. Definition of done

De uitbreiding is pas gereed wanneer:

1. externe PDF's aantoonbaar kunnen worden geïnterpreteerd tot een controleerbaar onderdeelmodel;
2. PDF → NC1, STEP en IFC werkt voor minimaal platen en standaardprofielen binnen de afgesproken scope;
3. NC1, STEP en IFC automatisch een technisch bruikbare vector-PDF kunnen genereren;
4. de PDF minimaal relevante voor-, boven-, zij- en/of doorsnedeaanzichten kiest;
5. maatvoering, aantallen, profiel, materiaal, lengte, merk en titelblok worden gegenereerd;
6. Trusted Converter PDF's exacte machineleesbare data bevatten voor betrouwbare terugconversie;
7. alle exports door roundtrip- en featurevalidatie gaan;
8. onzekere gegevens zichtbaar zijn en productie-export blokkeren;
9. de voorbeeldtekening als regressietest is opgenomen;
10. GUI, CLI en batchverwerking werken;
11. één Windows-installerbestand beschikbaar is;
12. volledige testresultaten, handleiding, checksums en resterende beperkingen worden geleverd.

---

## 23. Verboden shortcuts

Niet doen:

- een PDF alleen als afbeelding naar een AI-model sturen en vrije NC1-tekst laten genereren;
- ontbrekende maten stilzwijgend afleiden zonder waarschuwing;
- ronde gaten als grove polygonen exporteren wanneer een analytische cirkel bekend is;
- een IFC uitsluitend als triangulated mesh opslaan wanneer semantische/swept geometrie mogelijk is;
- een PDF rasteriseren wanneer vectoroutput mogelijk is;
- een tekening als vrijgegeven markeren terwijl kritische gegevens onzeker zijn;
- veiligheidscontroles uitschakelen om tests te laten slagen;
- alleen een mockup of architectuurdocument leveren zonder werkende code en tests.

---

## 24. Op te leveren resultaat

Lever uiteindelijk:

1. complete geïntegreerde broncode;
2. bijgewerkt canoniek datamodel;
3. PDF-importer met vector-, OCR- en AI-laag;
4. PDF-tekeninggenerator;
5. Trusted Converter PDF met embedded exact model;
6. PDF → NC1/STEP/IFC;
7. NC1/STEP/IFC → PDF;
8. GUI en CLI;
9. bedrijfstemplates;
10. validatie- en roundtriprapporten;
11. testbestanden en verwachte resultaten;
12. één Windows-installer-EXE;
13. portable ZIP;
14. gebruikershandleiding;
15. technische documentatie;
16. SHA-256-checksums;
17. een eerlijk overzicht van wat exact werkt en welke beperkingen nog bestaan.

Begin met het analyseren van de bestaande code en testbestanden. Maak daarna eerst het canonieke onderdeelmodel en de Trusted Converter PDF-structuur, omdat die de basis vormen voor een betrouwbare bidirectionele workflow. Implementeer vervolgens de externe PDF-herkenning, de tekeninggenerator en de gebruikerscontrole. Test iedere stap op echte roundtrips voordat je de volgende fase vrijgeeft.---

# Aanvullende productiemodule — compleet IFC-/STEP-model naar onderdelen, merken, inkoop, optimalisatie en machines

## 25. Hoofddoel van de complete-modelmodule

Breid de applicatie uit met een volwaardige **Project- en Productievoorbereidingsmodule**. Deze module moet een compleet IFC- of STEP-model als project kunnen inladen, de inhoud veilig opdelen in assemblies, merken, losse onderdelen, bevestigingsmiddelen, lasobjecten, beton-/houtobjecten en inkoopdelen, en alle afgeleide productiegegevens centraal beheren.

De hoofdworkflow wordt:

```text
Compleet IFC-/STEP-model
        ↓
Modelstructuur + geometrie + eigenschappen uitlezen
        ↓
Assemblies / merken / onderdelen / inkoopdelen classificeren
        ↓
Geometrisch normaliseren en identieke delen groeperen
        ↓
BOM, hoeveelheden, tekeningen en productiefeatures valideren
        ↓
Per merk of onderdeel exporteren
        ↓
PDF / NC1-DSTV / IFC / STEP / Excel / labels
        ↓
Handelslengte-optimalisatie / plaatnesting / inkoopplanning
        ↓
Vrijgegeven machinejobs via gevalideerde postprocessors
```

Deze module mag geen los programma worden. Integreer haar met:

- het canonieke interne model;
- de PDF-/tekeningenmodule;
- de NC1-, IFC- en STEP-converters;
- de profielendatabase;
- de materiaalbibliotheek;
- de hoeveelheden- en Excelmodule;
- de viewer;
- de validatie-engine;
- gebruikers, bedrijven, rollen, auditlog en instellingen;
- de Windows-installer en later de online bedrijfsomgeving.

---

## 26. Referentiemodellen en verplichte regressiebasis

Gebruik de meegeleverde bestanden als verplichte functionele referenties:

1. `TAS_RVB Defensie onderbouw te Leeuwarden- Rev4 [definitief].ifc`
2. `Samenstel nieuw - D1500-0190_Predeterminado (1).step`
3. `Staalconstructie bordes c04 - Part 18.step`

### 26.1 IFC-referentie

Het IFC-bestand is een Tekla Structures-export met onder meer:

- IFC2X3 Coordination View;
- assembly hierarchy ingeschakeld;
- bouten ingeschakeld;
- lassen ingeschakeld;
- property sets ingeschakeld;
- `IfcElementAssembly`-objecten;
- onderdelen zoals `IfcPlate`, `IfcBeam` en `IfcColumn`;
- mechanische bevestigingsmiddelen;
- lasobjecten;
- materialen;
- merken, part positions, gewichten, lengtes, fasen en andere Tekla-eigenschappen.

Gebruik dit bestand om de semantische IFC-route te testen. De applicatie moet de IFC-hiërarchie en properties benutten en mag niet eerst alles tot één vorm of mesh reduceren.

Programmeer een regressietest die minimaal controleert dat de huidige referentie-import dezelfde orde van grootte en classificatie teruggeeft als de gecontroleerde nulmeting:

- 353 assemblies;
- 1.293 platen;
- 707 liggers/balkobjecten;
- 369 kolomobjecten;
- 723 mechanische bevestigingsmiddelen;
- 2.654 las-/fastenerobjecten;
- 38 funderings-/opstortobjecten;
- 19 building-element proxies;
- 3 slabobjecten.

De test moet daarnaast specifiek herkennen:

- assemblymerk `MLO4`;
- part position `LO4`;
- profiel/omschrijving `STRIP5*120`;
- materiaal `S235JR`;
- lengte `160 mm`;
- assemblygewicht rond `0,6 kg`;
- een bout-/gatobject met nominale diameter `14 mm`;
- herhaalde merken zoals `LA1`, `A1`, `MP1` en `MP2` als meerdere exemplaren van een merk, niet automatisch als unieke nieuwe typen.

Leg afwijkingen tussen parser-versies vast en verklaar ze. Verlaag geen controles om een getal passend te maken.

### 26.2 STEP-referenties

De twee meegeleverde STEP-bestanden zijn AP242-bestanden uit Onshape. Behandel ze als voorbeelden van STEP-bestanden die wel hoogwaardige BREP-geometrie bevatten, maar niet noodzakelijk een bruikbare assemblyboom of productieproperties aanbieden.

De gecontroleerde nulmeting van de huidige bestanden is:

- `Samenstel nieuw - D1500-0190_Predeterminado (1).step`: één productrecord en één BREP-solid;
- `Staalconstructie bordes c04 - Part 18.step`: één productrecord en één BREP-solid.

De importer mag deze bestanden daarom niet kunstmatig opdelen in meerdere merken wanneer daarvoor geen semantische of geometrische basis bestaat. Ze moeten als afzonderlijke onderdelen of inkoopkandidaten worden geïmporteerd, waarna profiel-/featureherkenning en gebruikersclassificatie kunnen volgen.

Voeg daarnaast synthetische en echte regressiebestanden toe voor:

- AP242-assembly met meerdere product occurrences;
- STEP-compound met meerdere losse solids;
- één gefuseerde solid zonder assemblymetadata;
- meerdere identieke solids met verschillende placements;
- purchased part met fabrikant- of artikelmetadata;
- model met ontbrekende namen en merken.

---

## 27. Drie verplichte importstrategieën

De applicatie moet automatisch vaststellen welke importstrategie bruikbaar is. Gebruik deze prioriteitsvolgorde.

### 27.1 Strategie A — semantische productstructuur

Gebruik deze route wanneer IFC of STEP een betrouwbare product-/assemblystructuur bevat.

Voor IFC:

- lees `IfcProject`, `IfcSite`, `IfcBuilding` en storeys;
- lees `IfcElementAssembly`;
- volg `IfcRelAggregates` en relevante nesting-/containmentrelaties;
- lees `IfcPlate`, `IfcBeam`, `IfcColumn`, `IfcMember`, `IfcFooting`, `IfcSlab`, proxies en andere relevante producttypen;
- lees `IfcMechanicalFastener`, fasteners en weld-representaties;
- lees `IfcMaterial` en materiaalassociaties;
- lees quantity sets en property sets;
- behoud GlobalId, Name, Tag, ObjectType, placement en bronrelaties.

Voor STEP AP242:

- lees product, product definition en product occurrence-structuur;
- lees assembly usage relations;
- behoud placements/transformaties;
- behoud part names, product IDs, kleuren, layers en beschikbare user-defined attributes;
- koppel iedere shape representation aan het juiste product occurrence.

### 27.2 Strategie B — losse solids/connected components

Gebruik deze route wanneer geen semantische boom bestaat, maar het bestand meerdere duidelijk gescheiden solids bevat.

- splits een compound in topologische solids;
- behoud globale placement per solid;
- bereken een geometriehash in lokale coördinaten;
- groepeer identieke solids ondanks verschillende posities en rotaties;
- detecteer spiegelvarianten apart;
- genereer tijdelijke part-ID's wanneer namen ontbreken;
- laat de gebruiker groepen bevestigen en benoemen.

### 27.3 Strategie C — gefuseerde of onduidelijke geometrie

Gebruik deze route alleen als veilige fallback.

- analyseer connected regions, contacts, las-/boutverbindingen en geometrische discontinuïteiten;
- probeer standaardprofielen, platen, buizen en inkoopdelen te herkennen;
- maak geen definitieve opsplitsing wanneer een naad of contactvlak ook onderdeel van één gefabriceerde solid kan zijn;
- geef ieder voorstel een confidence-score;
- toon scheidingsvlakken visueel;
- laat de gebruiker onderdelen samenvoegen of splitsen;
- blokkeer NC1-uitvoer zolang de opsplitsing niet bevestigd is.

Noem deze route nooit “exact” wanneer de bron geen productstructuur bevat.

---

## 28. Uitgebreid projectdatamodel

Breid het canonieke model uit met minimaal de volgende entiteiten.

### 28.1 ProjectModel

- project-ID;
- projectnaam;
- klant;
- order;
- bronbestanden en hashes;
- importversie;
- eenheden;
- projectcoördinaten;
- assemblies;
- onderdelen;
- inkoopdelen;
- materialen;
- voorraad;
- productieorders;
- revisies;
- auditstatus.

### 28.2 Assembly / Merk

- internal ID;
- source GlobalId/product occurrence ID;
- merk/assembly mark;
- naam;
- aantal exemplaren;
- children;
- hoofdonderdeel;
- secundaire onderdelen;
- bevestigingsmiddelen;
- lassen;
- totaalgewicht;
- oppervlakte;
- globale placement;
- lokale assemblyassen;
- productiestatus;
- tekeningstatus;
- exportartefacten.

### 28.3 Part / Onderdeel

- part position;
- merkrelaties;
- aantal totaal;
- aantal per assembly;
- onderdeeltype;
- profiel;
- materiaal;
- lengte;
- massa;
- oppervlak;
- exact solid/BREP;
- productiefeatures;
- lokale assen;
- geometry hash;
- manufacturing hash;
- source provenance;
- exporteerbaarheid naar NC1;
- controlewaarschuwingen.

### 28.4 PurchasedItem / Inkoopdeel

- artikelnummer;
- leverancier;
- fabrikant;
- omschrijving;
- norm;
- materiaal/kwaliteit;
- afmetingen;
- hoeveelheid;
- eenheid;
- stukprijs;
- levertijd;
- alternatieve artikelen;
- STEP/IFC-preview;
- wel/geen interne bewerking;
- inkoopstatus;
- gekoppelde assemblies.

### 28.5 Fastener en Weld

- type;
- diameter/maat;
- kwaliteit;
- lengte;
- norm;
- aantal;
- locatie;
- connected parts;
- gatdiameter;
- sleufinformatie;
- lasgrootte;
- laslengte;
- lasproces;
- zijde;
- werkplaats/montage;
- kosten-/tijdparameters.

### 28.6 StockItem en Remnant

- materiaal;
- profiel;
- kwaliteit;
- handelslengte of plaatformaat;
- heat/batch/certificaat;
- leverancier;
- voorraadlocatie;
- beschikbaar aantal;
- prijs;
- reserveringen;
- restlengte/restplaat;
- minimum herbruikbare maat;
- status.

### 28.7 ProductionOperation

- zagen;
- boren;
- ponsen;
- snijden;
- frezen;
- markeren;
- afschuinen;
- coping/notching;
- lassen;
- conserveren;
- montage;
- machineklasse;
- machine-ID;
- instelling;
- cyclustijd;
- gereedschap;
- kwaliteitscontrole.

### 28.8 MachineProfile en MachineJob

- machine-ID;
- fabrikant/type;
- controller;
- ondersteunde formaten;
- maximale profiel-/plaatmaten;
- assen en kinematica;
- ondersteunde bewerkingen;
- gereedschappen;
- kerf/zaagbladbreedte;
- klem- en grijperzones;
- nulpunten;
- tolerantie;
- postprocessorversie;
- simulatiestatus;
- vrijgavestatus;
- jobbestand;
- checksum;
- operator;
- uitvoerlog.

---

## 29. Classificatie: produceren, inkopen, negeren of controleren

Classificeer elk object in één van deze hoofdcategorieën:

1. **Maakdeel** — intern te produceren onderdeel;
2. **Inkoopdeel** — standaard of leveranciersdeel;
3. **Bevestigingsmiddel** — bout, moer, ring, anker, schroef, etc.;
4. **Las-/procesobject** — geen zelfstandig materiaalonderdeel;
5. **Assembly/merk** — verzameling onderdelen;
6. **Niet-staal / ander vakgebied** — beton, hout, installatieobject, etc.;
7. **Referentieobject** — alleen context, niet produceren;
8. **Onbekend** — handmatig beoordelen.

### 29.1 Deterministische regels

Gebruik eerst regels op basis van:

- IFC-klasse;
- STEP-productnaam;
- part/assembly mark;
- profielbenaming;
- materiaal;
- standaard;
- fabrikant-/artikelnummer;
- geometrische categorie;
- propertysets;
- bedrijfsspecifieke mappingtabellen.

### 29.2 AI-classificatie

AI mag vervolgens:

- een categorie voorstellen;
- tekstaliassen herkennen;
- mogelijke leveranciersdelen signaleren;
- vergelijkbare artikelen suggereren;
- onduidelijke objectnamen interpreteren.

AI mag niet zelfstandig een NC-bestand vrijgeven of een object definitief als inkoopdeel verwijderen. Alle AI-classificaties moeten provenance en confidence krijgen.

### 29.3 Inkoopdeelherkenning

Herken onder meer:

- bouten, moeren en ringen;
- draadstangen en ankers;
- roosters;
- traptreden;
- scharnieren;
- lagers;
- wielen;
- motoren en aandrijvingen;
- bevestigingssets;
- standaard handrailcomponenten;
- leveranciersspecifieke onderdelen.

Maak voor inkoopdelen geen NC1 tenzij expliciet een interne nabewerking nodig is. Genereer in plaats daarvan een inkooplijst, artikelkaart, leveranciersbestanden en eventuele controle-PDF.

---

## 30. Merken, identieke onderdelen en geometrische groepering

Gebruik meerdere niveaus van identiteit.

### 30.1 Bronidentiteit

- IFC GlobalId;
- STEP occurrence/product ID;
- Tekla part position;
- Tekla assembly mark;
- bronbestand + entity-ID.

### 30.2 Geometrie-identiteit

Bereken een lokale, placement-onafhankelijke hash op basis van:

- profiel/doorsnede;
- lengte;
- exacte BREP-topologie;
- gaten;
- contouren;
- radii;
- bewerkingen;
- materiaal indien relevant;
- tolerantieversie.

### 30.3 Productie-identiteit

Twee delen zijn alleen hetzelfde productiedeel als minimaal gelijk zijn:

- materiaal/kwaliteit;
- profiel;
- lengte;
- alle productiefeatures;
- referentiezijden;
- spiegelstatus;
- vereiste toleranties;
- nabewerking/coating indien productiebepalend.

### 30.4 Conflicten

Toon expliciet:

- hetzelfde merk met verschillende geometrie;
- dezelfde geometrie met verschillende merken;
- gelijk onderdeel met verschillend materiaal;
- gespiegeld onderdeel;
- bijna gelijk onderdeel binnen tolerantie;
- ontbrekend merk;
- dubbel GlobalId;
- revisiewijziging.

Laat de gebruiker nooit ongemerkt verschillende geometrieën onder één NC-bestandsnaam exporteren.

---

## 31. Projectverkenner en gebruikersinterface

Voeg een hoofdtabblad **Project / Productie** toe.

### 31.1 Linkerpaneel — modelboom

Toon hiërarchisch:

```text
Project
├── Locaties / bouwlagen
├── Assemblies / merken
│   ├── hoofdonderdeel
│   ├── secundaire onderdelen
│   ├── bouten
│   └── lassen
├── Losse onderdelen
├── Inkoopdelen
├── Niet-staal
├── Onbekend / te controleren
└── Uitvoer en productieorders
```

### 31.2 Middenpaneel — onderdelenlijst

Kolommen minimaal:

- selectie;
- status;
- assemblymerk;
- part position;
- naam;
- categorie;
- profiel;
- materiaal;
- lengte;
- aantal;
- massa per stuk;
- totaalgewicht;
- maak/inkoop;
- NC1-geschikt;
- PDF-status;
- IFC-status;
- STEP-status;
- machine;
- revisie;
- waarschuwingen.

Ondersteun:

- zoeken;
- filters;
- groeperen;
- sorteren;
- kolommen opslaan;
- massabewerking;
- handmatige herclassificatie;
- selectie synchroniseren met 3D-viewer.

### 31.3 Rechterpaneel — 3D/2D en eigenschappen

- 3D-model;
- geselecteerd onderdeel isoleren;
- assembly tonen;
- transparante omgeving;
- exploderen;
- kleur per status/materiaal/profiel;
- productiefeatures markeren;
- eigenschappen;
- herkomst;
- waarschuwingen;
- exportpreview;
- tekeningpreview.

### 31.4 Onderliggende tabs

- Overzicht;
- Merken;
- Onderdelen;
- Inkoopdelen;
- Bouten;
- Lassen;
- Hoeveelheden;
- PDF/tekeningen;
- NC-uitvoer;
- Handelslengten;
- Plaatnesting;
- Voorraad/reststukken;
- Machines;
- Productiequeue;
- Validatie;
- Auditlog.

---

## 32. Export per onderdeel en per merk

### 32.1 Per los onderdeel

Ondersteun:

- NC1/DSTV;
- STEP;
- IFC;
- technische PDF;
- DXF voor geschikte plaatcontouren;
- Excel-/CSV-regel;
- label met barcode/QR;
- JSON-manifest;
- previewafbeelding.

### 32.2 Per assembly/merk

Ondersteun:

- assembly-PDF met stuklijst, aanzichten en las-/boutinformatie;
- losse part-PDF's;
- assembly-IFC;
- assembly-STEP;
- map met alle NC1-bestanden van maakdelen;
- inkooplijst;
- laslijst;
- boutenlijst;
- pak-/montagelijst;
- totaalrapport;
- ZIP-productiepakket met manifest en checksums.

### 32.3 Batch- en selectie-export

De gebruiker moet kunnen exporteren op:

- geselecteerde onderdelen;
- één merk;
- alle exemplaren van een merk;
- fase;
- materiaal;
- profiel;
- bouwlaag;
- productiestatus;
- machine;
- leverdatum;
- complete projectselectie.

### 32.4 Bestandsnamen

Maak configureerbare, conflictvrije naamtemplates, bijvoorbeeld:

```text
{project}_{assembly_mark}_{part_position}_{profile}_{revision}.{ext}
```

Valideer illegale tekens, maximale padlengte en dubbele namen. Gebruik nooit alleen een niet-unieke zichtbare naam.

---

## 33. Automatische technische PDF's vanuit complete modellen

Genereer twee niveaus.

### 33.1 Onderdeeltekening

Per uniek maakdeel:

- voor-, boven-, zij- en/of eindaanzicht;
- relevante doorsneden/details;
- maatvoering;
- profiel;
- materiaal;
- lengte;
- aantal totaal;
- gekoppelde merken;
- massa;
- oppervlakte;
- onderdeelpositie;
- NC1-status;
- revisie;
- barcode/QR naar projectrecord.

### 33.2 Merktekening / samenstellingstekening

Per assemblymerk:

- orthogonale aanzichten;
- isometrisch overzicht;
- hoofd- en secundaire onderdelen;
- positienummers;
- stuklijst;
- bouten en montagebouten;
- lassen en laslengtes;
- hoofdafmetingen;
- gewicht;
- zwaartepunt indien gewenst;
- montage-/productienotities;
- aantal exemplaren;
- revisieverschillen.

PDF-uitvoer moet vectorieel zijn en een embedded exact project-/onderdeelmanifest bevatten waar mogelijk.

---

## 34. Hoeveelheden, BOM en inkoop

Genereer minimaal:

### 34.1 Part BOM

- part position;
- profiel;
- materiaal;
- lengte;
- aantal;
- massa/stuk;
- totaalgewicht;
- oppervlak;
- coatingoppervlak;
- bronmerk(en).

### 34.2 Assembly BOM

- assembly mark;
- aantal assemblies;
- child parts;
- aantallen per assembly;
- bouten;
- lassen;
- gewicht;
- productiestatus.

### 34.3 Inkoop-BOM

- artikel;
- leverancier;
- norm;
- maat;
- kwaliteit;
- aantal;
- reservepercentage;
- benodigde datum;
- voorraad;
- te bestellen aantal;
- prijs;
- totaalprijs;
- alternatieven.

### 34.4 Materiaalstaat

- materiaal en kwaliteit;
- profiel/plaattype;
- netto behoefte;
- bruto behoefte na optimalisatie;
- snijverlies;
- reststukken;
- voorraaddekking;
- inkoopbehoefte;
- certificaat-/heatvereisten.

---

## 35. Optimaliseren naar handelslengten — 1D cutting stock

Bouw een reproduceerbare optimalisatiemodule voor profielen, kokers, buizen, hoeklijnen, rondstaal en strippen.

### 35.1 Invoer

- profiel;
- materiaal/kwaliteit;
- gewenste stuklengte;
- aantal;
- zaaghoeken links/rechts;
- kerf/zaagbladbreedte;
- koptrim;
- minimum eindrest;
- klemlengtes;
- grijperverboden zones;
- markeer-/boorvolgorde;
- beschikbare handelslengten;
- voorraadstaven;
- reststukken;
- leveranciersprijs;
- heat/batch/certificaat;
- gewenste leverdatum;
- machinesnelheid en setupkosten.

### 35.2 Harde beperkingen

- meng geen verschillende materialen/kwaliteiten;
- meng geen heats wanneer traceability dit verbiedt;
- gebruik geen reststuk onder minimummaat;
- respecteer kerf en trim;
- respecteer machine- en klemgrenzen;
- respecteer schuine zaagsneden;
- roteer/spiegel alleen wanneer productiegeometrie dat toestaat;
- splits een onderdeel niet zonder expliciete constructieve toestemming.

### 35.3 Doelfuncties

Maak configureerbaar:

1. minimale materiaalkosten;
2. minimaal afval;
3. minimaal aantal handelslengten;
4. minimaal aantal setups;
5. maximaal gebruik van bestaande reststukken;
6. minimale doorlooptijd;
7. combinatie van bovenstaande met gewichten.

### 35.4 Uitvoer

- zaagplan per staaf;
- grafische balkindeling;
- part marks op volgorde;
- kerfs;
- restlengte;
- afvalpercentage;
- bruto/netto materiaal;
- kosten;
- gebruikte voorraad;
- nieuw reststuk-ID;
- machinejob;
- zaaglijst-PDF;
- Excel;
- labels;
- machinebestand.

### 35.5 Algoritmen en controle

Gebruik voor kleine sets een exacte of aantoonbaar optimale methode waar praktisch. Gebruik voor grote sets een combinatie van column generation, integer programming en gecontroleerde heuristieken. Rapporteer:

- optimaliteitsstatus;
- lower bound;
- gevonden oplossing;
- gap;
- rekentijd;
- toegepaste vereenvoudigingen.

Een “optimale” claim mag alleen wanneer dit mathematisch is aangetoond binnen de ingestelde scope.

---

## 36. Plaatoptimalisatie — 2D nesting

Voor platen en stripcontouren:

### 36.1 Invoer

- materiaal;
- kwaliteit;
- dikte;
- plaatformaten;
- beschikbare restplaten;
- contour;
- binnencontouren;
- aantal;
- walsrichting/nerfrichting;
- rotatiebeperkingen;
- spiegelbeperkingen;
- kerf;
- randmarge;
- tussenafstand;
- lead-ins/lead-outs;
- common-line-cutting toegestaan;
- microjoints;
- machine tafelmaat;
- snijtechniek.

### 36.2 Uitvoer

- nestplan;
- plaatnummer;
- onderdeelposities;
- materiaalbenutting;
- snijlengte;
- pierce count;
- verwachte cyclustijd;
- restplaatcontour;
- DXF/NC/postprocessoroutput;
- nest-PDF;
- labels;
- traceability-manifest.

### 36.3 Veiligheid

- behoud gat-/contourtopologie;
- controleer overlaps;
- controleer minimale bruggen;
- respecteer warmte-/vervormingsregels per machine;
- laat nesting niet de gevalideerde onderdeelgeometrie wijzigen;
- roundtrip-vergelijk ieder genest onderdeel met het bronmodel.

---

## 37. Voorraad, handelslengten en reststukken

Voeg een configureerbare database toe met:

- standaard handelslengten per profiel/leverancier;
- standaard plaatformaten;
- prijzen;
- levertijden;
- minimumorderhoeveelheid;
- zaag-/snijkosten;
- materiaalcertificaten;
- actuele voorraad;
- gereserveerde voorraad;
- reststukken;
- locatie;
- barcode/QR;
- laatste meting;
- bruikbaarheidsstatus.

Laat de gebruiker één optimalisatie draaien tegen:

- alleen nieuwe handelslengten;
- alleen eigen voorraad;
- voorraad + reststukken + nieuwe inkoop;
- één leverancier;
- meerdere leveranciers;
- kostenoptimum;
- afvaloptimum;
- doorlooptijdoptimum.

---

## 38. Productieroutes en machinekeuze

Bouw een capability-based routeplanner.

### 38.1 Machinecategorieën

Ondersteun conceptueel:

- zaagmachine;
- zaag-/boorstraat;
- pons-/kniplijn;
- profielboor-/cope-lijn;
- plaatlaser;
- plasmatafel;
- autogeensnijtafel;
- waterjet;
- buislaser;
- hoeklijnmachine;
- freesmachine;
- markeermachine;
- lasrobot;
- handmatige werkplek.

### 38.2 Capability matrix

Per machine:

- profieltypen;
- min/max afmetingen;
- min/max lengte;
- gatdiameters;
- sleufgaten;
- boorassen;
- contourbewerking;
- zaaghoeken;
- markering;
- afschuining;
- gereedschappen;
- tolerantie;
- controller/formaat;
- klem-/grijperzones;
- onderhoudsstatus;
- beschikbaarheid.

### 38.3 Automatische routekeuze

De software mag een route voorstellen op basis van:

- maakbaarheid;
- materiaal;
- profiel;
- features;
- machinecapaciteit;
- setup;
- cyclustijd;
- wachtrij;
- kosten;
- leverdatum.

De operator/planner moet de route kunnen wijzigen. Niet-maakbare features moeten zichtbaar blijven en mogen niet stilzwijgend verdwijnen.

---

## 39. Machineaansturing: veilige architectuur

### 39.1 Geen universele directe uitvoer aannemen

Gebruik NC1/DSTV als neutrale productiebeschrijving waar passend, maar houd rekening met machine-/controller-specifieke postprocessing. Bouw één adapter/postprocessor per machineconfiguratie.

### 39.2 Gelaagde keten

```text
Gevalideerd Canonical Part
        ↓
Machine capability check
        ↓
Neutral manufacturing job
        ↓
Machine-specifieke postprocessor
        ↓
Simulatie en limietcontrole
        ↓
Digitale vrijgave
        ↓
Machinequeue / beveiligde overdracht
        ↓
Status- en resultaatterugmelding
```

### 39.3 Ondersteunde uitvoerfamilies

Afhankelijk van machine en licentie:

- DSTV/NC1;
- DXF;
- CSV/XML/JSON jobdata;
- G-code alleen via gevalideerde controllerpostprocessor;
- leverancierspecifieke formaten;
- labels/barcodes;
- zaaglijsten;
- boor-/markeerprogramma's.

### 39.4 Vrijgaveworkflow

Minimaal:

1. geometrie gevalideerd;
2. materiaal en profiel bevestigd;
3. machinecapability geslaagd;
4. postprocessorversie vastgelegd;
5. simulatie geslaagd;
6. operator ziet preview;
7. bevoegde gebruiker geeft vrij;
8. bestand krijgt checksum en onveranderbare auditregel;
9. machineontvangst wordt bevestigd;
10. productie-uitkomst wordt teruggekoppeld.

### 39.5 OPC UA/MES-koppeling

Ondersteun later OPC UA of leveranciers-API's voor:

- machine-identificatie;
- status;
- productiequeue;
- jobstatus;
- tellerstanden;
- storingen;
- gereedschapstatus;
- gereedmelding;
- KPI's.

Gebruik OPC UA niet als excuus om de geometrische postprocessor of controller-validatie over te slaan. Monitoring/jobmanagement en daadwerkelijke machinecode zijn afzonderlijke verantwoordelijkheden.

### 39.6 Verboden gedrag

- nooit automatisch naar een machine sturen na alleen AI-herkenning;
- nooit veiligheidscontroles uitschakelen;
- nooit onondersteunde bewerkingen stilzwijgend verwijderen;
- nooit generieke G-code voor verschillende controllers hergebruiken;
- nooit een job overschrijven zonder revisie en auditlog;
- nooit een machineprogramma vrijgeven zonder preview/simulatie.

---

## 40. Planning, labels en traceability

Genereer per productieorder:

- ordernummer;
- project;
- merk;
- part position;
- aantal;
- materiaal;
- heat/certificaat;
- handelslengte/plaat-ID;
- nest-/zaagplan;
- machine;
- route;
- operator;
- status;
- revisie;
- QR/barcode;
- tijdstempels;
- kwaliteitsmetingen;
- afkeur/herwerk;
- reststukregistratie.

Labels moeten naar het juiste digitale onderdeelrecord verwijzen en mogen geen gevoelige data bevatten die niet nodig is op de werkvloer.

---

## 41. Revisies en modelvergelijking

Bij een nieuw IFC-/STEP-model:

- vergelijk op GlobalId/product occurrence;
- vergelijk marks en part positions;
- vergelijk geometriehash;
- detecteer toegevoegd, verwijderd, gewijzigd en verplaatst;
- onderscheid alleen placementwijziging van productiegeometriewijziging;
- hergebruik reeds goedgekeurde NC/PDF alleen als manufacturing hash gelijk is;
- invalideer optimalisatie- en machinejobs wanneer relevante delen wijzigen;
- toon impact op materiaal, inkoop, voorraad en planning.

---

## 42. API en CLI voor complete modellen

Voeg minimaal toe:

```text
converter project-import model.ifc --project <naam>
converter project-import assembly.step --project <naam>
converter project-list-parts <project-id>
converter project-export-parts <project-id> --format nc1,step,ifc,pdf
converter project-export-assemblies <project-id> --format pdf,ifc,step
converter project-bom <project-id> --output bom.xlsx
converter optimize-bars <project-id> --stock stock.json
converter optimize-plates <project-id> --stock plates.json
converter create-machine-jobs <project-id> --machine <machine-id>
converter validate-machine-job <job-id>
```

CLI-eisen:

- JSON-outputmodus;
- bruikbare exitcodes;
- progress reporting;
- hervatbare batchjobs;
- geen stilzwijgende gedeeltelijke successen;
- manifest van alle gemaakte/overgeslagen bestanden;
- checksums.

API-endpoints later minimaal:

- `POST /api/projects/import`;
- `GET /api/projects/:id/tree`;
- `GET /api/projects/:id/parts`;
- `GET /api/projects/:id/assemblies`;
- `GET /api/projects/:id/purchased-items`;
- `POST /api/projects/:id/classify`;
- `POST /api/projects/:id/export`;
- `POST /api/projects/:id/optimize/bars`;
- `POST /api/projects/:id/optimize/plates`;
- `POST /api/projects/:id/machine-jobs`;
- `POST /api/machine-jobs/:id/release`;
- `GET /api/machine-jobs/:id/status`.

---

## 43. Aanvullende acceptatietests

### 43.1 IFC-projectimport

Voor het meegeleverde Tekla IFC-model:

- project opent zonder crash;
- assembly hierarchy blijft behouden;
- merken en part positions zijn doorzoekbaar;
- MLO4/LO4 wordt correct gekoppeld;
- materiaal, profiel, lengte, gewicht en bout-/gatinformatie worden getoond;
- bouten en lassen worden niet als gewone maakdelen geteld;
- beton/hout wordt van staalproductie gescheiden;
- herhaalde assemblymerken worden gegroepeerd met aantallen;
- ieder maakdeel kan worden geïsoleerd in de viewer;
- exportmanifest vermeldt ieder onderdeel en iedere reden van overslaan.

### 43.2 STEP-import

Voor beide meegeleverde STEP-bestanden:

- ieder bestand wordt als één product/solid geïmporteerd;
- geen fictieve assemblyonderdelen worden gemaakt;
- productnaam uit STEP wordt behouden;
- geometrie, volume en hoofdmaten worden gecontroleerd;
- gebruiker kan classificeren als maakdeel of inkoopdeel;
- per bestand kunnen STEP, IFC en PDF worden gemaakt;
- NC1 alleen wanneer profiel/features betrouwbaar herkend of bevestigd zijn.

### 43.3 Identieke delen

- identieke onderdelen op verschillende posities worden gegroepeerd;
- gespiegeld onderdeel blijft apart indien productie verschillend is;
- zelfde mark met andere geometrie geeft een blokkerende waarschuwing;
- geometry hash en manufacturing hash zijn stabiel over herimport.

### 43.4 Handelslengten

Testsets bevatten:

- eenvoudige exact oplosbare cases;
- meerdere handelslengten;
- kerf;
- reststukken;
- schuine zaagsneden;
- heat-separatie;
- onmogelijke orders;
- grote heuristische set.

Controleer materiaalbalans:

```text
bruto lengte = som onderdelen + kerf + trims + rest + afval
```

### 43.5 Plaatnesting

- geen overlaps;
- alle aantallen aanwezig;
- materiaal/dikte correct;
- walsrichting gerespecteerd;
- contouren onveranderd;
- restplaat correct berekend;
- roundtrip van ieder onderdeel geslaagd.

### 43.6 Machinejob

- ongeschikte machine wordt geweigerd;
- niet-ondersteunde feature wordt gemeld;
- postprocessorversie wordt opgeslagen;
- simulatie is verplicht;
- checksum verandert bij jobwijziging;
- vrijgave vereist bevoegde rol;
- auditlog is compleet;
- testomgeving kan geen echte machine per ongeluk aansturen.

---

## 44. Uitgebreide definition of done

De complete-model- en productiemodule is pas gereed wanneer:

1. een groot IFC-project met assemblies, onderdelen, bouten, lassen en materialen bruikbaar wordt ingelezen;
2. semantische IFC-hiërarchie behouden blijft;
3. STEP zowel met als zonder assemblyboom veilig wordt behandeld;
4. merken, part positions en identieke delen correct worden gegroepeerd;
5. inkoopdelen, maakdelen, bevestigingsmiddelen en niet-staal apart worden geclassificeerd;
6. ieder geselecteerd onderdeel PDF, NC1, IFC en STEP kan exporteren voor zover technisch passend;
7. ieder merk een assembly-PDF, IFC, STEP, stuklijst en productie-exportpakket kan krijgen;
8. NC1-uitvoer alleen na feature- en roundtripvalidatie beschikbaar is;
9. handelslengte-optimalisatie materiaalbalans en beperkingen aantoonbaar respecteert;
10. plaatnesting geen geometrie wijzigt en alle onderdelen bevat;
11. voorraad, reststukken en inkoopbehoefte worden verwerkt;
12. machinekeuze capability-based gebeurt;
13. iedere machine een versieerbare, geteste postprocessor heeft;
14. simulatie en bevoegde vrijgave verplicht zijn;
15. jobstatus en audittrail terug te lezen zijn;
16. de referentie-IFC en beide referentie-STEP-bestanden als automatische regressietests zijn opgenomen;
17. GUI, CLI en later API dezelfde projectdata gebruiken;
18. de volledige functionaliteit via één Windows-installer beschikbaar is;
19. alle testresultaten, beperkingen, checksums en versies worden meegeleverd;
20. geen AI-uitvoer rechtstreeks als machineveilig wordt beschouwd.

---

## 45. Aanvullend op te leveren resultaat

Lever naast de eerder gevraagde bestanden ook:

1. complete-model importer voor IFC en STEP;
2. project-/assembly-/partdatamodel;
3. projectverkenner in de GUI;
4. BOM- en inkoopmodule;
5. part- en assembly-exportpakketten;
6. handelslengte-optimalisator;
7. plaatnestingmodule of duidelijke gevalideerde integratielaag;
8. voorraad- en reststukkenmodule;
9. machineprofielen en capability matrix;
10. postprocessorframework;
11. simulatie-/vrijgaveworkflow;
12. productiequeue en auditlog;
13. labels en traceability;
14. referentieanalyse en regressietests voor de drie meegeleverde modellen;
15. eerlijke rapportage welke machines en formaten daadwerkelijk gevalideerd zijn.

De implementatievolgorde moet zijn:

```text
1. Semantische IFC/STEP-projectimport
2. Projectboom en betrouwbare part/assembly-identiteit
3. Classificatie en BOM
4. Per-part/per-merk PDF, IFC, STEP en bestaande NC1-export
5. Geometrische deduplicatie en revisievergelijking
6. Handelslengte-optimalisatie
7. Plaatnesting
8. Machine capability-profielen
9. Postprocessors, simulatie en vrijgave
10. Voorraad, MES/OPC UA en bedrijfsintegraties
```

Bouw de machineaansturing pas nadat import, classificatie, geometrie en productie-export aantoonbaar betrouwbaar zijn. Een mooi dashboard zonder gevalideerde geometrie, materialisatie en veiligheidsketen geldt niet als voltooid.


---

# Supplied phased build plan

The following build plan is included for sequencing context. The current immediate phase is the Part Workbench/production-feature validation bridge. Do not skip ahead to optimization or machine control.

# CWS Convertor — integraal bouwplan naar een productierijpe versie 1.0

**Status:** eerste bouwplan  
**Basis:** bestaande v0.5.1-conversiekern + uitbreiding complete-model-/productiemodule  
**Productnaam:** **CWS Convertor**

---

## 1. Productdoel

CWS Convertor wordt één geïntegreerde desktopapplicatie met vijf logisch gescheiden lagen:

1. **Convertor Core** — NC1/DSTV, STEP, IFC, PDF en Excel via één canoniek model.
2. **Drawings & AI** — technische PDF’s lezen, controleren en genereren; AI alleen adviserend.
3. **Project & BOM** — complete IFC-/STEP-projecten opdelen in merken, onderdelen, inkoopdelen, bouten en lassen.
4. **Optimization & Production** — handelslengten, plaatnesting, voorraad, productieroutes en machinejobs.
5. **Platform** — projecten opslaan, gebruikers/rechten, audit, licenties, installer en later online samenwerking.

De geometrische kern blijft de enige bron van waarheid. AI mag classificeren, interpreteren en voorstellen doen, maar niet rechtstreeks NC1, STEP, IFC of machinecode vrijgeven.

---

## 2. Huidige uitgangspositie

### Gereed of aantoonbaar aanwezig in v0.5.1

- bestaande NC1 ↔ STEP-regressiebasis;
- converter-eigen IFC-payload en gecontroleerde focusroundtrips;
- Canonical Part Model schema 1.1;
- Trusted Converter PDF met embedded model en hashes;
- eenvoudige externe vector-PDF naar gereviewde plaat/strip;
- deterministische maatgrafiek;
- interactieve review met provenance/confidence;
- begrensde lokale/cloud-AI-laag;
- basis-GUI en CLI;
- Windows build- en installerscripts.

### Nog niet productierijp

- echte LO4-PDF als vaste regressietest;
- algemene profiel- en meer-aanzichtreconstructie;
- productiebrede OCR/scan/foto-import;
- volledige hidden-line-, snede-, detail- en maatplaatsingsengine;
- complete IFC-/STEP-projectimport met assemblies en onderdelen;
- projectopslag, projectboom, BOM en inkoop;
- uitgebreide onderdeleneditor en moderne gegevensgrid;
- deduplicatie, revisievergelijking en manufacturing hashes;
- handelslengte-optimalisatie en plaatnesting;
- voorraad, reststukken, machines en postprocessors;
- licenties, rollen, online jobmodel en echte Cloudflare-backend;
- native gebouwde en op een schone Windows-pc geteste installer.

---

## 3. Voorlopige technische intake van de nieuwe referentiebestanden

### Tekla IFC

Het aangeleverde IFC2X3-bestand bevat op STEP-entiteitsniveau exact de beoogde nulmeting:

- 353 `IfcElementAssembly`;
- 1.293 `IfcPlate`;
- 707 `IfcBeam`;
- 369 `IfcColumn`;
- 723 `IfcMechanicalFastener`;
- 2.654 `IfcFastener`;
- 38 `IfcFooting`;
- 19 `IfcBuildingElementProxy`;
- 3 `IfcSlab`.

Ook de waarden `MLO4`, `LO4`, `STRIP5*120` en `S235JR` zijn aanwezig. Dit maakt het bestand geschikt als harde semantische regressietest. Deze intake is nog geen volledige geometrische/projectimport; die wordt in fase 2 gebouwd en gevalideerd.

### Nieuwe STEP-bestanden

Alle drie de nieuwe bestanden zijn AP242 en bevatten volgens de bestandsstructuur één productrecord en één BREP-solid:

| Bestand | Structuur | Gebruik in tests |
|---|---|---|
| `Samenstel nieuw - 11864_Predeterminado (1).step` | één product, één solid | normale complexe partimport |
| `Samenstel nieuw - 11881_Predeterminado (1).step` | één product, één zeer complexe solid | performance-/stressregressie |
| `Samenstel nieuw - 2x voetplaat hoog.step` | één product, één solid | veilige fallback; niet op basis van de naam kunstmatig splitsen |

De importeur mag dus geen fictieve assemblyboom verzinnen. Alleen semantische relaties, losse solids of expliciet door de gebruiker bevestigde scheidingen mogen tot meerdere parts leiden.

---

## 4. Doelarchitectuur

```text
CWS Convertor Desktop / CLI / later API
                  │
                  ▼
        Application & Job Services
                  │
      ┌───────────┼────────────┐
      ▼           ▼            ▼
Project Store  Validation   Audit/Permissions
      │           │
      └──────┬────┘
             ▼
  Canonical Project Model 2.x
  ├─ Project
  ├─ Assemblies / merken
  ├─ Parts / onderdelen
  ├─ Purchased items
  ├─ Fasteners / welds
  ├─ Stock / remnants
  ├─ Operations
  └─ Machine jobs
             │
      ┌──────┼──────────────────────────┐
      ▼      ▼             ▼            ▼
  Importers  Exporters   Drawings     Optimization
  IFC/STEP   NC1/IFC/    PDF/AI       Bars/Nesting
  PDF/NC1    STEP/PDF
             │
             ▼
     Geometry / BREP Core
```

### Belangrijke technische keuze

De huidige conversiekern blijft behouden als headless bibliotheek. Voor de omvangrijke projectinterface wordt een moderne desktoplaag aanbevolen, bij voorkeur Qt/PySide met een OpenCascade-gebaseerde viewer. De bestaande Tkinter-interface blijft tijdelijk beschikbaar totdat de nieuwe interface functioneel gelijkwaardig is. Zo wordt geen werkende kern weggegooid, maar ontstaat wel ruimte voor dockable panels, grote grids, drag-and-drop, undo/redo en professionele 3D-selectie.

---

## 5. Bouwvolgorde

## Fase 0 — Baseline vastzetten, naam wijzigen en ontwikkelstraat herstellen

**Doel:** één controleerbare uitgangsversie voordat nieuwe projectfunctionaliteit wordt toegevoegd.

### Bouwen

- broncode uit v0.5.1 en Git-bundle samenbrengen in één echte repository;
- tag `v0.5.1-baseline` maken;
- alle zichtbare productnamen wijzigen naar **CWS Convertor**;
- executable-, installer-, map- en documentnamen aanpassen;
- interne compatibiliteitslagen behouden voor bestaande project-/payloadversies;
- repository opdelen in `core`, `importers`, `exporters`, `drawings`, `project`, `optimization`, `machines`, `ui`, `cli` en `tests`;
- dependency-lock, software bill of materials en reproduceerbare builds toevoegen;
- logging, foutcodes, crashdump en testresultaatformaten uniform maken.

### Testpoort

- alle bestaande v0.5.1-regressies blijven slagen;
- geen wijziging in bestaande NC1/STEP/IFC/PDF-uitvoer zonder verklaarde migratie;
- nieuwe naam zichtbaar in GUI, CLI, installer en rapporten.

### Resultaat

**CWS Convertor v0.6.0-alpha — betrouwbare basis.**

---

## Fase 1 — Canonical Project Model 2.x en projectopslag

**Doel:** van losse onderdelen naar één versieerbaar projectmodel.

### Bouwen

- `ProjectModel`, `Assembly`, `Part`, `PurchasedItem`, `Fastener`, `Weld`, `StockItem`, `Remnant`, `ProductionOperation`, `MachineProfile` en `MachineJob`;
- bronidentiteit, geometry hash en manufacturing hash;
- lokale en globale placements;
- provenance/confidence per veld;
- revisie-, vrijgave- en auditstatus;
- projectdatabase in SQLite;
- draagbaar projectpakket, bijvoorbeeld `.cwscproj`, met database, manifests, bronhashes, previews en audit;
- autosave, herstel, migraties en read-only openen van oudere schema’s;
- centrale jobmanager voor lange import-, export- en optimalisatietaken.

### Testpoort

- project opslaan, sluiten en exact heropenen;
- stabiele IDs en hashes na herimport;
- corrupte of onvolledige projecten veilig blokkeren;
- oude Canonical Part Model-data migreren zonder verlies.

### Resultaat

**CWS Convertor v0.6.0-beta — projectfundament.**

---

## Fase 2 — Semantische IFC-/STEP-projectimport

**Doel:** complete modellen betrouwbaar opdelen zonder geometrie of hiërarchie te verzinnen.

### Bouwen

#### Strategie A — semantische structuur

- IFC2X3/IFC4-hiërarchie, assemblies, containment, materials, propertysets, placements, bouten en lassen;
- STEP AP242 product definitions, occurrences, transforms, namen, kleuren en attributen;
- één bronentity koppelen aan één stabiele projectentity.

#### Strategie B — losse solids

- compounds naar afzonderlijke solids splitsen;
- lokale geometrie normaliseren;
- identieke solids op verschillende placements groeperen;
- spiegelvarianten afzonderlijk houden.

#### Strategie C — gefuseerd/onduidelijk

- alleen voorstellen voor mogelijke scheidingen;
- confidence en visuele scheidingsvlakken;
- handmatige samenvoeg-/splitsreview;
- productie-export blokkeren tot bevestiging.

#### Performance

- achtergrondjobs, voortgang, annuleren en hervatten;
- caching van triangulatie en thumbnails;
- lazy loading van properties en geometrie;
- geheugen- en tijdslimieten.

### Harde regressies

- Tekla IFC opent zonder crash en behoudt de gemeten classificatie-orde;
- MLO4/LO4, profiel, materiaal en bout-/gatinformatie zijn doorzoekbaar;
- bouten en lassen worden niet als gewone maakdelen geteld;
- de drie nieuwe STEP-bestanden worden elk als één product/solid geïmporteerd;
- `2x voetplaat hoog` wordt niet automatisch gesplitst;
- 11881 wordt performance- en geheugentest.

### Resultaat

**CWS Convertor v0.7.0-alpha — betrouwbare projectimport.**

---

## Fase 3 — Identiteit, classificatie en BOM

**Doel:** elk object krijgt een gecontroleerde productiebetekenis.

### Bouwen

- deterministische classificatieregels voor maakdeel, inkoopdeel, fastener, weld, assembly, niet-staal, referentie en onbekend;
- profiel- en materiaalmapping via databases en bedrijfsspecifieke aliassen;
- AI uitsluitend als voorstel bij onduidelijke namen/properties;
- part-, assembly-, inkoop-, bouten-, lassen- en materiaal-BOM;
- hoeveelheid, massa, oppervlak en coatingoppervlak;
- bronmark, assembly mark, part position en aantallen;
- conflictregels voor hetzelfde merk met andere geometrie, gelijk deel met ander materiaal en spiegelvarianten;
- classificatiesjablonen per bedrijf.

### Testpoort

- MLO4/LO4 correct gekoppeld;
- herhaalde merken als aantallen gegroepeerd;
- onbekende of conflicterende delen zichtbaar geblokkeerd;
- BOM-sommen sluiten aan op projecttotalen;
- AI-classificatie is altijd herleidbaar en handmatig overschrijfbaar.

### Resultaat

**CWS Convertor v0.7.0-beta — bruikbare projectstructuur en BOM.**

---

## Fase 4 — Moderne CWS-projectinterface en onderdeeleditor

**Doel:** een overzichtelijke, snelle en visueel professionele desktopapplicatie.

### Hoofdnavigatie

```text
Start
Convertor
Project / Productie
PDF / Tekening
BOM / Excel
Optimalisatie
Voorraad
Machines
Audit / Rapporten
Instellingen
```

### Projectscherm

```text
┌ CWS Convertor ─ Project ─ Revisie ─ Validatiestatus ─ Gebruiker ┐
├──────────────┬──────────────────────────┬────────────────────────┤
│ Modelboom    │ Onderdelen-/merkengrid   │ 3D / 2D / Eigenschappen│
│ locaties     │ filter, sorteer, groepeer│ isolate, explode, compare│
│ assemblies   │ batchacties              │ warnings, preview         │
│ parts        │ statussen                │ export                    │
│ inkoop       │                          │                           │
└──────────────┴──────────────────────────┴────────────────────────┘
```

### Onderdeeleditor

Tabbladen:

- Algemeen;
- Extra informatie;
- Bewerkingen;
- Hoeken;
- Gaten;
- Coderingen/markeringen;
- Prijzen;
- Bewerkingstijden;
- Validatie en herkomst.

### Eigenschappengrid

- kolommen slepen;
- oplopend/aflopend sorteren;
- groeperen;
- veldkeuze;
- filters;
- footers en totalen;
- optimale kolombreedte;
- opgeslagen schermindelingen per gebruiker/bedrijf;
- Excel/CSV-export;
- virtualisatie voor duizenden regels;
- selectie synchroniseren met viewer.

### Vormgeving

- naam en branding: **CWS Convertor**;
- industriële, rustige basis met één CWS-accentkleur;
- licht en donker thema;
- consistente statuskleuren: groen gevalideerd, oranje review, rood geblokkeerd, blauw informatief;
- compacte datadichtheid zonder kleine onleesbare tekst;
- duidelijke primaire acties en vaste validatiebalk;
- geen kopie van Trimble Connect, wel dezelfde professionele bedieningskwaliteit.

### Testpoort

- grote IFC blijft responsief;
- selectie werkt bidirectioneel tussen boom, grid en 3D-view;
- kolomindeling en filters worden onthouden;
- wijzigingen hebben undo/redo en audit;
- keyboard- en muisbediening zijn consistent.

### Resultaat

**CWS Convertor v0.8.0-alpha — projectverkenner en editor.**

---

## Fase 5 — Per-part/per-merk exports en technische tekeningen

**Doel:** gecontroleerde productieartefacten vanuit het projectmodel.

### Bouwen

- per onderdeel: NC1, STEP, IFC, vector-PDF, DXF waar passend, Excel/CSV, label en manifest;
- per merk: assembly-PDF, assembly-IFC/STEP, part-PDF’s, NC-map, bouten-/las-/inkooplijst en ZIP-productiepakket;
- configureerbare bestandsnaamsjablonen en conflictcontrole;
- manifest met gemaakt, overgeslagen en geblokkeerd per object;
- automatische part drawing en assembly drawing;
- title blocks, huisstijl, revisies, stuklijsten en QR/ID;
- voortbouwen op Trusted Converter PDF en dimension graph;
- NC1 alleen na canonical → NC1 → re-import → vergelijking.

### Tekeningengine uitbreiden

- profiel- en meer-aanzichtprojecties;
- verborgen lijnen en hartlijnen;
- eind-/doorsnedeaanzichten;
- detailaanzichten;
- collision-free maatplaatsing;
- handmatig verplaatsbare en opnieuw te ankeren maatobjecten;
- A4/A3/A2/A1 en schaalkeuze;
- concept/controle/vrijgegeven/vervallen.

### Testpoort

- geselecteerd IFC-onderdeel kan geïsoleerd en geëxporteerd worden;
- ieder exportbestand is aan part/assembly/revisie gekoppeld;
- gelijke marks met andere geometrie blokkeren naamconflicten;
- PDF en productiemodel bevatten dezelfde maatwaarden en BOM.

### Resultaat

**CWS Convertor v0.8.0-beta — productie-exportpakket.**

---

## Fase 6 — PDF/AI-module compleet maken

**Doel:** externe tekeningen veilig en breed bruikbaar maken.

### Bouwen

- echte `Pos LO4 - LOSSE PLAAT.pdf` als vaste testfixture;
- vectorprofielen, meerdere orthogonale aanzichten en featurecorrespondentie;
- scans: deskew, perspectiefcorrectie, ruisreductie en OCR-bounding boxes;
- symboolherkenning voor Ø, R, hoeken, toleranties, las- en gatnotaties;
- titelblok-/tabeltemplates per bedrijf;
- 2D/3D-review met lijnen herclassificeren, maten koppelen en contourpunten corrigeren;
- AI voor classificatie, semantiek, conflictsamenvatting en layoutvoorstel;
- lokale modus als standaard, cloud alleen na toestemming;
- alle onzekerheid via confidence, provenance en concrete vragen;
- productie-export blijft geblokkeerd bij ontbrekende kritische gegevens.

### Testpoort

- LO4-bron → reviewed model → NC1/STEP/IFC/PDF;
- vector-, scan-, hybride- en negatieve tests;
- open contour, ontbrekende dikte, conflictmaat en onduidelijke gatdiameter blokkeren;
- AI-output kan geen productiegeometrie of machinecode injecteren.

### Resultaat

**CWS Convertor v0.9.0-alpha — complete tekeningenworkflow binnen vastgestelde scope.**

---

## Fase 7 — Geometrische deduplicatie en revisievergelijking

**Doel:** identieke onderdelen en wijzigingen betrouwbaar herkennen.

### Bouwen

- placement-onafhankelijke geometry hash;
- manufacturing hash inclusief materiaal, features, referentiezijden, spiegelstatus en coating;
- groepen voor exact gelijk, gespiegeld en bijna gelijk;
- IFC GlobalId/STEP occurrence/marks combineren met geometrie;
- revisiecompare: toegevoegd, verwijderd, gewijzigd, alleen verplaatst;
- impact op BOM, materiaal, tekeningen, optimalisatie en machinejobs;
- alleen artefacten hergebruiken wanneer manufacturing hash gelijk is.

### Testpoort

- hashes stabiel over herimport;
- placementwijziging verandert geen manufacturing hash;
- relevante featurewijziging invalideert NC, optimalisatie en job;
- conflict tussen mark en geometrie is blokkerend.

### Resultaat

**CWS Convertor v0.9.0-beta — revisie- en identiteitsbeheer.**

---

## Fase 8 — Handelslengte-optimalisatie

**Doel:** reproduceerbare 1D cutting-stockplanning.

### Bouwen

- handelslengten, kerf, trims, minimumrest, klemzones, zaaghoeken, heats en voorraad;
- exacte solver voor kleine sets en gecontroleerde heuristiek voor grote sets;
- doelen: kosten, afval, aantal staven, setups, reststukgebruik en doorlooptijd;
- zaagplannen, balkvisualisatie, labels, Excel/PDF en machine-neutraal jobmanifest;
- optimaliteitsstatus, bound, gap, rekentijd en vereenvoudigingen rapporteren.

### Testpoort

- materiaalbalans sluit exact;
- geen materiaal-/heat-menging tegen regels;
- onmogelijke orders worden verklaard;
- claim “optimaal” alleen bij bewezen oplossing.

### Resultaat

**CWS Convertor v0.10.0-alpha — profielenoptimalisatie.**

---

## Fase 9 — Plaatnesting

**Doel:** veilige 2D-nesting zonder wijziging van onderdeelgeometrie.

### Bouwen

- plaatformaten, restplaten, kerf, marge, rotatie/spiegelrestricties en walsrichting;
- contouren met binnencontouren;
- nestingresultaat, plaat-ID, benutting, snijlengte, pierces en restcontour;
- DXF/neutral job output;
- plugin/postprocessorgrens voor specifieke snijmachines;
- roundtripvergelijking van elk geplaatst onderdeel.

### Testpoort

- geen overlaps;
- alle aantallen aanwezig;
- topologie en manufacturing hash gelijk aan bron;
- materiaal, kwaliteit en dikte correct;
- restplaat reproduceerbaar.

### Resultaat

**CWS Convertor v0.10.0-beta — plaatoptimalisatie.**

---

## Fase 10 — Machineprofielen, routeplanning en veilige postprocessors

**Doel:** machinejobs voorbereiden zonder onveilige universele codegenerator.

### Bouwen

- capability matrix per machine;
- neutral manufacturing job;
- versieerbaar postprocessorframework;
- machinegeschiktheid, tools, klemzones en featurechecks;
- preview, simulatie, operatorcontrole en digitale vrijgave;
- checksums, immutable audit en ontvangst/status;
- eerst alleen test-/exportmap, pas later gecontroleerde netwerkoverdracht;
- één expliciet gevalideerde adapter per merk/controller.

### Testpoort

- ongeschikte machine weigert job;
- unsupported feature blijft zichtbaar;
- simulatie en bevoegde vrijgave verplicht;
- jobwijziging verandert checksum;
- testomgeving kan geen echte machine aansturen.

### Resultaat

**CWS Convertor v0.11.0 — gevalideerd machineframework; alleen gevalideerde adapters actief.**

---

## Fase 11 — Voorraad, inkoop, planning, labels en traceability

**Doel:** complete materiaal- en productievoorbereiding.

### Bouwen

- voorraad, handelslengten, plaatformaten, reststukken, locaties en reserveringen;
- leveranciers, prijzen, levertijden, MOQ en alternatieven;
- materiaalcertificaten/heats;
- inkoopadvies en orderbehoefte;
- productieorders, routes, labels, QR/barcodes, kwaliteitsmetingen en herwerk;
- planning en queue;
- rollen en bevoegdheden;
- project-/bedrijfsisolatie en audit.

### Testpoort

- netto/bruto/voorraad/inkoopbalans sluit;
- reststuk krijgt unieke identiteit;
- traceability vanaf bronmodel tot label en job;
- onbevoegde gebruiker kan niet vrijgeven.

### Resultaat

**CWS Convertor v0.12.0 — productievoorbereiding.**

---

## Fase 12 — Licenties, online omgeving, Windows-release en definitieve acceptatie

**Doel:** distributie en bedrijfsgebruik zonder technische installatiehandelingen.

### Modulair licentiemodel voorbereiden

- **Core** — basisconvertor en viewer;
- **Drawings & AI** — PDF/tekeningen en AI-review;
- **BOM & Excel** — hoeveelheden en rapportages;
- **Project & Production** — complete modelstructuur en productievoorbereiding;
- **Optimization** — bars en nesting;
- **Machine** — postprocessors en jobs;
- **Enterprise/Cloud** — multi-user, online jobs en integraties.

Prijzen worden later vastgesteld; de entitlementgrenzen worden nu al schoon in de architectuur aangebracht.

### Platform

- lokale signed license en optionele online activatie;
- gebruikers, bedrijven en rollen;
- API/jobmodel;
- Cloudflare-frontend en beveiligde backend/jobopslag;
- geen geometrieclaim zolang server-side converter niet echt draait;
- later MES/OPC UA voor status en queue, apart van machinecode.

### Release

- één `CWS_Convertor_Setup_<versie>_x64.exe`;
- portable ZIP;
- runtime en dependencies ingebouwd;
- file associations en contextmenu’s;
- code signing;
- updatekanaal;
- schone Windows x64-test zonder Python;
- performance- en hersteltests;
- handleiding, technische documentatie, SBOM, checksums en beperkingenrapport.

### Eindpoort

- volledige acceptatieset groen;
- geen open kritische geometrie- of veiligheidstekorten;
- alle mislukte/overgeslagen objecten verklaard;
- installer, installed app en portable build getest;
- alleen daadwerkelijk gevalideerde machineformaten als ondersteund vermeld.

### Resultaat

**CWS Convertor 1.0 — productierijpe, controleerbare release.**

---

## 6. Release-overzicht

| Release | Hoofdresultaat |
|---|---|
| 0.6 | baseline, branding, projectmodel en opslag |
| 0.7 | semantische IFC/STEP-import, classificatie en BOM |
| 0.8 | projectinterface, editor, exports en technische tekeningen |
| 0.9 | complete PDF/AI-scope, deduplicatie en revisies |
| 0.10 | handelslengten en plaatnesting |
| 0.11 | machineprofielen, postprocessors en vrijgave |
| 0.12 | voorraad, inkoop, planning en traceability |
| 1.0 | licenties, installer, documentatie en volledige acceptatie |

---

## 7. Harde bouwregels

1. Geen nieuwe dashboardlaag vóór het projectmodel en de importtests bestaan.
2. Geen kunstmatige STEP-assemblyboom zonder bronbewijs.
3. Geen NC1 vanuit vrije AI-output.
4. Geen machinejob vóór canonical- en roundtripvalidatie.
5. Geen “optimale” claim zonder bewijs of gerapporteerde gap.
6. Geen nesting die de brongeometrie wijzigt.
7. Geen hergebruik van oude productie-uitvoer na wijziging van manufacturing hash.
8. Geen echte machineoverdracht vóór gevalideerde postprocessor, simulatie en bevoegde vrijgave.
9. Geen eindgebruikersrelease zonder schone Windows-test.
10. Elke fase levert code, tests, rapporten en checksums; niet alleen schermen of documenten.

---

## 8. Eerste uitvoerbare bouwbatch

De eerste concrete bouwbatch bestaat uit:

1. v0.5.1 repository reconstrueren en taggen;
2. alle zichtbare branding wijzigen naar **CWS Convertor**;
3. architectuurmappen en compatibiliteitsfacades aanbrengen;
4. Canonical Project Model 2.0 ontwerpen en migratietests maken;
5. SQLite-projectopslag en `.cwscproj`-pakket toevoegen;
6. Tekla IFC-regressietest vastleggen met entity counts en MLO4/LO4-zoektests;
7. AP242-regressietests maken voor 11864, 11881 en `2x voetplaat hoog`;
8. pas daarna de semantische IFC-/STEP-importer implementeren.

Deze batch vormt de vrijgavepoort voor alle latere UI-, BOM-, optimalisatie- en machinefuncties.
