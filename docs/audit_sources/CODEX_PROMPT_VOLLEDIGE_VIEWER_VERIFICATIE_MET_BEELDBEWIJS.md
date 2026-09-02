# Codex-opdracht: volledige Viewer-verificatie met beeldbewijs

Je werkt als onafhankelijke release-auditor van de CWS Convertor Viewer. Controleer de actuele repository volledig en bepaal uitsluitend op basis van reproduceerbaar bewijs of de Viewer 100% releasegereed is.

## Uitgangssituatie

- Repository: `CoenWessselink/Convertor`
- Werkbranch: `agent/cws-product-ui-reintegration-v1`
- Bekende referentiecommit: `9feb78c701f9551745d204a0446746b6d88513bd`
- Controleer bij aanvang de actuele remote HEAD. Als deze afwijkt, noteer zowel de referentiecommit als de werkelijk geteste commit. Alle resultaten en artefacten moeten aan één exacte, volledige commit-SHA zijn gekoppeld.
- Gebruik de meegeleverde gap-analyse en gap-matrix als invoer:
  - `CWS_CONVERTOR_VIEWER_COMPLETE_GAP_ANALYSE_2026-09-02.md`
  - `CWS_CONVERTOR_VIEWER_COMPLETE_GAP_MATRIX_2026-09-02.json`
  - `CWS_CONVERTOR_VIEWER_GAP_ANALYSE_NA_AANPASSING_2026-09-02.md`
  - `CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json`

## Strikte werkwijze

1. Voer een onafhankelijke controle uit. Wijzig geen productiecode, requirements, drempelwaarden of bestaande testverwachtingen om een PASS te verkrijgen. Alleen nieuwe audit-, log-, rapport- en bewijsbestanden zijn toegestaan.
2. Begin met een schone checkout van de actuele branch. Leg vast: repository, branch, volledige SHA, UTC-tijd, besturingssysteem, CPU, GPU, RAM, schermresolutie, DPI-schaal, Python-versie, driver-versie en gebruikte build.
3. Controleer eerst of de vier aangeleverde rapporten onderling consistent zijn. Ontdubbel bestanden op SHA-256 en benoem verschillen expliciet.
4. Inventariseer alle actieve requirements vanuit de gezaghebbende bron in de repository. Het verwachte aantal is 317, maar hardcode dit niet. Rapporteer het dynamisch gevonden aantal en verklaar iedere afwijking.
5. Koppel iedere requirement aan minimaal één controle en aan exact bewijs. Een ontbrekende, verouderde, niet-reproduceerbare of niet aan de actuele SHA gebonden controle is `FAIL` of `BLOCKED`; nooit `PASS`.
6. Hergebruik bestaand bewijs alleen als inhoud, testobject, configuratie en volledige commit-SHA aantoonbaar overeenkomen. Broncode of alleen een testdefinitie geldt niet als uitvoeringsbewijs.
7. Verberg, herclassificeer of relativeer geen fouten. Een overgeslagen test is geen PASS. Een menselijke acceptatie zonder ondertekend bewijs is geen PASS. Een XSD-valide BCF-export is geen productcertificering.
8. Als de omgeving een verplichte controle niet ondersteunt, voer die controle uit op een gekwalificeerde Windows/GPU-runner of markeer hem `BLOCKED`. Gebruik geen gesimuleerde of gemockte renderer als releasebewijs.

## Uit te voeren controles

### A. Repository, build en release-integriteit

- Controleer werkboom, submodules, lockfiles, dependency-resolutie en reproduceerbaarheid van de releasebuild.
- Bouw de Viewer zoals deze daadwerkelijk wordt uitgebracht, inclusief installer/package.
- Controleer digitale ondertekening, checksums, virusscanresultaat, versiebron, bestandsversies, productnaam, startmenu-/desktopkoppelingen, installatie, upgrade en uninstall indien dit releasevereisten zijn.
- Voer smoke-tests uit op de gebouwde artefacten, niet alleen vanuit de broncode.
- Controleer dat elk bewijsbestand de exacte SHA en buildchecksum bevat.

### B. Volledige traceability van alle requirements

