# Materiaal- en modelherkenning — bouwoverdracht

## Doel en harde grens

Iedere ingelezen modelcomponent moet expliciet behandeld worden: herkend met herleidbaar bewijs, als kandidaat aangeboden, of als onopgelost/geconflicteerd geblokkeerd. Het programma mag geen staalsoort, aluminiumtoestand, materiaalsterkte of dichtheid verzinnen omdat een geometrie op een bekend extrusieprofiel lijkt.

Een geometrisch bewezen profiel is niet hetzelfde als een bewezen materiaalkwaliteit. Een 100% geslaagde acceptatiesuite bewijst alleen de omschreven regressiegevallen, niet dat elk wereldwijd materiaal of willekeurig beschadigd model automatisch herkend wordt.

## Onderdelen van deze build

| Onderdeel | Implementatie en controle |
| --- | --- |
| Materiaalcatalogus en resolver | `materials.json`, `material_database.py`, `cws_convertor/material_resolution.py`: exacte codes, expliciete aliassen, confidence, reden en bron; onbekend blijft onbekend. |
| Hoeveelheden en massa | `quantities.py`: geen stilzwijgende staalfallback; massa alleen wanneer materiaal en toegestane dichtheid beschikbaar zijn. |
| IFC-bronnen | `cws_convertor/importers/ifc_project.py`: bronrelaties, type-informatie, materiaalstructuren en conflicten; herkomst wordt bewaard. |
| Native IFC-materiaalbinding | `ifc_native.py`: materiaal per object binden; geen eerste-declaratie-fallback, geen staaletiket voor aluminium en geen verzonnen materiaal bij leeg bronveld. De serializer-unitcontrole is geen native CAD-geometriebewijs. |
| Classificatie bij import | `cws_convertor/project/service.py` en `classification.py`: classificatie na semantische import; onderscheiden beoordeling, bevestiging en conflicten. |
| STEP en extrusies | `cws_convertor/manufacturing_interpreter/` en `importers/step_project.py`: geometrie/profielherkenning apart van materiaalbewijs; stabiele bronbinding en cache; onveilige promotie blokkeren. |
| Conversieroutes zonder stilzwijgende defaults | CLI, applicatie, conversieservice, IFC-conversie en viewer-roundtrip: bronmateriaal of expliciete gebruikerstoewijzing behouden; een leeg veld wordt geen standaardstaal. Pure dispatch-/beleidtests zijn gescheiden van werkelijke CAD-conversies. |
| Veilige NC1-uitvoer | STEP→NC1 valideert in staging op hetzelfde bestandssysteem en vervangt het doel pas na succes. Fouten behouden bestaande uitvoer; bron en doel mogen geen identiek bestand zijn. |
| PDF/DXF-kandidaten | `cws_convertor/importers/source_material_evidence.py`: tekst/metadata met bronlocatie; geen materiaalkwaliteit afleiden uit kleur of geometrie. Kandidaten vragen beoordeling. |
| Materiaalreview | `cws_convertor/ui/material_review.py` en Qt-werkruimte: bewijs, cataloguskandidaten, reden, bevestigen/afwijzen, bulkpreview en bewaakte undo. |
| Productievrijgave | Workbench- en exportgates: materiaal/profielbevestiging, confidence, productie-identiteit en bestaande geometrie-/roundtripvoorwaarden. |
| Reproduceerbare controle | `tools/run_material_model_recognition_acceptance.py`: subprocess per suite, JSON per test, logs, dependencies en bronfingerprint. |

De geselecteerde STEP-herkenning is beschikbaar via **Bewerken → Extra info → STEP-profiel herkennen**. De achtergrondtaak werkt op een losse projectsnapshot; wijzigingen worden alleen op de UI-thread overgenomen als project, onderdeel en bron nog overeenkomen. Gestarte Workbench-revisies en bevestigde onderdelen worden behouden. Het service-equivalent is `ProjectSession.recognize_deferred_step_sources(...)` en de gelijknamige methode op `ProjectService` voor een projectpad.

