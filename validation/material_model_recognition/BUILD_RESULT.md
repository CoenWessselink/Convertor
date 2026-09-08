# Materiaal- en modelherkenning — opleverresultaat

Datum: 8 september 2026. Status: **implementatie uitgebreid, volledige acceptatie ONVOLLEDIG, installatievrijgave NEE**.

## Wat is ingebouwd

- 76 catalogusmaterialen, exacte codes en expliciete aliassen; geen fictieve staalfallback of materiaalkwaliteit uit alleen geometrie.
- IFC-materiaalrelaties, type-overerving, samengestelde materialen en conflicten met herleidbaar bronbewijs.
- Automatische importclassificatie, brongebonden STEP/extrusieherkenning en veilige promotie naar een te beoordelen Workbench-voorstel.
- PDF/DXF-tekstkandidaten, materiaalreview, bulkpreview, bevestigen/afwijzen en bewaakte undo/redo.
- Blokkades op onbekend of tegenstrijdig materiaal, ontbrekende dichtheid, onvolledig profielbewijs en verouderde bron-/productie-identiteit.
- Transactionele STEP→NC1-uitvoer: een fout wist geen bestaand doelbestand. Materiaalafhankelijke massa en behoud van brongewicht.
- Snellere exacte profielcatalogusindex. Decimalen blijven betekenisvol: `SHS20x20x15` is niet `SHS20x20x1.5`. Alle 2.849 bestaande letterlijke catalogusnamen en aliassen behouden hun resultaat.
- Reproduceerbare tests, bronhashen en strikte Windows-CI-gates vóór de bestaande installatiebuilds.

## Werkelijk uitgevoerde eindcontrole

Opdracht:

```text
python tools/run_material_model_recognition_acceptance.py --require-native --output validation/material_model_recognition --timeout 120
```

Python 3.12.13 op Linux. De broncode bleef tijdens de hele run ongewijzigd.

| Controle | Resultaat |
| --- | ---: |
| Verplichte suites | 39 |
| Volledig geslaagde suites | 31 — 79,49% |
| Geblokkeerde suites | 7 |
| Suite met native skips | 1 |
| Geslaagde logische tests | 243 |
| Overgeslagen logische tests | 2 |
| Testfouten / errors / time-outs | 0 |
| Actuele echte UI-screenshots | 0 |
| Volledige acceptatie / installatievrijgave | Nee / Nee |

Het testaandeel in de JSON is 243/245 = 99,18%; de twee skips blijven in die noemer. Geblokkeerde suites krijgen geen verzonnen aantal niet-uitgevoerde tests. Deze percentages meten testbewijs, niet de gereedheid van het hele programma of universele herkenningsnauwkeurigheid.

| Testgebied | Volledig geslaagde suites | Bewijsdekking |
| --- | ---: | ---: |
| Materiaalcatalogus | 1/1 | 100% |
| IFC-semantiek | 3/3 | 100% |
| STEP-semantiek | 1/1 | 100% |
| Classificatie | 5/5 | 100% |
| Projectregressies | 5/5 | 100% |
| Modelherkenning incl. native gate | 4/5 | 80% |
| Conversiebeleid incl. native gate | 2/3 | 66,67% |
| PDF/DXF incl. native modelgate | 2/3 | 66,67% |
| Materiaalreview incl. Qt/persistentie | 1/3 | 33,33% |
| Workbench/productievrijgave | 6/9 | 66,67% |
| Integriteit acceptatierunner | 1/1 | 100% |

## Praktijkcorpus

De machineleesbare eindmeting staat in `reference/corpus.json`; de meting vóór de profielindexoptimalisatie staat apart in `reference/corpus_before_profile_index.json`. Het HVPC-bronpakket wordt alleen gelezen en in een tijdelijk project opnieuw geïmporteerd. De 26 STEP-regressies zijn gegenereerde/synthetische bronnen, geen onafhankelijk geannoteerde externe klantmodellen.