- Genereer een actuele requirementsmatrix met precies één rij per actief requirement.
- Verplichte kolommen: `requirement_id`, `omschrijving`, `bron`, `controle`, `platform`, `resultaat`, `bewijs`, `bewijs_sha256`, `geteste_commit`, `opmerking`.
- Toegestane resultaten: `PASS`, `FAIL`, `BLOCKED`, `NOT_APPLICABLE`.
- `NOT_APPLICABLE` vereist een concrete, controleerbare motivering en telt niet stilzwijgend als geïmplementeerd.
- Controleer dat CI hetzelfde dynamisch bepaalde aantal requirements afdwingt en niet het oude aantal van 51.
- Verifieer de uiteindelijke matrix met een script: unieke IDs, geen ontbrekende rijen, geen bewijslinks naar niet-bestaande bestanden en geen SHA-mismatches.

### C. Geautomatiseerde tests en statische controles

- Voer alle unit-, integratie-, broncontract-, import-, packaging-, schema-, regressie- en end-to-endtests uit die in de repository aanwezig zijn.
- Voer de volledige releaseworkflow uit op de actuele SHA.
- Rapporteer per suite: commando, start/eindtijd, duur, aantallen PASS/FAIL/SKIP/XFAIL, exitcode en logpad.
- Onderzoek iedere skip en iedere platformafhankelijke fout afzonderlijk.
- Leg vast of eerder bekende problemen nog bestaan, waaronder packaged-runtime DLL-mismatches, ontbrekende CasADi-DLL's, launcher-selftestproblemen en EGL/OpenGL-problemen.

### D. HVPC-performance op gekwalificeerde hardware

Gebruik het exacte HVPC IFC-model en noteer bestandsnaam, bytegrootte en SHA-256. Gebruik een native releasebuild op representatieve Windows-hardware met echte GPU-rendering. Sluit prewarming, vooraf gevulde caches en eerdere processtatus uit van een cold-loadmeting.

Voer minimaal vijf volledig onafhankelijke cold runs en vijf warm runs uit. Verwijder niets als uitbijter. Leg ruwe samples en aggregaten vast.

Harde acceptatiecriteria:

- cold exact load: iedere run maximaal `5,000 s`;
- gemiddelde interactieve framerate: minimaal `30 FPS`;
- frame time p95: maximaal `33 ms`;
- inputlatentie p95: maximaal `35 ms` en p99 maximaal `50 ms`;
- picklatentie p95: maximaal `150 ms`;
- 10 minuten continue orbit/pan/zoom/selectie zonder stall;
- geheugendrift tijdens de soak: minder dan `10%`;
- nul crashes, verkeerde picks, verborgen-object-picks of worker failures;
- alle verwachte geometrie-resources geladen, met expliciete teller.

Meet cold load vanaf het starten van het niet-actieve proces tot de eerste volledig interactieve frame waarin het volledige exacte model zichtbaar en selecteerbaar is. Rapporteer worker-start/prewarm apart, maar trek die tijd niet af als deze voor een echte koude gebruikersstart nodig is.

Bewaar ruwe JSON/CSV, runnergegevens, logs en grafieken. Toon het testresultaat ook in beeldbewijs met de volledige Viewer en een leesbaar performancepaneel of een controleerbare combinatie van Viewer-opname en meetrapport.

### E. Functionele Viewer-controle

Controleer met echte representatieve IFC-bestanden, inclusief het HVPC-model:

- openen, exact laden, annuleren, heropenen en foutafhandeling;
- modelboom, zoeken, filteren, properties en GlobalId;
- selectie, multi-selectie, isolate, hide/show, reset en picking;
- orbit, pan, zoom, fit, view cube en standaardaanzichten;
- perspectief en orthografische camera;
- clipping/sectioning en relevante meetfuncties;
- shaded, wireframe/x-ray indien vereist en echte hidden-line rendering;
- transparantie, kleur, materiaal, diepte, occlusie en randen;
- grote modellen, meerdere modellen en het tweede vereiste grote testmodel;
- reviewworkflow, viewpoints, issues, comments en BCF;
- native schermafbeeldingen/export vanuit de Viewer;
- keyboardbediening, focusvolgorde, zichtbare focus, schaalbaarheid en relevante toegankelijkheidseisen;
- bruikbaarheid van de model-dominante layout en panelen op ondersteunde resoluties en DPI-instellingen.

### F. Hidden-line rendering

