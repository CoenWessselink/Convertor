# CWS Convertor 0.6.0-beta

**CWS Convertor** is een local-first Windows-desktopapplicatie en CLI voor:

- NC1/DSTV ↔ STEP ↔ IFC;
- Trusted Converter PDF en gecontroleerde externe PDF-analyse;
- hoeveelheden en Excel;
- draagbare projectbestanden voor complete IFC-/STEP-modellen.

Versie 0.6 voegt het fundament voor **Project / Productie** toe zonder de bewezen v0.5.1-conversiekern te vervangen.

## Veiligheidsarchitectuur

Alle productie-uitvoer loopt via canonieke modellen en deterministische validatie:

```text
PDF / NC1 / STEP / IFC
          ↓
Canonical Part Model
          ↓
NC1 / STEP / IFC / PDF / Excel

Complete IFC / STEP
          ↓
Canonical Project Model 2.0
          ↓
Assemblies / parts / BOM / productie (gefaseerd en gevalideerd)
```

AI mag documentsemantiek, classificatievoorstellen, confidence, conflicten en controlevragen leveren. AI schrijft geen ongecontroleerde NC1-regels, CAD-geometrie of machinecode. Kritische onzekerheid sluit de productiepoort.

## Nieuw in 0.6.0-beta

### CWS-productidentiteit

De zichtbare productnaam, GUI, CLI, build, installer en projectbestandskoppeling gebruiken nu **CWS Convertor**. Legacy payloadmarkers blijven bewust leesbaar zodat v0.4/v0.5 IFC- en Trusted PDF-bestanden niet worden gebroken.

### Canonical Project Model 2.0

Het projectmodel bevat voorbereidende entiteiten voor:

- projectbronnen en provenance;
- assemblies/merken;
- maakdelen en inkoopdelen;
- bevestigingsmiddelen en lassen;
- voorraad en reststukken;
- productiehandelingen;
- machineprofielen en machinejobs;
- validatie, revisies en auditlog.

Identiteit wordt gescheiden in bronidentiteit, placement-onafhankelijke geometry hash en manufacturing hash. Gespiegelde of materiaaltechnisch verschillende delen kunnen daardoor niet ongemerkt als hetzelfde productiedeel worden behandeld.

### Draagbaar `.cwscproj`-projectbestand

Een CWS-project is één ZIP-container met:

- `manifest.json`;
- `project.sqlite` met het canonieke projectsnapshot;
- optioneel ingesloten IFC-/STEP-bronnen;
- hash-gecontroleerde previews;
- SHA-256 per entry;
- ZIP-CRC- en SQLite-integriteitscontrole;
- revisiehistorie en auditlog;
- veilige, lichtgewicht autosave en herstel.

Opslaan gebeurt atomair. Een mislukte batchimport laat het bestaande project byte-identiek staan.

De Project Foundation-validatie op het grote Tekla IFC-model en de drie AP242 STEP-modellen bevat **117/117 geslaagde controles**. Daarbij zijn ook embedded bronnen/previews, autosaveherstel, CLI, compilecontrole en GUI-start getest.

### Deterministische importnulmeting

De huidige projectfase kiest veilig de importroute en legt bewijs vast:

1. **Strategy A — semantic structure** voor IFC/STEP met bruikbare productstructuur;
2. **Strategy B — separate solids** wanneer alleen losse BREP-solids betrouwbaar zijn;
3. **Strategy C — fused/ambiguous** als expliciete reviewroute.

Bronnamen leiden nooit op zichzelf tot opsplitsing. Het bestand `2x voetplaat hoog.step` blijft dus één product en één solid totdat geometrie of gebruiker anders bevestigt.

### Project / Productie-interface

Het functionele tabblad kan:

- een project maken, openen en opslaan;
- IFC- en STEP-bronnen in een achtergrondtaak analyseren;
- bronbestanden optioneel in het project insluiten;
- nulmetingen exporteren;
- ingesloten bronnen veilig uitpakken;
- bronnen sorteren en details/waarschuwingen tonen;
- projectstatus, gedetecteerde aantallen en opslag samenvatten;
- periodiek autosaven.

De getoonde gegevens komen uit hetzelfde Project Model en dezelfde service als de CLI.

## Bewezen referentienulmeting

### Tekla IFC2X3

| Objectgroep | Aantal |
|---|---:|
| Assemblies | 353 |
| Platen | 1.293 |
| Balken/liggers | 707 |
| Kolommen | 369 |
| Mechanische bevestigingsmiddelen | 723 |
| Las-/fastenerobjecten | 2.654 |
| Funderingsobjecten | 38 |
| Building-element proxies | 19 |
| Slabs | 3 |

De nulmeting vindt tevens `MLO4`, `LO4`, `STRIP5*120`, `S235JR`, lengte 160 mm, circa 0,6 kg assemblygewicht, diameter 14 mm en herhaalde marks `LA1`, `A1`, `MP1` en `MP2`.