| HVPC-eindmeting | Resultaat |
| --- | ---: |
| Onderdelen expliciet afgehandeld | 3.419/3.419 — 100% |
| Materiaal in catalogus gevonden | 3.407/3.419 — 99,65% |
| Tegenstrijdig materiaalbewijs | 12; alle 12 geblokkeerd |
| Exacte profielcatalogusmatch | 2.248/3.419 — 65,75% |
| Cataloguskwaliteit bevestigingsmiddelen | 2.282/2.306 — 98,96% |
| Automatische classificatie / review vereist | 2.350 / 1.069 |
| Onderdelen met productievrijgave | 0 |
| Bronpakket en gecontroleerde kerncode ongewijzigd | Ja |

De 1.171 ontbrekende profielcatalogushits bevatten vooral klantspecifieke plaat-/stripmaten, daarnaast inkoopartikelen en onopgeloste profielen. Ze bewijzen niet dat hun geometrie onherkenbaar is; deze corpusrun meet geen native geometrische equivalentie. Alle 26 STEP-regressies zijn veilig verwerkt zonder materiaal te verzinnen; zij leveren semantisch geen materiaal-/profielcatalogusmatch op.

HVPC-import plus classificatie daalde in de twee gemeten runs van 211,417 naar 109,415 seconden (ongeveer 48% korter). De volledige HVPC-controle ging van 286,330 naar 134,249 seconden. Dit is een waarneming op dezelfde runtime, geen geïsoleerde benchmark of Windows-prestatiegarantie; tijdens de tweede run draaide ook de korte eindacceptatie. De volledige 27-bronnencorpusrun duurde 163,429 seconden en voldeed aan zijn veiligheidschecks.

Een exacte catalogustreffer bewijst geen geometrische equivalentie, chemische samenstelling, materiaalcertificaat of productiegeschiktheid. De corpuscontrole houdt onopgeloste waarden en exportblokkades afzonderlijk bij.

## Bronbinding en overdracht

De test controleerde de volledige toenmalige werkboom op basiscommit `66e1f4e11787ac75e0aae97ece14e8dd917849b7`, inclusief de nieuwe bronwijzigingen. De definitieve codebytes zijn gebonden door:

```text
source_tree_sha256 = 22064be48d1b3e88d2e5d3a088723cb50c859c2ca31827c13bf865e682663e69
source_file_count = 978
```

`SOURCE_FINGERPRINT.json` bevat de afzonderlijke bestanden. Gegenereerde validatiebestanden tellen niet mee in deze bronhash. Een latere commit-ID is geen bewering dat GitHub-CI al is uitgevoerd: er is in deze oplevering niet gepusht en geen externe CI-run gecontroleerd.

Zie `docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md` voor de volledige installatie-overdracht. Installeer in de Windows-buildomgeving de bestaande locked dependencies, herhaal de strikte herkenningsgate op de bedoelde commit en voer daarna alle bestaande programmabrede releasegates uit. De drie aangepaste CI-workflows bewaren hun nieuwe bewijs onder `build/material_model_recognition/`.

## Nog te bewijzen of uit te breiden

- CadQuery, OCP, IfcOpenShell, PySide6 en ezdxf ontbreken hier. Native CAD/roundtrips, Qt-schermen en screenshots zijn niet bewezen.
- Er is geen EXE, portable of installer gebouwd of getest. Schone installatie, eerste start, opslaan/heropenen en uninstall blijven releasevoorwaarden.
- De uitgestelde STEP-projectactie is begrensd tot één onderdeel/solid; multiparts en onzekere CUSTOM-doorsneden blijven geblokkeerd voor automatische promotie.
- Semantische IGES/IGS- en losse BREP-import, binaire DXF en OCR voor raster-PDF zijn niet toegevoegd.
- Documentkandidaten moeten aan het juiste onderdeel gekoppeld en bevestigd worden. De 76 materialen vormen geen universele materiaalinventaris.
- Grote-modelgeheugen bij volledige UI-snapshots en representatieve nauwkeurigheid op onafhankelijk geannoteerde praktijkmodellen vereisen aanvullende metingen.

Geen van deze open punten mag als een geslaagde test of 100% productgereedheid worden gepresenteerd.