- Controleer native op de gekwalificeerde GPU-runner dat verborgen lijnen daadwerkelijk niet zichtbaar zijn.
- Gebruik minstens drie camerastandpunten: buitenaanzicht, detail met sterke occlusie en doorsnede/complex interieur.
- Vergelijk tegen wireframe en shaded zodat zichtbaar is dat hidden-line geen alias van een andere modus is.
- Controleer selecteren, hide/isolate, transparantie en camerabeweging in deze modus.
- Voeg per camerastandpunt ongecropte screenshots toe met dezelfde camera en viewport voor `shaded`, `wireframe` en `hidden-line`.

### G. BCF 2.1

- Maak meerdere issues met topicmetadata, status, prioriteit, assignee, due date, comments, perspectief- en orthografische viewpoints en IFC-componentselecties op GlobalId.
- Exporteer BCF vanuit de releasebuild.
- Controleer ZIP-structuur, veilige XML-verwerking, determinisme waar vereist en alle officiële buildingSMART BCF 2.1 XSD's.
- Importeer het resultaat opnieuw en vergelijk semantisch alle velden en viewpoints.
- Test ongeldige, corrupte, te grote en path-traversal/XXE-achtige invoer veilig.
- Als gecertificeerde BCF-export wordt geclaimd, lever het geldige externe certificaat of officiële conformance-resultaat. Zonder dat bewijs blijft deze eis open, ook als alle XSD-tests slagen.

### H. Visuele en Trimble-pariteit

- Gebruik de overeengekomen referentiebeelden of een naast elkaar draaiende referentietoepassing. Ontbreken die, markeer Trimble-pariteit `BLOCKED`.
- Gebruik exact hetzelfde model, camera, projectie, viewport, resolutie, DPI, clipping en zichtbaarheidsstatus.
- Maak per kernscenario een drieluik: `referentie`, `actuele Viewer`, `pixel-diff/overlay`.
- Rapporteer objectieve afwijkingsmetingen waar zinvol, maar vervang menselijke acceptatie daar niet mee.
- Laat een bevoegde reviewer visuele pariteit expliciet accepteren met naam/rol, datum, geteste SHA en lijst van beelden. Zonder die acceptatie is de eis niet PASS.

### I. CI en releasebewijs

- Controleer de actuele workflowuitvoering voor de exact geteste SHA.
- Controleer dat alle vereiste jobs daadwerkelijk zijn uitgevoerd op het juiste OS/hardwareprofiel.
- Controleer artifactnamen, retentie, inhoud, checksums en SHA-binding.
- De releasegate moet falen zodra één actief requirement niet PASS is, behalve expliciet goedgekeurde `NOT_APPLICABLE`-gevallen volgens het releasebeleid.
- Neem screenshots op van de workflow-samenvatting en relevante jobs, maar bewaar ook machineleesbare workflowdata/logs; een screenshot alleen is niet voldoende.

## Verplicht beeldbewijs

Maak echte PNG-opnamen van de geteste releasebuild. Geen mockups, gereconstrueerde UI of alleen broncodebeelden. Gebruik originele resolutie en zorg dat de volledige applicatierand, titel/versie, model en relevante panelen zichtbaar zijn. Voeg waar mogelijk in de app of bewijscompositie een niet-overlappende auditstrook toe met volledige commit-SHA, buildchecksum, UTC-tijd, machine-ID en scenarionaam. Bewaar daarnaast altijd de onbewerkte opname.

Minimaal vereiste beelden:

1. applicatiestart en About/versie;
2. volledig geladen HVPC-model met modelboom en properties;
3. geselecteerd element met GlobalId;
4. shaded buitenaanzicht;
5. wireframe vanuit exact dezelfde camera;
6. hidden-line vanuit exact dezelfde camera;
7. hidden-line detail met occlusie;
8. clipping/section-resultaat;
9. isolate/hide en correcte selectie;
10. perspectief- en orthografische weergave;
11. BCF-issue met metadata en viewpoint;
12. succesvolle BCF 2.1 XSD-validatie en roundtripresultaat;
13. native Viewer-screenshot/exportresultaat;
14. performance tijdens HVPC-interactie;
15. resultaten van cold exact loads en 10-minuten-soak;
16. ondersteunde minimumresolutie en hoge-DPI-weergave;
17. keyboardfocus/toegankelijkheidsstatus;
18. Trimble/referentie, Viewer en diff voor elk verplicht kernscenario;
19. CI-overzicht voor de exacte SHA;
20. uiteindelijke releasegate met totaal aantal requirements en verdict.

