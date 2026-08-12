# v0.5.0 - opleverstatus en vervolgvolgorde

## Doel van deze fase

Deze fase bouwt voort op de bestaande v0.4-conversiekern en voegt de eerste veilige, bidirectionele PDF-/AI-laag toe. De werkende NC1-, STEP- en IFC-routes zijn behouden. AI is uitsluitend adviserend; productiegeometrie en exportvrijgave blijven deterministisch.

## In deze fase gerealiseerd

### 1. Canoniek onderdeelmodel schema 1.1

- provenance en confidence per herkend veld;
- veldstatussen en bronbewijs;
- tekengegevens, open controlevragen en auditlog;
- productie-/vrijgavestatus;
- gehashte bijlagen en payloadlimieten;
- compatibiliteit binnen schemafamilie 1.x.

### 2. Trusted Converter PDF

- vectoriele technische PDF uit NC1, STEP en IFC;
- embedded `converter-model.json` met exact canoniek model;
- oorspronkelijke bron als PDF-bijlage;
- XMP-identiteit en hashes;
- checksum van canoniek model, geometrie, bron en zichtbare tekening;
- exacte terugconversie naar NC1, STEP en IFC wanneer alle controles slagen;
- blokkade bij zichtbare manipulatie of beschadigd manifest.

### 3. Externe PDF-analyse

- lokale tekst- en vectorclassificatie;
- herkenning van bladformaat, schaal, positie, profiel, materiaal, lengte, aantal, merk, onderwerp en callouts;
- confidence, bronbewijs en controlevragen;
- productie-export blijft geblokkeerd zolang contour, maatkoppeling of referentiezijde niet deterministisch is bevestigd.

### 4. Veilige AI-functie

- lokale offline semantische provider;
- optionele cloudprovider via een begrensd JSON-schema;
- expliciete toestemming per cloudanalyse;
- `store=false` in de cloudrequest;
- semantische whitelist;
- recursieve guard tegen NC1/DSTV-, STEP-, IFC-, contour-, coordinaten- en soliddata;
- deterministische herkenning heeft voorrang en wordt niet stilzwijgend door AI overschreven;
- auditinformatie met hashes en request-ID's, zonder lokale opslag van klantinhoud in het auditrecord.

### 5. GUI en CLI

- tabblad `PDF / AI controle`;
- Trusted PDF-inspectie;
- externe PDF-analyse met lokale of optionele cloud-AI;
- PDF-voorvertoning, confidence, bronbewijs, waarschuwingen en vragen;
- CLI-routes voor PDF-generatie, PDF-inspectie, PDF-analyse en Trusted PDF-terugconversie;
- JSON-rapportage en batchinvoer;
- strikte productievalidatie kan niet worden uitgeschakeld.

### 6. Windows-releaseketen

- Python 3.12 x64 als beoogde buildruntime;
- PyInstaller `onedir` voor GUI en CLI;
- Inno Setup-project voor een installer-EXE;
- portable ZIP en SHA-256-generatie;
- optionele bestandskoppelingen voor NC/NC1/STEP/STP/IFC;
- PDF-contextmenu zonder de standaard PDF-lezer over te nemen;
- GitHub Actions-workflow met compile-, regressie-, PDF-/AI- en GUI-smokes.

## Werkelijk uitgevoerde tests

### Conversiekern

| Testgroep | Geslaagd | Totaal |
|---|---:|---:|
| NC1 -> STEP | 24 | 24 |
| STEP -> NC1 | 19 | 19 |
| NC1 -> IFC -> STEP -> NC1 | 4 | 4 |
| STEP -> IFC -> NC1 -> STEP | 4 | 4 |

### PDF en AI

| Test | Uitkomst |
|---|---|
| P1811 NC1 -> Trusted PDF -> NC1/STEP/IFC | Geslaagd |
| D20 STEP -> Trusted PDF -> STEP | Geslaagd, volumeverschil 0% binnen meetprecisie |
| Zichtbaar gewijzigde Trusted PDF | Correct geblokkeerd |
| Beschadigd Trusted PDF-manifest | Correct geblokkeerd |
| Synthetische LO4-vector-PDF | 12 semantische velden herkend; productie correct geblokkeerd |
| Cloud-AI-contract met mocktransport | Toestemming, `store=false`, schema, image input en audit geslaagd |
| AI-productiegeometrieguard | Verboden inhoud correct geweigerd |

De echte `Pos LO4 - LOSSE PLAAT.pdf` was in deze runtime niet als lokaal PDF-binair bestand beschikbaar. Daarom is daarvoor nog geen vector-/geometrieclaim gedaan.

## Wat nog niet als gereed mag worden beschouwd

- generieke geometrische reconstructie van willekeurige externe vector-PDF's;
- volledige maatgrafiek en koppeling van geschreven maten aan contourfeatures;
- scan-OCR, deskew en perspectiefcorrectie op productieniveau;
- interactieve correctie van contouren, maatankers en aanzichten;
- volledige hidden-line-, detail-, snede- en maatplaatsingsengine;
- formele belastingstest op zeer grote IFC-/STEP-projecten;
- native Windows-installerbuild en schone-machine-installatietest;
- projectbeheer, licenties en online jobomgeving.

## Juiste vervolgvolgorde

1. **Echte LO4-PDF als lokaal testbestand opnemen.** Vectorpaden, tekstposities, maatlijnen en contouren exact analyseren.
2. **Dimension graph en externe plaatreconstructie afronden.** Eerst platen en strips; productie-export pas na gesloten contour en feature-roundtrip.
3. **Interactieve PDF-review bouwen.** Bron links, 2D/3D-reconstructie rechts, veld- en featurecorrecties, bevestiging en audit.
4. **Profieltekeningen uitbreiden.** Orthografische aanzichten, hidden lines, doorsneden en bewerkingsdetails.
5. **Scan-/OCR-pipeline toevoegen.** Alleen als reviewplichtige conceptmodus, met dezelfde exportblokkades.
6. **Multi-part IFC/PDF, performance en batchrapportage harden.** Inclusief grote-bestandentests.
7. **Windows x64-release bouwen.** Installer en portable ZIP op Windows maken, daarna op een schone machine zonder Python installeren en de acceptatieset uitvoeren.
8. **Pas daarna projectopslag, licenties en online/cloud-jobmodel afronden.** Deze functies mogen de geometrische kern en veiligheidslaag niet omzeilen.

## Vrijgavebeoordeling

v0.5.0 is een geteste broncode-/validatiemijlpaal en een build-ready Windows-releasekandidaat. Het is nog geen bewezen eindgebruikersinstaller zolang de native Windows-build en schone-machine-test niet zijn uitgevoerd.
