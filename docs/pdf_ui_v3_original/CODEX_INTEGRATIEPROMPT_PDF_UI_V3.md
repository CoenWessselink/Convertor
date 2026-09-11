# Codex-startprompt — integreer PDF-maatvoering V3 in het totale CWS Convertor-pakket

## Opdracht

Werk deze opdracht in één aaneengesloten build volledig uit in de bestaande repository `CoenWessselink/Convertor`.

Integreer de interactieve PDF-/tekeningenwerkruimte als een volwaardig onderdeel van het totale CWS Convertor-pakket. Gebruik de drie meegeleverde afbeeldingen uitsluitend als visueel referentiedoel. Bouw alle bediening native in de bestaande PySide6-applicatie; toon de mock-ups niet als vervanging voor werkende UI en gebruik geen statische nepknoppen, vooraf getekende maatvoering of hardcoded bewijsresultaten.

De actuele ontwikkellijn bevat reeds de PDF-V2-functies, projectpersistentie, echte EXE-herstarttest en Viewer-correcties. Behoud deze werking. Start met het vastleggen van branch, exacte HEAD, tree-hash en werkboomstatus. Lees `AGENTS.md` en alle repository-instructies volledig. Verwijder of overschrijf geen bestaande gebruikerswijzigingen. Werk vanaf de actuele branch en niet vanaf een oudere snapshot.

## Meegeleverde visuele referenties

Gebruik deze bestanden relatief aan dit document:

1. `references/01_PDF_WERKRUIMTE_VOLLEDIG.png`
   - volledige PDF-/tekeningenwerkruimte;
   - linker productnavigatie;
   - compacte maatvoering-toolbar;
   - centrale A3-tekening;
   - rechter eigenschappeninspecteur;
   - formaat, oriëntatie, schaal en PASS-status.
2. `references/02_MAAT_SELECTEREN_EN_BEWERKEN.png`
   - bestaande maat selecteren;
   - geometrische ankerpunten en snapmarkeringen;
   - maatlijn- en tekstgrips;
   - opnieuw ankeren, verwijderen, verbergen, undo en redo;
   - eigenschappen zoals offset, tolerantie, prefix en suffix.
3. `references/03_ASSEMBLY_PERSISTENTIE_EN_LINTER.png`
   - assembly A1 met afzonderlijke onderdelen P1 en P2;
   - onderdeeloverschrijdende hart-op-hart- en horizontale maat;
   - modelboom, BOM, DrawingLinter en revisiestatus;
   - project opnieuw openen en persistent maatdocument herstellen.

De afbeeldingen zijn ontwerpvoorbeelden en geen testbewijs. Alleen nieuwe screenshots uit de werkelijk gebouwde bronapp, one-folder EXE, portable runtime en geïnstalleerde applicatie gelden als bewijs.

## Functionele integratie

### 1. Eén volwaardige PDF-/tekeningenwerkruimte

Integreer de werkruimte in de bestaande hoofdschil en projectcontext. Zij moet minimaal ondersteunen:

- openen vanuit het hoofdmenu en vanuit geselecteerde onderdelen/merken/assemblies;
- bron uit NC1, IFC, STEP, CWS/canoniek onderdeel of volledig project;
- tekeningstype onderdeel, merk en assembly;
- papierformaten A4, A3, A2, A1 en A0;
- staand/liggend;
- automatische schaal en handmatige genormeerde schalen;
- voor-, boven-, zij-, kop- en isometrisch aanzicht;
- doorsneden, detailviews en vervolgbladen;
- titelblok, revisietabel, materiaal, profiel, positienummer, aantal, status en BOM;
- normale PDF-export en Trusted PDF-route zonder verlies van semantiek.

Gebruik bestaande productie-authorities zoals `DrawingWorkspacePanel`, `ProductionDrawingEngine`, `ProductionDrawingRenderer`, het canonieke model en `ProjectSession`. Maak geen tweede, concurrerende tekenengine of losstaande projectopslag.

