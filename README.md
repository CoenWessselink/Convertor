# NC1 / DSTV - STEP - IFC - Trusted PDF Converter v0.5.1

Lokale Windows-applicatie en CLI voor staalonderdelen. De v0.5-lijn bouwt voort op de bewezen NC1/STEP-kern en voegt een canoniek onderdeelmodel, lossless converter-eigen IFC/PDF, technische vector-PDF's, een deterministische maatgrafiek, menselijke review en een begrensde AI-laag toe.

## Veiligheidsprincipe

Alle productieformaten lopen via één canoniek onderdeelmodel:

```text
PDF / NC1 / STEP / IFC
          |
          v
Canonical Part Model
          |
          v
NC1 / STEP / IFC / PDF / Excel
```

AI mag uitsluitend documentsemantiek, aanzichten, conflicten, confidence en controlevragen voorstellen. AI schrijft geen NC1-regels, STEP/IFC-geometrie, contourcoordinaten of gatposities. Geometrie, maatwaarden, hoeveelheden, serialisatie, roundtripcontrole en vrijgave blijven deterministisch.

Een kritische afwijking of onopgeloste vraag blokkeert productie-export. De strikte veiligheidscontrole is in GUI en CLI niet uitschakelbaar.

## Aantoonbaar geteste status

### Conversiekern

| Testgroep | Geslaagd | Totaal |
|---|---:|---:|
| NC1 -> STEP | 24 | 24 |
| STEP -> NC1 | 19 | 19 |
| NC1 -> IFC -> STEP -> NC1 | 4 | 4 |
| STEP -> IFC -> NC1 -> STEP | 4 | 4 |

De acht focusbestanden, inclusief platen met gaten, HEA140/HEA160 en rondstaal D20, zijn geslaagd met de strikte productiepoort ingeschakeld.

### PDF, review en AI

| Testgroep | Geslaagd | Totaal |
|---|---:|---:|
| NC1 -> Trusted PDF -> exact NC1 | 24 | 24 |
| STEP -> Trusted PDF -> exact STEP | 19 | 19 |
| Focus Trusted PDF -> IFC | 2 | 2 |
| Synthetische LO4 externe-PDF-keten | 1 | 1 |
| AI-, integriteits-, review- en ambiguiteitstests | 11 | 11 |

De synthetische LO4-test reconstrueert een gesloten plaatcontour met twee analytische radii R13,5 en een analytisch gat Ø14 op X/Y 20 mm. Na expliciete review worden NC1, STEP, semantisch IfcPlate en een nieuwe Trusted PDF gemaakt. De maatgrafiek is voor en na review geldig met 100% dekking.

Volledige rapporten staan in de afzonderlijke validatiepakketten.

## Conversierichtingen

### Productiekern

- NC1/DSTV -> STEP
- STEP -> NC1/DSTV
- NC1/DSTV -> IFC
- IFC -> NC1/DSTV
- STEP -> IFC
- IFC -> STEP
- IFC/STEP -> hoeveelheden en Excel

### Technische PDF

- NC1/DSTV -> vectoriele Trusted Converter PDF
- STEP -> vectoriele Trusted Converter PDF
- IFC -> een of meer vectoriele technische PDF's
- ongewijzigde Trusted Converter PDF -> NC1/DSTV
- ongewijzigde Trusted Converter PDF -> STEP
- ongewijzigde Trusted Converter PDF -> IFC
- eenvoudige externe vector-PDF met plaat/strip -> analyse -> interactieve review -> Trusted PDF -> NC1/STEP/IFC

Een willekeurige externe PDF zonder geverifieerde converterpayload wordt nooit stilzwijgend naar productieformaten vrijgegeven. Alleen wanneer contour, gaten, radii, referentiezijde, kritische metadata en maatconsistentie deterministisch zijn bepaald of expliciet zijn bevestigd, kan een Trusted PDF worden gemaakt.

## Trusted Converter PDF

Een door de applicatie gemaakte Trusted PDF bevat:

- een scherpe vectoriele werktekening;
- een deterministische, feature-gekoppelde maatgrafiek;
- totale hoofdafmetingen, gatdiameters en gatposities vanaf vaste datums;
- radii, plaatdikte/profieldoorsnede, stukregel en titelblok;
- het volledige versieerbare canonieke model als `converter-model.json`;
- een `converter-manifest.json` met hashes en technische identiteit;
- de oorspronkelijke NC1/STEP/IFC-bron als gekoppelde PDF-bijlage wanneer beschikbaar;
- XMP-velden met schema-, onderdeel- en hashinformatie;
- hashes van canoniek model, geometrie, bronbestand en zichtbare tekening.

Bij import worden alle lagen opnieuw gecontroleerd. Een zichtbare wijziging, beschadigde manifestchecksum, ontbrekende bronbijlage, maatgrafiekfout of XMP-mismatch maakt de PDF ongeldig voor productie-export.

## Externe PDF en interactieve review

De huidige vector-PDF-pipeline kan lokaal:

