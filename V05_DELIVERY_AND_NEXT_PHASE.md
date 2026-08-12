# v0.5.1 - opleverstatus en vervolgvolgorde

## Doel van deze fase

Deze fase bouwt voort op de bestaande v0.4-conversiekern en voegt een veilige, bidirectionele PDF-/AI-laag toe. De werkende NC1-, STEP- en IFC-routes zijn behouden. AI is uitsluitend adviserend; productiegeometrie, maatwaarden, roundtripcontrole en exportvrijgave blijven deterministisch.

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
- embedded `converter-model.json` en `converter-manifest.json`;
- oorspronkelijke bron als PDF-bijlage waar beschikbaar;
- XMP-identiteit en hashes;
- checksum van canoniek model, geometrie, bron en zichtbare tekening;
- exacte terugconversie naar NC1, STEP en IFC wanneer alle controles slagen;
- blokkade bij zichtbare manipulatie, beschadigd manifest, ontbrekende bijlage of maatgrafiekfout.

### 3. Externe vector-PDF-analyse en plaatreconstructie

- lokale tekst- en vectorclassificatie;
- herkenning van bladformaat, schaal, positie, profiel, materiaal, lengte, aantal, merk, onderwerp en callouts;
- gesloten contourdetectie en collineaire vereenvoudiging;
- cirkel-/gatdetectie en Bezier-naar-boogfitting;
- conflictcontrole tussen geschreven en gemeten waarden;
- confidence, bronbewijs en gerichte controlevragen;
- eenvoudige platen/strips kunnen na expliciete review naar Trusted PDF en daarna NC1/STEP/IFC.

### 4. Deterministische maatgrafiek

- feature-gekoppelde maatobjecten met stabiele ID's;
- totale X/Y-maten, gatdiameters, X/Y-ordinaten, radii, plaatdikte en profielmaten;
- vaste datums en maatketens;
- provenance, confidence, bronveld en geometrische ankers per maat;
- dekking- en integriteitsvalidatie als harde productiepoort;
- dimension graph tamper-test toegevoegd.

### 5. Interactieve menselijke review

- bron-PDF links en deterministisch 2D-model rechts;
- bronbewijs en modelonderdelen markeren;
- toegestane velden, gaten en contourpunten corrigeren;
- expliciet bevestigen en vragen beantwoorden;
- reviewer/commentaar/audit vastleggen;
- strikte allow-list en evidenceguard;
- GUI-knop **Interactief reviewen** en CLI-route `pdf-review`.

### 6. Veilige AI-functie

- lokale offline semantische provider;
- optionele OpenAI Responses-provider via begrensd JSON-schema;
- configureerbare modelnaam, standaard `gpt-5.6`;
- expliciete toestemming per cloudanalyse;
- `store=false` in de cloudrequest;
- semantische whitelist en recursieve geometry-/machinecodeguard;
- deterministische herkenning heeft voorrang en wordt niet stilzwijgend door AI overschreven;
- auditinformatie met hashes en request-ID's, zonder klantinhoud in het lokale auditrecord.

### 7. Semantische IFC voor gereviewde platen

- gereviewde plaat wordt als IfcPlate geschreven;
- analytische swept solid in plaats van alleen een generiek meshobject;
- ronde gaten als analytische voids;
- contourbogen en hoeveelheden worden vastgelegd;
- exacte converterpayload blijft aanwezig voor betrouwbare roundtrip.

### 8. GUI en CLI

- tabblad `PDF / Tekening`;
- Trusted PDF-inspectie;
- externe PDF-analyse met lokale of optionele cloud-AI;
- modelkeuze en expliciete cloudtoestemming;
- PDF-voorvertoning, confidence, bronbewijs, waarschuwingen en vragen;
- interactieve reviewdialoog;
- CLI-routes voor PDF-generatie, analyse, review en Trusted PDF-terugconversie;
- JSON-rapportage en batchinvoer;
- strikte productievalidatie kan niet worden uitgeschakeld.

### 9. Windows-releaseketen

- Python 3.12 x64 als beoogde buildruntime;
- PyInstaller `onedir` voor GUI en CLI;
- Inno Setup-project voor één installer-EXE;
- portable ZIP en SHA-256-generatie;
- optionele bestandskoppelingen voor NC/NC1/STEP/STP/IFC;
- PDF-contextmenu zonder de standaard PDF-lezer over te nemen;
- GitHub Actions-workflow met compile-, kern-, PDF-, maatgrafiek-, review- en GUI-smokes;
- stille installer-/uninstaller-smoke met Python verwijderd uit `PATH`.