### 2. Volledige maatvoering-toolbar

Bied herkenbare, compacte tools voor:

- selecteren;
- horizontale maat;
- verticale maat;
- uitgelijnde maat;
- kettingmaat;
- baseline-maat;
- ordinaat X/Y;
- hoekmaat;
- radius;
- diameter;
- hart-op-hart;
- leader/callout en tekst;
- opnieuw ankeren;
- verplaatsen van maatlijn;
- verplaatsen van maattekst;
- individueel verwijderen;
- multiselectie en bulkbewerking;
- verbergen/tonen;
- undo/redo.

Gebruik waar mogelijk de bestaande applicatie-iconen en kleur-/spacingtokens. Maak ontbrekende iconen als consistente native/vectorassets. Gebruik de rastermock-ups niet als knoppen of achtergronden.

### 3. Handmatige maatvoering door puntselectie

Dit onderdeel is verplicht en mag niet worden gesimuleerd.

- Laat de gebruiker een maattool kiezen en vervolgens één of meer echte geometrische punten selecteren.
- Ondersteun endpoints, midpoints, centers, gatcentra, boog-/cirkelcentra, snijpunten en relevante featurepunten.
- Toon hovermarkering, snaptype, onderdeel-ID, feature-ID en view-ID.
- Gebruik een configureerbaar selectiefilter: alles, eindpunten, middelpunten, centra/gaten en relevante combinaties.
- `Tab` wisselt deterministisch tussen overlappende kandidaten zonder focus uit de tekenwerkruimte te verplaatsen.
- Het eerste anker blijft zichtbaar; na het tweede anker verschijnt een dynamische preview; een volgende klik legt maatlijn/tekstpositie vast.
- Iedere kandidaat-ID is uniek per view en entity; semantisch identieke doelen worden gededupliceerd.
- Een assemblymaat bewaart beide afzonderlijke componentidentiteiten, bijvoorbeeld P1 en P2.
- De maatwaarde wordt uit de geometrie berekend. Alleen expliciete tekstoverride mag de getoonde tekst wijzigen; de werkelijke meetwaarde blijft traceerbaar.

### 4. Selecteren, wijzigen en verwijderen

Een bestaande maat moet direct selecteerbaar zijn via maatlijn, tekst of grip. Toon daarna in het eigenschappenpaneel:

- type en unieke maat-ID;
- berekende waarde en eenheid;
- ankers en betrokken entity-/feature-/view-ID's;
- offset en maatlijnpositie;
- tekstpositie en eventuele override;
- boven-/ondertolerantie;
- prefix en suffix;
- laag, kleur, lijntype, teksthoogte en pijlpunt;
- zichtbaarheid;
- status `RESOLVED`, `STALE`, `ORPHANED` of overeenkomstige bestaande domeinstatus;
- tekeningrevisie, bronrevisie en lockversie.

Wijzigingen moeten onmiddellijk vectorieel in de tekening worden gerenderd en via één transactiemodel worden opgeslagen. Verwijderen werkt voor één maat en multiselectie, vraagt bevestiging waar passend, ondersteunt undo/redo en schrijft auditinformatie. Opnieuw ankeren laat de gebruiker nieuwe echte geometriepunten selecteren zonder de maat-ID onnodig te vervangen.

### 5. Persistentie, revisies en veiligheid

- Sla maatdocumenten per entity op in het bestaande `.cwscproj`-project.
- Bewaar stabiele maat-ID's, ankers, stijl, status, audit en revisie over save/open.
- Bewijs heropening binnen dezelfde applicatie én via een werkelijk tweede EXE-proces met een andere PID.
- Vergelijk vóór en na herstart de project-SHA256 en maat-ID's.
- Bewaar minstens één onafhankelijke A1-maat nadat een andere maat in de revisietest bewust is gewijzigd/verwijderd.
- Autosave/crashherstel mag geen maat verliezen of dupliceren.
- Verwijderde geometrie maakt een maat zichtbaar orphaned; herstel/re-anchor maakt haar weer resolved.
- Een released/read-only tekening blokkeert alle mutaties fail-closed.
- Revisievergelijking bewaart de released snapshot en toont toegevoegde, gewijzigde én verwijderde objecten.
- DrawingLinter toont blokkerende problemen zichtbaar en voorkomt vrijgave bij ontbrekend of tegenstrijdig bewijs.