- pagina's classificeren als vector, raster, hybride of tekst-only;
- bladformaat, oriëntatie, schaal en tekeningskwaliteit bepalen;
- tekst, woorden, vectorpaden, cirkels en afbeeldingen met broncoordinaten uitlezen;
- stukregel, titelblok, positie, profiel, materiaal, lengte, aantal, merk en onderwerp herkennen;
- gesloten plaatcontouren reconstrueren;
- collineaire segmenten vereenvoudigen;
- cirkels, ronde gaten en uit Bezierpaden gefitte contourbogen herkennen;
- geschreven en geometrisch gemeten waarden op conflicten controleren;
- per veld provenance, confidence, status en bronbewijs opslaan;
- gerichte blokkerende controlevragen formuleren.

Via **Interactief reviewen** toont de GUI links de bron-PDF en rechts het deterministisch gereconstrueerde model. De gebruiker kan toegestane velden, gaten en contourpunten corrigeren, bronbewijs markeren, vragen beantwoorden en de review met naam/commentaar vastleggen. Alleen toegestane paden worden verwerkt; onbekende of niet-onderbouwde reviewvelden worden geweigerd.

## AI-functie

Het tabblad **PDF / Tekening** ondersteunt drie standen:

- geen AI;
- lokale offline regel-/semantiekprovider;
- optionele OpenAI Responses-provider na expliciete toestemming.

Cloud-AI staat standaard uit. Voor inschakeling zijn een modelnaam en `OPENAI_API_KEY` nodig. De cloudrequest gebruikt afbeeldinginput, een strikt semantisch JSON-schema, `store=false` en een auditrecord met hashes en request-ID's. Klantinhoud wordt niet in het lokale auditrecord opgeslagen.

AI-uitvoer gaat door een recursieve whitelist/guard. Vrije productiegeometrie, coordinate arrays, NC1/DSTV, STEP, IFC, solids en machinecode worden actief geweigerd. AI kan dus alleen een reviewvoorstel leveren; de deterministische parser en geometriekern blijven leidend.

## Deterministische maatgrafiek

`dimension_graph.py` bouwt maatobjecten rechtstreeks uit het canonieke model. Elke maat bevat:

- stabiele ID en maatsoort;
- numerieke waarde en eenheid;
- echte geometrische ankers;
- featureverwijzingen;
- bronveld, provenance, confidence en status;
- kritische/release-indicatie;
- optionele datumketen.

De validatielaag controleert waarde, ankers, featurebestaan, duplicaten, ketens en verplichte dekking. Productie-PDF-export wordt geblokkeerd wanneer de maatgrafiek niet valide is.

## Technische tekeninggenerator

De v0.5.1-generator maakt een reproduceerbare vector-PDF met:

- primaire projectie;
- eind-/doorsnedeweergave waar relevant;
- standaard tekenschaal die overeenkomt met het titelblok;
- totale lengte, breedte en/of hoogte;
- gatdiameters en datumgebaseerde gatposities;
- contourradii indien aanwezig;
- plaatdikte of profieldoorsnede;
- stukregel met Pos, Profiel, Materiaal, Lengte, Aantal en Merk;
- status, datum, bronbestand, formaat en schaal;
- conceptwatermerk wanneer productie niet is vrijgegeven.

Bedrijfsspecifieke instellingen staan in `templates/default_company.json` en kunnen als eigen JSON-template worden opgeslagen.

## GUI

Start na installatie via het Startmenu of dubbelklik op:

```text
NC1_STEP_Converter.exe
```

Tabbladen:

- **Converter** - conversierichtingen, batchverwerking en log;
- **Visuele vergelijking** - links/rechts 3D-vergelijking;
- **PDF / Tekening** - Trusted PDF, externe PDF-analyse, AI en interactieve review;
- **Profielendatabase** - zoeken en filteren in 1.718 profielrecords;
- **Hoeveelheden & Excel** - hoeveelheden, massa en materiaaldata.

De Windows-installer kan `.nc`, `.nc1`, `.step`, `.stp` en `.ifc` koppelen. Voor PDF blijft de normale PDF-lezer intact; de installer voegt alleen **Openen in NC1 STEP IFC Converter** aan het contextmenu toe.

## CLI

Voorbeelden:

```text
NC1_STEP_Converter_CLI.exe nc1-to-step input.nc1 -o output
NC1_STEP_Converter_CLI.exe step-to-nc1 input.step -o output
NC1_STEP_Converter_CLI.exe nc1-to-pdf input.nc1 -o output
NC1_STEP_Converter_CLI.exe step-to-pdf input.step -o output
NC1_STEP_Converter_CLI.exe pdf-analyze drawing.pdf -o analyse --ai-provider local-rules
NC1_STEP_Converter_CLI.exe pdf-review drawing.pdf --review review.json -o reviewed_trusted.pdf
NC1_STEP_Converter_CLI.exe pdf-to-nc1 reviewed_trusted.pdf -o output
NC1_STEP_Converter_CLI.exe pdf-to-step reviewed_trusted.pdf -o output
NC1_STEP_Converter_CLI.exe pdf-to-ifc reviewed_trusted.pdf -o output
NC1_STEP_Converter_CLI.exe ifc-to-pdf model.ifc -o output
NC1_STEP_Converter_CLI.exe excel model.ifc model.step -o hoeveelheden.xlsx
```