De IFC-tessellatieserializer schrijft bij onbekend materiaal geen fictieve materiaalrelatie. De bijbehorende lichte lezer volgt per object de expliciete materiaalrelatie; een eerste materiaaldeclaratie wordt niet over alle objecten verspreid. Catalogusdichtheden en andere materiaalwaarden zijn nominale rekengegevens, geen materiaalcertificaat of constructieve geschiktheidsverklaring.

Materiaalafhankelijke NC1-massa en de omrekening van brongewicht naar profieloppervlakte gebruiken de gevonden dichtheid. Ontbrekende betrouwbare dichtheid blokkeert een noodzakelijke massaomrekening. Een nulgewicht uit NC1 blijft in het geïmporteerde profiel nul. Bestaande geometrische profielcatalogi kunnen nominale staalmassa bevatten; die waarde is op zichzelf geen bronmateriaalbewijs.

Dit document beschrijft het werkpakket. De actuele aantoonbare teststatus staat uitsluitend in de gegenereerde `FINAL_ACCEPTANCE.json` van de te leveren bronrevisie.

## Acceptatie uitvoeren

Gebruik de bestaande repo, Python 3.12 x64 en een eigen virtuele omgeving. Installeer geen willekeurige nieuwere CAD-versies naast de lock.

```powershell
python -m pip install -r requirements-runtime.lock.txt
python -m pip check
python tools/run_material_model_recognition_acceptance.py --require-native
```

De runner gebruikt de actuele Python-interpreter en controleert echte imports van CadQuery, OCP, IfcOpenShell, PySide6, PyMuPDF, ezdxf, ReportLab, pypdf en NumPy. De CI-workflow `material-model-recognition.yml` voert dezelfde strikte opdracht uit op Windows en uploadt het bewijs ook bij een mislukte test of dependency-installatie.

De bestaande workflows `final-release-proof.yml` en `build-product-ui-reintegration-exe.yml` vereisen deze strikte gate eveneens vóór hun verpakkingsstappen. Zij schrijven naar `build/material_model_recognition/`, zodat een CI-run niet de meegeleverde lokale validatiebestanden overschrijft. Een geblokkeerde herkenningsgate stopt daar de installatiebuild; bewijs wordt ook bij fouten geüpload.

Een gerichte ontwikkelcontrole kan wel, maar is nooit volledige acceptatie:

```powershell
python tools/run_material_model_recognition_acceptance.py --suite material_resolution_smoke --suite material_workbench_gate_smoke
```

Een geslaagde selectie geeft `SUBSET_PASS`, `acceptance_passed: false` en percentages met de volledige manifestnoemer. `--require-native` mag niet met `--suite` worden gecombineerd.

## Bewijsbestanden en percentages

Standaard komen de resultaten onder `validation/material_model_recognition/`:

| Bestand/map | Betekenis |
| --- | --- |
| `FINAL_ACCEPTANCE.json` | Volledige status, suite- en testaantallen, percentages per gebied, blokkades, runtime en bronbinding. |
| `SOURCE_FINGERPRINT.json` | Git-SHA, branch en SHA256 van bronbestanden, inclusief nog niet gecommitteerde bronwijzigingen. Gegenereerde validatiebestanden tellen niet mee in de bronhash. |
| `DEPENDENCIES.json` | Werkelijke importresultaten; een aanwezige maar defecte module telt niet als beschikbaar. |
| `suites/*.json` | Werkelijke uitkomsten per testmethode/functie, inclusief fout-, skip- en fixture-events. |
| `logs/*.log` | Uitvoer en fouten per geïsoleerde testsuite. |
| `screenshots/` | Echte UI-captures wanneer de UI-tests deze produceren; geen gegenereerde voorbeeldafbeeldingen als testbewijs gebruiken. |

Rekenregels:

- Suitepercentage = geslaagde suites / alle verplichte suites in het vaste manifest × 100. Geblokkeerde, ontbrekende en niet-geselecteerde suites blijven in de noemer.
- Uitgevoerde-testpercentage = geslaagde logische tests / werkelijk uitgevoerde logische tests × 100. Subtestfouten worden afzonderlijk geregistreerd en tellen niet als extra uitgevoerde testmethoden.
- Een geblokkeerde suite krijgt geen verzonnen testaantal. Daardoor kan het uitgevoerde-testpercentage 100% zijn terwijl het suitepercentage lager is en de totale acceptatie niet is geslaagd.
- `SKIPPED`, expected failures, nul ontdekte tests, importfouten, time-outs en ontbrekende native afhankelijkheden zijn nooit `PASS`.
- Een gewijzigde bronfingerprint tijdens de run maakt de run ongeldig. Stop parallelle bronwijzigingen vóór de definitieve acceptatierun.
- De runner controleert tevens dat een oud resultaatsbestand niet als nieuw bewijs hergebruikt wordt wanneer een subprocess geen resultaat schrijft.

## Minimale functionele bewijsgevallen

De exacte testnamen zijn leidend in de `SUITES`-manifest van de runner. Het pakket bestrijkt:

1. Bekende exacte materiaalcode, expliciete alias en onbekende/incomplete code; geen impliciete default.
2. Staal, RVS, aluminium, bevestigingsklassen, hout, beton en kunststoffen; geblokkeerde massa als de dichtheid onvoldoende is onderbouwd.
3. IFC-materiaalrelaties, type-overerving, samengestelde materialen, conflicten en semantische import.
4. STEP zonder materiaalbewijs, bronhashcontrole, uitgestelde geometrieherkenning en veilige MGI-promotie.
5. Doorsneden met segmentatie, gaten, bogen en niet-standaardvormen; onduidelijke vormen blijven onopgelost/CUSTOM.
6. Importclassificatie en projectpersistentie, ontbrekende materiaal/profielbevestiging en vrijgaveblokkades.
7. PDF/DXF-tekst als kandidaat, conflicterende materiaalnamen en uitgesloten kleur-/geometrie-inferentie.
8. Materiaalreview, bulkpreview, expliciete reden, bevestigen/afwijzen, stale-state-bewaking en undo.
9. Native CAD-herkenning, canonieke roundtrip en de werkelijke Qt-reviewwerkruimte.
10. De acceptatierunner zelf: fout- en skipdetectie, exacte telling, bronfingerprint en bescherming tegen oud bewijs.
11. Projectmodel, opslag/heropenen, BOM, projectservice, semantische service en uniform projectschema als regressievoorwaarden.
12. Productienormalisatie: bronmetrics en expliciete vrijgavevoorwaarden; drie niet-native controles plus twee werkelijke native metricfixtures. Zonder CAD blijven die twee native checks expliciet overgeslagen en de suite onvolledig.
13. Stille materiaaldefaults in CLI/GUI/helpers en IFC-conversiebeleid; afzonderlijke native conversiecontroles voor het daadwerkelijk gegenereerde model.

De aanvullende native PDF-modelgate bouwt een echte STEP-fixture en controleert dat import zonder materiaalkwaliteit concept/onopgelost blijft, terwijl een expliciet opgegeven catalogusmateriaal met herkomst behouden blijft. PDF-tekstanalyse heeft geen CAD-kernel nodig en wordt afzonderlijk getest.

## Visueel bewijs

Voor een visuele oplevering zijn echte, actuele screenshots nodig van minimaal: de bronbewijstabel en reviewwachtrij, een bekende en onbekende kandidaat, bulkpreview, bevestiging, afwijzing/conflict, undo en de productievrijgaveblokkade. Leg project/part-ID, testnaam, bronfingerprint en verwacht resultaat vast naast de afbeelding.

Een afbeelding bewijst geen geometrische equivalentie of materiaalkwaliteit. Combineer haar met de machineleesbare uitkomst. Ontbrekende screenshots blijven een expliciete visuele opleveringsgap; deze runner geeft nooit zelfstandig toestemming voor een installerrelease.

## Overdracht naar Windows-installatiebuild

De herkenningsgate bouwt zelf geen EXE of installer. `installer_release_approved` blijft daarom bewust `false`, ook als alle herkenningstests groen zijn.

