# NC1 / DSTV - STEP - IFC - Trusted PDF Converter v0.5.0

Lokale Windows-applicatie en CLI voor staalonderdelen. De v0.5-lijn bouwt voort op de bewezen NC1/STEP-kern en voegt een canoniek onderdeelmodel, lossless converter-eigen IFC/PDF, technische vector-PDF's en een begrensde AI-laag voor tekeningen toe.

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

AI mag uitsluitend documentsemantiek, aanzichten, conflicten, confidence en controlevragen voorstellen. AI schrijft geen NC1-regels, STEP/IFC-geometrie, contourcoördinaten of gatposities. Geometrie, maatwaarden, hoeveelheden, serialisatie en vrijgave blijven deterministisch.

Een kritische afwijking of onopgeloste vraag blokkeert productie-export. De strikte veiligheidscontrole is in GUI en CLI niet uitschakelbaar.

## Aantoonbaar werkende kern

De volledige meegeleverde regressieset is met v0.5 opnieuw uitgevoerd:

| Testgroep | Geslaagd | Totaal |
|---|---:|---:|
| NC1 -> STEP | 24 | 24 |
| STEP -> NC1 | 19 | 19 |
| NC1 -> IFC -> STEP -> NC1 | 4 | 4 |
| STEP -> IFC -> NC1 -> STEP | 4 | 4 |

De acht focusbestanden inclusief platen met gaten, HEA140/HEA160 en rondstaal D20 zijn geslaagd. Details staan in `VALIDATION_V05/ROUNDTRIP_VALIDATIE_V05.md` in het vrijgavepakket.

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
- externe PDF -> lokale vector-/tekstanalyse en optionele AI-review

Een externe PDF zonder geverifieerde converterpayload wordt niet direct naar productieformaten vrijgegeven. De huidige v0.5 analyseert documenttype, bladformaat, tekst, stukregel, profiel, materiaal, positie, aantallen, callouts, radii, schaal en controlevragen. Exacte externe-PDF-geometrie en de interactieve correctieworkflow zijn nog in ontwikkeling.

## Trusted Converter PDF

Een door de applicatie gemaakte Trusted PDF bevat:

- een scherpe vectoriele werktekening;
- maatvoering van hoofdmaten en gatcallouts;
- een configureerbare stukregel en titelblok;
- het volledige versieerbare canonieke model als `converter-model.json`;
- de oorspronkelijke NC1/STEP/IFC-bron als gekoppelde PDF-bijlage;
- XMP-velden met schema-, onderdeel- en hashinformatie;
- hashes van canoniek model, geometrie, bronbestand en zichtbare tekening.

Bij import worden alle lagen opnieuw gecontroleerd. Een zichtbare wijziging, beschadigde manifestchecksum, ontbrekende bronbijlage of XMP-mismatch maakt de PDF ongeldig voor productie-export.

## PDF/AI-tabblad

Het tabblad **PDF / AI controle** ondersteunt:

- PDF kiezen en als afbeelding voorvertonen;
- Trusted PDF controleren;
- lokale offline semantische analyse;
- optionele cloud-AI na expliciete toestemming;
- per veld waarde, confidence, methode en bronbewijs tonen;
- blokkerende fouten en gerichte controlevragen tonen.

Cloud-AI staat standaard uit. Bij inschakeling is een expliciet model en `OPENAI_API_KEY` nodig. De aanvraag gebruikt gestructureerde semantische uitvoer, `store=false` en een auditrecord met hashes en request-ID's. Klantbestanden worden niet stilzwijgend extern verwerkt.

## Technische tekeninggenerator

De v0.5-generator maakt een reproduceerbare A4-vector-PDF met:

- primaire projectie;
- eind-/doorsnedeweergave;
- standaard tekenschaal die exact overeenkomt met het titelblok;
- totale lengte en breedte/hoogte;
- gaten met diametercallout;
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

- **Converter** - alle conversierichtingen, batchverwerking en log;
- **Visuele vergelijking** - links/rechts 3D-vergelijking;
- **PDF / AI controle** - Trusted PDF en externe PDF-analyse;
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
NC1_STEP_Converter_CLI.exe pdf-inspect drawing.pdf --json
NC1_STEP_Converter_CLI.exe pdf-analyze drawing.pdf --ai-provider local --json
NC1_STEP_Converter_CLI.exe pdf-to-nc1 trusted.pdf -o output
NC1_STEP_Converter_CLI.exe ifc-to-pdf model.ifc -o output
NC1_STEP_Converter_CLI.exe excel model.ifc model.step -o hoeveelheden.xlsx
```

Machineleesbare JSON-rapportage en batchmappen worden ondersteund. Gebruik `--help` bij het hoofdcommando en subcommando.

Voor optionele cloud-AI:

```text
set OPENAI_API_KEY=...
NC1_STEP_Converter_CLI.exe pdf-analyze drawing.pdf ^
  --ai-provider openai ^
  --allow-cloud-ai ^
  --ai-model gpt-5.6 ^
  --json
```

## Windows-installatie

De eindgebruiker heeft geen Python, pip, venv of terminal nodig. De beoogde release bevat:

```text
NC1_STEP_IFC_Converter_Setup_0.5.0_x64.exe
NC1_STEP_IFC_Converter_Portable_0.5.0_x64.zip
SHA256SUMS.txt
```

De installer bundelt de Python-runtime, CadQuery/Open CASCADE, IfcOpenShell, PyMuPDF, Matplotlib, XlsxWriter, profielen, materialen en templates. De daadwerkelijke Windows-EXE en installer moeten op een Windows x64-runner worden gebouwd en getest; een Linux-build is daarvoor niet gelijkwaardig.

Ontwikkelaars kunnen op Windows de volledige releaseketen starten met `build_windows_exe.bat`. GitHub Actions gebruikt Python 3.12 x64, voert alle smoke- en PDF-tests uit, bouwt een PyInstaller `onedir`, maakt de portable ZIP en verpakt die via Inno Setup in één installer-EXE.

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
```

Volledige NC1/STEP/IFC-regressie:

```text
python validation\run_v05_validation.py ^
  --handover-root <overdrachtspakket> ^
  --output <validatiemap>
```

Persistente PDF/AI-validatie:

```text
python validation\run_v05_pdf_ai_validation.py ^
  --handover-root <overdrachtspakket> ^
  --output <validatiemap>
```

## Huidige beperkingen

- De exacte Trusted PDF-roundtrip is productierijp voor door de converter gemaakte PDF's; willekeurige externe tekeningen zijn nog reviewplichtig.
- De echte `Pos LO4 - LOSSE PLAAT.pdf` kon in de huidige runtime niet binair worden geopend en is daarom nog geen uitgevoerde vector-/geometrieregressietest. Alleen een duidelijk als synthetisch gemarkeerde semantische test is uitgevoerd.
- Algemene externe scan-OCR, perspectiefcorrectie, maatgrafiek, aanzichtkoppeling en interactieve contourcorrectie zijn nog niet volledig ingebouwd.
- De tekeningenmodule heeft nu primaire en doorsnedeweergaven; volledige hidden-lineprojectie, detailaanzichten, snijlijnen en handmatig verplaatsbare maten volgen later.
- Grote externe IFC/STEP-bestanden en multi-gigabyte projectmodellen hebben nog geen formele belastings-/geheugentest.
- Een echte Windows-installer is pas bewezen nadat het GitHub/Windows-buildresultaat op een schone Windows x64-machine zonder Python is geinstalleerd en getest.

Geen van deze beperkingen schakelt de veiligheidscontrole uit: onzekere productie-uitvoer wordt geblokkeerd.