Machineleesbare JSON-rapportage en batchmappen worden ondersteund. Gebruik `--help` bij het hoofdcommando en subcommando.

Voor optionele cloud-AI:

```text
set OPENAI_API_KEY=...
NC1_STEP_Converter_CLI.exe pdf-analyze drawing.pdf -o analyse ^
  --ai-provider openai ^
  --allow-cloud-ai ^
  --ai-model gpt-5.6
```

## Windows-installatie

De eindgebruiker heeft geen Python, pip, venv of terminal nodig. De beoogde release bevat:

```text
NC1_STEP_IFC_Converter_Setup_0.5.1_x64.exe
NC1_STEP_IFC_Converter_Portable_0.5.1_x64.zip
SHA256SUMS.txt
```

De installer bundelt de Python-runtime, CadQuery/Open CASCADE, IfcOpenShell, PyMuPDF, Matplotlib, XlsxWriter, profielen, materialen en templates. De daadwerkelijke Windows-EXE en installer moeten op een Windows x64-runner worden gebouwd en getest; een Linux-build is daarvoor niet gelijkwaardig.

Ontwikkelaars kunnen op Windows de volledige releaseketen starten met `build_windows_exe.bat`. GitHub Actions gebruikt Python 3.12 x64, voert compile-, kern-, PDF-, maatgrafiek-, review- en GUI-smokes uit, bouwt een PyInstaller `onedir`, maakt de portable ZIP, verpakt die via Inno Setup in één installer-EXE en voert een geinstalleerde-app-smoke uit met Python verwijderd uit `PATH`.

## Broninstallatie voor ontwikkelaars

De normale gebruiker hoeft dit niet uit te voeren. Voor bronontwikkeling:

```text
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python app.py
```

Belangrijkste runtime-afhankelijkheden:

- CadQuery 2.8.0;
- NumPy 2.x;
- Matplotlib 3.10.8;
- XlsxWriter 3.2.9;
- IfcOpenShell 0.8.5;
- PyMuPDF 1.26.7.

## Tests

Snelle tests:

```text
python -m py_compile *.py tests\*.py validation\*.py
python tests\analytic_fitting_smoke.py
python tests\regression_smoke.py
python tests\pdf_ai_smoke.py
python tests\pdf_review_smoke.py
python tests\dimension_graph_smoke.py
python tests\review_workflow_smoke.py
```

Volledige NC1/STEP/IFC-regressie:

```text
python validation\run_v05_validation.py ^
  --handover-root <overdrachtspakket> ^
  --output <validatiemap>
```

Persistente PDF/AI/review-validatie:

```text
python validation\run_v05_pdf_ai_validation.py ^
  --handover-root <overdrachtspakket> ^
  --output <validatiemap>
```

## Huidige beperkingen

- De exacte Trusted PDF-roundtrip is geteste bronfunctionaliteit voor door de converter gemaakte PDF's; willekeurige externe tekeningen blijven reviewplichtig.
- De echte `Pos LO4 - LOSSE PLAAT.pdf` kon in deze runtime niet als lokaal PDF-binair bestand worden geopend en is daarom nog geen uitgevoerde vector-/geometrieregressietest. Alleen een duidelijk als synthetisch gemarkeerde LO4-test is uitgevoerd.
- De externe geometrische reconstructie is nu gericht op eenvoudige vectoriele platen/strips. Algemene profieltekeningen, meerdere orthografische aanzichten en complexe bewerkingen zijn nog niet productiebreed afgedekt.
- Raster-OCR, deskew, foto-/perspectiefcorrectie en taal-/symboolvarianten zijn nog geen productie-importer.
- De interactieve editor dekt velden, gaten en contourpunten; een volledig vrije CAD-schetseditor, drag-and-drop maatankers, undo/redo en detailaanzichtbewerking volgen later.
- Volledige hidden-lineprojectie, detailaanzichten, snijlijnen en algemene maatplaatsingsoptimalisatie zijn nog niet gereed.
- De uitgebreide materiaal-/onderdeeleditor, versleepbare eigenschappenlijst, prijsregels, bewerkingstijden, projectopslag en licenties uit de aanvullende UI-scope zijn nog niet gebouwd.
- Grote externe IFC/STEP-bestanden en multi-gigabyte projectmodellen hebben nog geen formele belastings-/geheugentest.
- Een echte Windows-installer is pas bewezen nadat het Windows-buildresultaat op een schone Windows x64-machine zonder Python is geinstalleerd en getest.

Geen van deze beperkingen schakelt de veiligheidscontrole uit: onzekere productie-uitvoer wordt geblokkeerd.