### 6. Visuele integratie

Benader de informatiehiërarchie uit de afbeeldingen, maar houd de bestaande CWS-stijl leidend:

- centrale tekening krijgt maximale bruikbare ruimte;
- maattools staan gegroepeerd boven het canvas;
- formaat, oriëntatie en schaal blijven direct zichtbaar;
- rechter inspector is contextgevoelig en inklapbaar;
- modelboom/BOM/linter worden alleen getoond wanneer zij relevant zijn;
- actieve tool, hover, eerste anker, preview, selectie, grips, orphaned en read-only hebben onderling duidelijk verschillende toestanden;
- bruikbaar op 100%, 125%, 150%, 175% en 200% Windows-schaal;
- toetsenbordnavigatie, focus, tooltips, toegankelijke namen en voldoende contrast;
- geen clipping, overlappende bediening, onleesbare tekst of horizontale schuifbalk voor de primaire bediening.

Maak na implementatie een visuele vergelijking per referentiebeeld. Leg afwijkingen vast als bewust en functioneel gemotiveerd; kopieer geen toevallige fictieve projectnamen, klantnamen, data of maatwaarden uit de mock-ups.

## Vereiste technische aanpak

1. Inventariseer eerst de bestaande implementatie en maak een requirement-to-code-matrix.
2. Hergebruik en consolideer bestaande productiecode; verwijder geen compatibiliteitsroute voordat tests het aantoonbaar toestaan.
3. Houd model, controller/state-machine, renderer, projectstore en UI van elkaar gescheiden.
4. Alle acties lopen via dezelfde transacties, audit en undo/redo-authority.
5. Voeg gerichte unit-, integratie-, GUI- en packaged-runtime-tests toe.
6. Gebruik echte PySide6-events voor GUI-tests; roep niet rechtstreeks handlers aan wanneer de gebruiker normaal klikt of typt.
7. Bewijs PDF-uitvoer door werkelijk PDF-bestanden te maken, terug te lezen en naar PNG te renderen.
8. Bewijs EXE-gedrag vanuit een schone Windows-build; bron-Python alleen is onvoldoende.
9. Behoud fail-closed checks voor canonieke hashes, bronexactheid, PDF-integriteit, installer en Viewer.
10. Verruim geen acceptatiegrens en verander geen PASS-criteria uitsluitend om CI groen te maken.

## Verplichte test- en bewijsmatrix

Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten:

1. toolbar; 2. selectiefilter; 3. endpoint-hover; 4. gatcentrum-hover; 5. eerste anker; 6. dynamische preview; 7. horizontaal; 8. verticaal; 9. aligned; 10. chain; 11. baseline/ordinate; 12. angle; 13. radius/diameter; 14. center-distance; 15. leader; 16. selectie/grips; 17. properties; 18. maatlijn verplaatsen; 19. tekst verplaatsen; 20. één maat verwijderen; 21. multiselect/bulk; 22. re-anchor; 23. hide/show; 24. undo/redo; 25. section; 26. detail; 27. continuation; 28. assembly P1/P2; 29. project reopen; 30. tweede EXE-restart; 31. crash recovery; 32. orphaned; 33. revision compare; 34. released/read-only; 35. DrawingLinter-block.

Daarnaast:

- voer alle bestaande PDF-V2-tests uit met `0 failed` en `0 skipped`;
- controleer de volledige PDF-functiematrix en behoud 43/43 waar de repository die matrix voorschrijft;
- maak per bewijs-ID een echte PNG met zichtbare test-ID en PASS-status;
- lever een machineleesbaar JSON-manifest met pad, SHA256, runtime, PID waar relevant, status en gekoppelde requirement;
- neem één screenshot op uit bronapp, one-folder EXE, verse portable runtime en geïnstalleerde applicatie;
- controleer dat screenshots niet identiek gekopieerd zijn en werkelijk uit de betreffende runtime komen;
- controleer geproduceerde normale en Trusted PDF op openen, pagina's, vectorinhoud, metadata en renderbaarheid;
- voer alle bestaande conversie-, Viewer-, project-, release- en installer-smokes uit.

## CI en release

Werk door totdat de actuele commit volledig groen is. Vereist:

- schone exacte SHA en ongewijzigde tracked worktree na tests;
- volledige bronacceptatie;
- Windows Phase 1, 2 en 3 groen;
- alle 12 packaged conversieroutes groen;
- PDF-V2 en volledige PDF-functiematrix groen;
- echte app-herstart groen;
- Viewer-gates groen zonder grensverruiming;
- one-folder EXE, verse portable ZIP en installer getest;
- installatie in een schone tijdelijke map, starten, project openen, PDF maken en afsluiten;
- checksums en manifesten gebonden aan dezelfde commit;
- final release artifact pas publiceren wanneer iedere verplichte gate PASS is.

Bij een rode CI-run: download de diagnostics, bepaal de eerste echte oorzaak, herstel productiecode of een aantoonbare fout in de testopzet, voeg een regressietest toe, commit en herhaal. Maskeer geen fout met `continue-on-error`, skips, vaste PASS-data, hogere toleranties of gedeactiveerde checks.

## Opleverbestanden

Lever minimaal:

- Windows x64 installer;
- Windows x64 portable ZIP;
- one-folder runtime of bijbehorend releaseartifact;
- broncommit en volledige SHA;
- `RELEASE_MANIFEST.json` met SHA256 per bestand;
- `PDF_FUNCTION_GAP_MATRIX.json` en `.md` met totalen en percentages;
- `PDF_RUNTIME_EVIDENCE.json`;
- alle 35 PDF-GUI-screenshots plus extra runtimebeelden;
- normale en Trusted voorbeeld-PDF;
- voorbeeldproject `.cwscproj` voor P1 en assembly A1;
- revision audit en migratierapport;
- test-/CI-samenvatting met aantallen passed, failed en skipped;
- beknopte gebruikershandleiding voor maat toevoegen, selecteren, verplaatsen, opnieuw ankeren en verwijderen.

## Definitie van gereed

Meld het werk uitsluitend als 100% gereed wanneer:

- iedere functionele eis aan productiecode én testbewijs is gekoppeld;
- er geen verplichte `FAIL`, `PARTIAL`, `BLOCKED`, `NOT_IMPLEMENTED`, `NOT_INTEGRATED`, `NOT_TESTED` of `SKIPPED` resteert;
- percentages uit getelde requirements worden berekend en samen optellen tot 100%;
- de drie distributievormen werkelijk starten en dezelfde kernfuncties uitvoeren;
- de PDF-maatvoering na opslaan, projectheropening, tweede EXE-herstart en crashherstel intact blijft;
- CI op exact de opgeleverde commit groen is;
- de downloadbare releaseartifacten bestaan en hun checksums zijn gecontroleerd.

Als iets niet aantoonbaar gereed is, rapporteer dan exact wat ontbreekt, waarom, welk bewijs ontbreekt en welk bestand of welke test dit blokkeert. Noem het resultaat dan niet 100%.

## Werkwijze voor Codex

Begin direct zonder een nieuwe fasering aan de gebruiker te vragen. Werk zelfstandig door in één build, geef korte voortgangsupdates, maak kleine logisch samenhangende commits en push alleen gecontroleerde wijzigingen. Stop niet na code of na een lokale test: volg ook GitHub Actions tot de finale uitslag en lever de daadwerkelijke installatie- en bewijsbestanden op.