### AP242 STEP

De drie nieuwe referentiebestanden bevatten ieder:

- één productrecord;
- één BREP-solid;
- nul assembly usage-relaties;
- geldige CAD-geometrie bij de volledige validatierun.

Daarom maakt de importer geen fictieve assemblystructuur.

## Productiepoort in deze release

Deze beta **registreert en valideert de bronintake**, maar materialiseert het grote IFC-model nog niet volledig als actieve ProjectModel-assemblies/parts. De STEP-solids worden evenmin automatisch als NC1-geschikte maakdelen vrijgegeven. Per bron wordt daarom een blokkerende `semantic_import_pending`-status opgeslagen.

Dat betekent dat complete-model BOM-, NC1-, optimalisatie- en machine-export bewust nog niet beschikbaar zijn. De volgende fase is semantische IFC/STEP-import en betrouwbare part-/assembly-identiteit.

## Bestaande conversiekern behouden

De v0.5.1-functionaliteit blijft aanwezig:

- NC1 → STEP: 24/24 regressies;
- STEP → NC1: 19/19 regressies;
- NC1 → IFC → STEP → NC1: 4/4 focusroundtrips;
- STEP → IFC → NC1 → STEP: 4/4 focusroundtrips;
- Trusted PDF-roundtrips;
- deterministische maatgrafiek en interactieve PDF-review;
- begrensde optionele AI-laag;
- hoeveelheden en Excel.

## GUI starten uit bron

Alleen voor ontwikkelaars:

```text
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python app.py
```

Tabbladen:

- Convertor;
- Project / Productie;
- PDF / Tekening;
- Visuele vergelijking;
- Profielendatabase;
- Hoeveelheden & Excel.

## CLI

Projectbasis:

```text
CWS_Convertor_CLI.exe --version
CWS_Convertor_CLI.exe inspect-model model.ifc model.step --json-report baseline.json
CWS_Convertor_CLI.exe project-new project.cwscproj --name "Mijn project"
CWS_Convertor_CLI.exe project-import-baseline project.cwscproj model.ifc model.step
CWS_Convertor_CLI.exe project-info project.cwscproj --json
CWS_Convertor_CLI.exe project-sources project.cwscproj --json
CWS_Convertor_CLI.exe project-verify project.cwscproj --json
CWS_Convertor_CLI.exe project-export-json project.cwscproj -o project-model.json
CWS_Convertor_CLI.exe project-extract-source project.cwscproj <source-id> -o bron.ifc
CWS_Convertor_CLI.exe project-recover project.cwscproj -o hersteld.cwscproj
CWS_Convertor_CLI.exe project-migrate oud.cwscproj -o nieuw.cwscproj
```

Bestaande conversies:

```text
CWS_Convertor_CLI.exe nc1-to-step input.nc1 -o output
CWS_Convertor_CLI.exe step-to-nc1 input.step -o output
CWS_Convertor_CLI.exe nc1-to-pdf input.nc1 -o output
CWS_Convertor_CLI.exe pdf-analyze drawing.pdf -o analyse --ai-provider local-rules
CWS_Convertor_CLI.exe pdf-to-ifc reviewed_trusted.pdf -o output
CWS_Convertor_CLI.exe excel model.ifc model.step -o hoeveelheden.xlsx
```

## Windows-release

De buildstraat gebruikt Python 3.12 x64 als ontwikkelruntime en levert uiteindelijk:

```text
CWS_Convertor_Setup_0.6.0-beta_x64.exe
CWS_Convertor_Portable_0.6.0-beta_x64.zip
SHA256SUMS.txt
```

De eindgebruiker heeft geen Python, pip, venv of terminal nodig. In deze Linux-ontwikkelomgeving is geen native Windows-EXE gebouwd; de PyInstaller/Inno Setup-workflow moet op Windows worden uitgevoerd en op een schone Windows 10/11 x64-installatie worden geverifieerd.

## Belangrijkste brononderdelen

```text
cws_convertor/product.py          centrale naam en versie
cws_convertor/project/model.py    Canonical Project Model 2.0
cws_convertor/project/storage.py  .cwscproj ZIP+SQLite-opslag
cws_convertor/project/baseline.py IFC/STEP-nulmeting en routekeuze
cws_convertor/project/service.py  gedeelde GUI/CLI-projectservice
cws_convertor/project/jobs.py     annuleerbare achtergrondtaken
project_tab.py                    functionele Project/Productie-GUI
cli.py                            conversie- en project-CLI
```

## Volgende bouwfase

1. semantische IFC Strategy A-import met relaties, placements, properties, materialen, bouten en lassen;
2. STEP Strategy A/B-import met product occurrences en losse solids;
3. stabiele assembly-/part-identiteit en groepering;
4. classificatie en BOM;
5. daarna pas per-part/per-merk productie-export.