## Werkelijk uitgevoerde tests

### Conversiekern

| Testgroep | Geslaagd | Totaal |
|---|---:|---:|
| NC1 -> STEP | 24 | 24 |
| STEP -> NC1 | 19 | 19 |
| NC1 -> IFC -> STEP -> NC1 | 4 | 4 |
| STEP -> IFC -> NC1 -> STEP | 4 | 4 |

### PDF, review en AI

| Testgroep | Geslaagd | Totaal |
|---|---:|---:|
| NC1 -> Trusted PDF -> exact NC1 | 24 | 24 |
| STEP -> Trusted PDF -> exact STEP | 19 | 19 |
| Focus Trusted PDF -> IFC | 2 | 2 |
| Synthetische LO4 externe-PDF-keten | 1 | 1 |
| AI-/integriteits-/review-/ambiguiteitstests | 11 | 11 |

De synthetische LO4-keten reconstrueert positie LO4, profiel STRIP5*120, materiaal S235JR, lengte 160, aantal 4, merk MLO4, twee R13,5-bogen en één Ø14-gat op X/Y 20 mm. Na review zijn NC1, analytische STEP, semantisch IfcPlate en een Trusted PDF gemaakt. De maatgrafiek was voor review, na review en in de Trusted PDF geldig met 100% dekking.

De echte `Pos LO4 - LOSSE PLAAT.pdf` was in deze runtime niet als lokaal PDF-binair bestand beschikbaar. Daarom is daarvoor nog geen echte vector-/geometrieclaim gedaan.

## Wat nog niet als gereed mag worden beschouwd

- productiebrede reconstructie van willekeurige profiel- en meer-aanzichttekeningen;
- scan-OCR, deskew, foto-/perspectiefcorrectie en symboolvarianten op productieniveau;
- volledig vrije CAD-schetseditor, undo/redo en handmatig verplaatsbare maatankers;
- volledige hidden-line-, detail-, snede- en algemene maatplaatsingsengine;
- formele belastingstest op zeer grote IFC-/STEP-projecten;
- native Windows-installerbuild en schone-machine-installatietest;
- uitgebreide materiaal-/onderdeeleditor, prijzen, bewerkingstijden en versleepbare eigenschappenlijst;
- projectbeheer, licenties en online jobomgeving.

## Juiste vervolgvolgorde

1. **Echte LO4-PDF als lokaal testbestand opnemen.** Vectorpaden, tekstposities, maatlijnen, contouren en de huidige reconstructie tegen de werkelijke Tekla-PDF valideren.
2. **Profiel- en meer-aanzichtreconstructie uitbreiden.** Eerst standaard I/U/L/T/koker/rond met orthografische viewkoppeling en stabiele featurecorrespondentie.
3. **Tekeninggenerator uitbreiden.** Hidden lines, sneden, detailaanzichten, collision-free maatplaatsing en handmatig verplaatsbare maatankers.
4. **Scan-/OCR-pipeline toevoegen.** Deskew, perspectiefcorrectie en OCR alleen als reviewplichtige conceptmodus met dezelfde productieblokkades.
5. **Multi-part IFC/PDF, performance en batchrapportage harden.** Inclusief grote-bestandentests en geheugenlimieten.
6. **Windows x64-release bouwen.** Installer en portable ZIP op Windows maken, daarna op een schone machine zonder Python installeren en de acceptatieset uitvoeren.
7. **Materiaal-/onderdeeleditor en eigenschappenlijst bouwen.** Pas nadat de geometrie- en reviewbasis stabiel is: tabbladen, bewerkingen, hoeken, gaten, coderingen, prijzen, tijden en versleepbare/sorteerbare kolommen.
8. **Projectopslag, licenties en online/cloud-jobmodel afronden.** Deze functies mogen de geometrische kern en veiligheidslaag niet omzeilen.

## Vrijgavebeoordeling

v0.5.1 is een geteste broncode-/validatiemijlpaal en een build-ready Windows-releasekandidaat. Het is nog geen bewezen eindgebruikersinstaller zolang de native Windows-build en schone-machine-test niet zijn uitgevoerd.