Codex moet vóór een installatieoplevering:

1. De bedoelde branch en definitieve commit vaststellen; geen oude acceptatie van een andere SHA hergebruiken.
2. De strikte herkenningsgate op die commit uitvoeren zonder skips en de overige bestaande programmabrede gates uitvoeren.
3. Werkelijke UI-bewijsafbeeldingen controleren; ontbrekende of lege captures herstellen.
4. De bestaande Windows-releaseketen gebruiken (`.github/workflows/final-release-proof.yml`, locked buildruntime en bestaande release-/installerscripts), zonder een tweede los productpakket te bouwen.
5. One-folder runtime, vers uitgepakte portable en werkelijk geïnstalleerde applicatie testen, inclusief voorbeeld-IFC, STEP, PDF en DXF.
6. Installatie, eerste start, opslaan/heropenen en uninstall bewijzen op een schone Windows-testomgeving. Geen productiegegevens of bestaande gebruikersinstallatie wissen.
7. EXE/portable/installer, checksums, bron-SHA, buildlog, actuele acceptatie-JSON en screenshots samen opleveren. Niet-uitgevoerde checks expliciet rapporteren.

## Bekende grenzen die niet als voltooid mogen worden gepresenteerd

- Chemische samenstelling en sterkte zijn niet uit alleen vorm, kleur, mesh of extrusie te bepalen.
- De materiaalcatalogus is uitbreidbaar, niet een inventaris van alle ooit bestaande materiaalsoorten.
- Een generieke of onvolledige materiaalnaam is geen bewijs van de exacte productiekwaliteit.
- Complexe, beschadigde of niet-standaard doorsneden kunnen veilig onopgelost blijven; dit is geen toestemming voor productie.
- Native tests die niet in de huidige omgeving kunnen draaien, moeten op de bedoelde runtime/CI worden uitgevoerd; lokaal groen op pure tests vervangt dit niet.
- Deze vaste regressiesuite is geen representatief nauwkeurigheidspercentage over alle klantmodellen. Daarvoor is een geannoteerde praktijkcorpus nodig met afzonderlijke juist/onjuist/onopgelost/conflict-tellingen.
- Een STEP-bron met meerdere onderdelen wordt nog niet per solid door de nieuwe uitgestelde projectactie geïsoleerd: deze actie blokkeert dit expliciet. Hetzelfde geldt voor geometrieën zonder voldoende doorsnede- en equivalentiebewijs.
- Semantische IGES/IGS- en losse BREP-projectimport is in deze build niet toegevoegd. IFC/STEP-bronstructuur en PDF/DXF-documentbewijs zijn de geïntegreerde routes.
- Binaire DXF en een raster-PDF zonder tekst/OCR leveren in de nieuwe documentbewijsroute geen automatische materiaalwaarde. Materiaalkandidaten uit een document moeten aan het juiste onderdeel gekoppeld en bevestigd worden.
- Qt-schermen, native CAD-geometrie, prestatiegedrag op grote modellen en Windows-installatie vereisen eigen werkelijk uitgevoerde controles. In het bijzonder is het geheugengebruik van de volledige projectsnapshot voor een bulkactie nog niet gemeten met de native viewer.

## Praktijkcorpus apart meten

```powershell
python tools/check_material_reference_corpus.py --include-regression-steps
```

Dit herimporteert de ingesloten bron uit het beschikbare HVPC-referentieproject in een nieuw tijdelijk project, plus de expliciet als gegenereerd/synthetisch gelabelde STEP-regressiebestanden. Het oorspronkelijke projectpakket wordt niet opgeslagen of gewijzigd. `validation/material_model_recognition/reference/corpus.json` bevat bronhashes, catalogustreffers, onbekende waarden, classificatie en exportblokkades apart. Extra echte STEP-bronnen kunnen met herhaalde `--step PAD` argumenten worden toegevoegd. Een catalogustrefferpercentage is geen gemeten herkenningsnauwkeurigheid zonder onafhankelijk vastgestelde juiste waarden.