Naamgeving: `EVID-<requirement-id>-<scenario>-<sha8>-<utc>.png`.

Maak `evidence/manifest.json` met per bestand: relatieve naam, SHA-256, bestandsgrootte, pixelafmetingen, opnametijd, volledige geteste commit, buildchecksum, machine-ID, scenario, requirement-IDs, opnamewijze en aanduiding `raw` of `annotated`. Controleer automatisch dat alle genoemde bestanden bestaan en dat hun hashes kloppen.

## Op te leveren resultaten

Plaats alle uitvoer in een nieuwe map `release_audit/<volledige-sha>/` zonder bestaande bewijsbestanden te overschrijven:

- `VIEWER_RELEASE_AUDIT.md`: volledige Nederlandstalige audit met methode, omgeving, resultaten, afwijkingen en conclusie;
- `VIEWER_RELEASE_GAP_MATRIX.json`: machineleesbare matrix voor alle actuele requirements;
- `VIEWER_RELEASE_GAP_MATRIX.csv`: dezelfde matrix voor menselijke controle;
- `VIEWER_RELEASE_EVIDENCE.pdf`: compacte bewijsbundel met onderschriften, requirement-ID, SHA en verwijzing naar de onbewerkte bestanden;
- `evidence/`: alle ruwe en geannoteerde PNG's plus `manifest.json`;
- `logs/`: volledige onbewerkte logs;
- `metrics/`: ruwe performance- en soakdata plus grafieken;
- `bcf/`: geëxporteerde BCF, XSD-validatierapport en roundtripvergelijking;
- `CHECKSUMS.sha256`: hashes van alle auditbestanden;
- `REPRODUCE.md`: exacte commando's en stappen om iedere controle opnieuw uit te voeren.

Maak bovendien een korte eindtabel met:

| Onderdeel | Resultaat | Kernbewijs | Resterende gap |
| --- | --- | --- | --- |
| 317/dynamisch gevonden requirements |  |  |  |
| HVPC cold exact load |  |  |  |
| HVPC interactieve performance |  |  |  |
| Visuele pariteit |  |  |  |
| Trimble-pariteit |  |  |  |
| Hidden-line |  |  |  |
| BCF 2.1 schema/roundtrip |  |  |  |
| BCF-certificering |  |  |  |
| Packaging/installatie |  |  |  |
| Toegankelijkheid/UX |  |  |  |
| CI en exact-SHA-releasebewijs |  |  |  |

## Beslisregel

Geef alleen het eindverdict `100% RELEASEGEREED` als:

- ieder actief requirement aantoonbaar `PASS` is;
- alle harde performancegrenzen zijn gehaald;
- visuele en Trimble-pariteit formeel zijn geaccepteerd;
- hidden-line native bewezen is;
- de vereiste BCF-certificering daadwerkelijk is aangetoond;
- packaging en native Windows-runtime slagen;
- CI alle dynamisch gevonden requirements voor exact dezelfde SHA controleert;
- alle bewijsbestanden aanwezig, leesbaar, integer en SHA-gebonden zijn.

Zodra één onderdeel `FAIL`, `BLOCKED`, onbewezen, alleen lokaal gesimuleerd of aan een andere commit gekoppeld is, luidt het verdict `NIET RELEASEGEREED`. Vermeld dan precies welke gaps resteren, wat het gemeten resultaat is, welk criterium geldt, welk bewijs ontbreekt en wat de kleinste concrete vervolgactie is. Gebruik nooit een afgerond percentage om open releaseblokkades te maskeren.

Sluit af met:

1. de exact geteste volledige commit-SHA;
2. het dynamisch gevonden aantal requirements en de telling PASS/FAIL/BLOCKED/NOT_APPLICABLE;
3. het releaseverdict;
4. de lijst met resterende blockers in prioriteitsvolgorde;
5. de paden naar rapport, matrix, bewijs-PDF, beeldmanifest en checksums;
6. een expliciete verklaring dat geen bewijs of drempelwaarde is gemanipuleerd.
