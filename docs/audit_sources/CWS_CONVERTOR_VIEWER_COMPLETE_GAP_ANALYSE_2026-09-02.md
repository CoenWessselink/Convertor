# CWS Convertor — complete Viewer-gapanalyse

**Datum:** 2 september 2026  
**Scope:** de complete Viewer-functionaliteit binnen CWS Convertor, inclusief de koppelingen met Project, Productie, Controle en Uitvoer  
**Auditbasis:** actuele GitHub-broncode, gecommitteerde validatie-evidence, bestaande Viewer 1000%-documentatie en eerdere productscope uit de chat  
**Geaudite branch:** agent/cws-product-ui-reintegration-v1  
**Geaudite HEAD:** a2cd946d1c2eef9ea454c2feebd4770f87600576  
**Productversie in bron:** CWS Convertor 0.10.18-beta-dev  
**Project Model:** 2.25  
**Canonical Part:** 1.1  

---

## 1. Managementsamenvatting

De CWS Viewer is geen prototype meer. De bron bevat een brede, samenhangende Viewer met exact geometry, projectscene, selectie, zichtbaarheid, secties, metingen, saved views, review, revision compare, model control, exports en koppelingen naar de rest van CWS Convertor.

De eerlijke eindconclusie is echter:

> **Functioneel grotendeels gebouwd, maar nog niet aantoonbaar 100% releasegereed.**

De grootste resterende gaten zijn niet “nog een knop toevoegen”, maar:

1. **Werkelijke HVPC-interactieprestaties:** 20,39 FPS gemiddeld, frame-p95 50,66 ms en input-to-render-p95 269,68 ms. Dat voelt stroperig en faalt de gestelde performancegrenzen.
2. **Cold exact load:** 7,939 seconden waar maximaal 5 seconden is vereist.
3. **Visuele en ergonomische Viewer-pariteit:** alle referentievergelijkingen staan nog op HUMAN_REVIEW_REQUIRED; de huidige Viewer is aantoonbaar dichter en minder modelgericht dan de referenties.
4. **Releasebewijs op de huidige exacte commit:** de laatste volledige release-evidence hoort bij een oudere commit. De huidige HEAD ligt elf commits later.
5. **Acceptatie-automatisering:** de workflow controleert nog “51 of 51”, terwijl de actieve traceability 317 requirements bevat.
6. **Object-voor-object Trimble-pariteit:** timingvergelijking bestaat, maar visuele en gedragsmatige pariteit is nog BLOCKED_EXTERNAL_EVIDENCE.
7. **Reproduceerbare duurtest en geheugengrens:** een 10-minuten-soak wordt in traceability als PASS genoemd, maar het aangewezen bewijsbestand is niet aanwezig op de geaudite branch. In een andere representatieve run is RSS-drift 11,52%, boven de grens van 10%.

De aanbevolen koers is daarom **geen herbouw**, maar één gecontroleerde closure-build die performance, UX, ontbrekende eindfuncties en exact-HEAD releasebewijs tegelijk sluit.

---

## 2. Scorekaart

De percentages hieronder zijn indicatieve volwassenheidsscores, geen vervanging voor acceptatietests.

| Domein | Score | Oordeel |
|---|---:|---|
| Functionele bronimplementatie | 92% | Zeer breed geïmplementeerd |
| Integratie met Project/Productie/Controle/Uitvoer | 90% | Architectuur en routes grotendeels aanwezig |
| Traceability en gecommitteerde evidence | 78% | Veel bewijs, maar deels verouderd of intern tegenstrijdig |
| Grote-modelperformance en Viewer-feel | 58% | Warm snel, echte interactie nog onvoldoende |
| Visuele/ergonomische pariteit | 48% | Structureel gekoppeld, visueel niet geaccepteerd |
| Releasebewijs op exacte huidige HEAD | 0% | Geen complete releasebinding op a2cd946 |

**Belangrijk onderscheid:**

- De bronfunctionaliteit is ongeveer 92% aanwezig.
- De huidige exacte build is niet releasegekwalificeerd.
- Een simpele optelsom tot één “gereedheidspercentage” zou de P0-gaten verhullen.

---

## 3. Product- en architectuurbasis

De gewenste geïntegreerde productstroom uit de eerdere scope is:

**Inlezen → Viewer/Project → Bewerken → Converteren → Controleren → PDF/Tekening → Tekeningen → Scribing → Hoeveelheden/Excel → Exporteren**

De actuele bron sluit hier in grote lijnen op aan:

- vijf hoofdwerkruimtes: Project, Viewer, Productie, Controle en Uitvoer;
- één canoniek Project Model;
- één projectscene en één globale selectiestaat;
- stabiele bron- en object-ID’s;
- object-, part- en assemblyniveaus;
- veilige downstreamkoppelingen;
- machineschrijven en fysieke transfer blijven standaard geblokkeerd zolang kwalificatie ontbreekt.

### Architectuursterktes

- Geen noodzaak voor een tweede Viewer-engine.
- Canonieke project- en workbenchpaden zijn aanwezig.
- Scene-, selectie-, BOM- en manufacturingdata worden via stabiele identifiers verbonden.
- Exact/proxy/herkomstinformatie is in de Viewer zichtbaar te maken en te bewijzen.
- Worker pool, cache en warmstart zijn structureel ontworpen, niet als losse demo.
- Viewerfuncties zijn gekoppeld aan review, productievoorbereiding, scribing en export.

### Architectuurrisico’s

- Er zijn meerdere versie-identiteiten in omloop. De Viewer-packageversie vermeldt nog 1.0.0-dev0, terwijl elders het V15-previewcontract 1.4.0-v15-preview.2 wordt gebruikt.
- Autoriteitsdocumenten lopen achter op de huidige branch en HEAD.
- Legacy- en compatibilitylagen vergroten het risico op dubbele routes of afwijkend gedrag.
- Module-imports trekken CadQuery en VTK vroeg naar binnen, waardoor lichte unit- en contracttests niet onafhankelijk kunnen draaien.

---

## 4. Wat aantoonbaar is gebouwd

### 4.1 Projectscene en geometrie

- IFC- en STEP-geometrie kunnen als exacte projectscene worden geladen.
- De HVPC-dataset bevat 6.626 IFC-records en 5.725 fysieke objecten.
- Voor alle 5.725 fysieke objecten is een exact CWS-mesh/source-ID aangetoond.
- Ontbrekende, dubbele, lege en box-fallbackobjecten: nul.
- Geometry resources: 1.496; hergebruikte instances: 4.229.
- Verdiepingen en assen zijn gerepresenteerd: 8 levels en 192 axes.
- Proxygebruik wordt getagd en kan fail-closed worden behandeld.

**Oordeel:** objectcompleetheid is een duidelijke PASS.

### 4.2 Navigatie en camera

- orbit, pan en zoom;
- standaardaanzichten;
- perspective/orthographic;
- pivot/focusgedrag;
- fit/zoom extents;
- world-up orbit en roll suppression;
- project-, assembly- en partniveau;
- box- en crossingselectie.

**Oordeel:** gebouwd en deels geautomatiseerd bewezen; exacte waarneembare Trimble-pariteit is nog niet extern gesloten.

### 4.3 Selectie en synchronisatie

- whole-object selectie;
- single- en Ctrl-multiselect;
- selectie op object-, part- en assemblyniveau;
- select all en clear;
- selectie via 3D, boom, grid en BOM;
- bidirectionele synchronisatie;
- wrong-pick count van nul in de representatieve warmstartmeting;
- selectie blijft gekoppeld aan stabiele identifiers.

**Oordeel:** functioneel sterk; performance bij grote selecties en huidige packaged HEAD moet opnieuw worden bewezen.

### 4.4 Zichtbaarheid en weergave

- hide, show, show all;
- isolate;
- ghost/transparantie;
- source colors/IFC-kleuren;
- shaded, shaded plus edges en wireframe;
- grid- en asoverlay;
- clip- en sectieweergave;
- explode.

**Expliciete functionele lacune:** echte hidden-line removal is niet geïmplementeerd. De enum bestaat, maar de controller weigert de modus en verwijst naar shaded plus edges of wireframe.

### 4.5 Meten

- afstand;
- hoek;
- radius;
- coördinaten;
- from/to-punten;
- live preview en foregroundlabels;
- bewijsclassificatie exact, verified of proxy;
- JSON-, CSV- en PDF-export;
- koppeling met scene-ID’s.

**Oordeel:** uitgebreide implementatie. De huidige exacte Windows-build moet de volledige set nog reproduceerbaar bewijzen.

### 4.6 Secties, clipbox en explode

- doorsnede over X, Y en Z;
- section-from-face;
- flip;
- aan/uit;
- verwijderen;
- clipbox;
- explode;
- undo/redo en historykoppeling.

**Oordeel:** gebouwd. Acceptatie moet op de current HEAD, met echte HVPC-geometrie, opnieuw worden gebonden.

### 4.7 Saved views, groepen en review

- saved views;
- groepen;
- slideshow;
- markups;
- review issues en ToDo’s;
- comments;
- stale-referencebehandeling;
- screenshots;
- portable review package.

**Expliciete functionele lacune:** BCF-export is bewust niet schema-gecertificeerd. Het systeem weigert daarom terecht een bestand als geldige BCF te presenteren en gebruikt .cwsreview als ondersteund pakket.

### 4.8 Revisievergelijking en modelcontrole

- revision compare;
- deviation en impact;
- brede clashdetectie;
- exacte controle van geselecteerde paren;
- issuekoppeling en review;
- veilige scheiding tussen analyse en fysieke machineactie.

**Oordeel:** functioneel aanwezig; representatieve current-HEAD packaged evidence is onvolledig.

### 4.9 Zoeken, eigenschappen en werkruimte

- properties;
- search en filter;
- virtuele grids;
- tree/list/BOM-relaties;
- lay-out en dockstructuur;
- vijf hoofdwerkruimtes;
- 31 gecapteerde schermoppervlakken;
- 226 gecontroleerde UI-controls zonder ontbrekende of dubbele test-ID’s.

**Oordeel:** controls zijn breed aanwezig. De informatiedichtheid en visuele hiërarchie zijn nog geen referentie-PASS.

### 4.10 Export en downstreamintegratie

- screenshots;
- meetexports;
- reviewpakket;
- routes naar manufacturing, scribing, machine, nesting en algemene export;
- globale undo/redo/activity/problems/settings/command/print zijn in runtime-controltests gevonden;
- fysieke machine-transfer blijft veilig geblokkeerd.

**Oordeel:** routes zijn aanwezig, maar current-HEAD one-folder, portable, installer, associations en uninstall zijn niet opnieuw volledig bewezen.

---

## 5. Complete functionele gapmatrix

Legenda:

- **PASS:** functie en passend bewijs aanwezig.
- **PARTIAL:** gebouwd, maar bewijs, UX of representatieve schaal ontbreekt.
- **FAIL:** harde requirement of gemeten grens wordt niet gehaald.
- **BLOCKED:** vereist externe bewijsbron of kwalificatie.
- **NOT VERIFIABLE:** claim bestaat, maar aangewezen current-branch bewijs ontbreekt.

| ID | Functiedomein | Status | Kernbewijs / resterend gat |
|---|---|---|---|
| V-001 | Eén permanente Viewer-instance | PASS | Ontwerp en shell houden één Viewer/context aan |
| V-002 | Eén globale selectiestaat | PASS | 3D, tree, grid en BOM gebruiken canonieke ID’s |
| V-003 | Canoniek Project Model | PASS | Project Model 2.25 |
| V-004 | Stabiele object/source-ID’s | PASS | 5.725 objecten volledig herleidbaar |
| V-005 | IFC exact laden | PASS | 100% fysieke HVPC-dekking |
| V-006 | STEP exact laden | PARTIAL | Implementatie aanwezig; current-HEAD packaged matrix ontbreekt |
| V-007 | NC1/PDF/projectbronnen tonen | PARTIAL | Intake/routes aanwezig; complete Vieweracceptatie per bron ontbreekt |
| V-008 | Proxyherkomst en fail-closed | PASS | Exact/proxybewijs ingebouwd |
| V-009 | Orbit/pan/zoom | PASS | Implementatie en tests aanwezig |
| V-010 | World-up en roll suppression | PASS | Contract en controller aanwezig |
| V-011 | Standaardaanzichten en fit | PASS | Viewercontrolset aanwezig |
| V-012 | Perspective/orthographic | PASS | Render/cameramodi aanwezig |
| V-013 | Pivot/focus | PARTIAL | Gebouwd; Trimble-gevoel niet objectief geaccepteerd |
| V-014 | Boxselectie | PASS | Widget/backend/controller aanwezig |
| V-015 | Crossingselectie | PASS | Widget/backend/controller aanwezig |
| V-016 | Whole-object selectie | PASS | Selectiecontract en wrong-pick nul |
| V-017 | Ctrl-multiselect | PASS | Contract en controls aanwezig |
| V-018 | Object/part/assemblyniveau | PASS | Selectieniveaus aanwezig |
| V-019 | Tree↔3D-synchronisatie | PASS | Canonieke selectiecoördinatie |
| V-020 | Grid/BOM↔3D-synchronisatie | PASS | Routes en ID-koppeling aanwezig |
| V-021 | Select all/clear | PASS | Controls en acties aanwezig |
| V-022 | Hide/show/show all | PASS | Visibility state aanwezig |
| V-023 | Isolate | PASS | Visibility state aanwezig |
| V-024 | Ghost/transparency | PASS | Weergave-instellingen aanwezig |
| V-025 | Shaded | PASS | VTK-renderpad |
| V-026 | Shaded plus edges | PASS | VTK-renderpad |
| V-027 | Wireframe | PASS | VTK-renderpad |
| V-028 | Echte hidden-line removal | FAIL | Modus wordt expliciet geweigerd |
| V-029 | IFC/source colors | PASS | Exacte kleuren en 24 rendergroepen aangetoond |
| V-030 | Grid- en asoverlay | PASS | 8 levels en 192 axes |
| V-031 | Afstandsmeting | PASS | Tool, labels en export aanwezig |
| V-032 | Hoekmeting | PASS | Tool, labels en export aanwezig |
| V-033 | Radiusmeting | PASS | Tool, labels en export aanwezig |
| V-034 | Coördinatenmeting | PASS | Tool, labels en export aanwezig |
| V-035 | Exact/verified/proxy meetbewijs | PASS | Bewijsclassificatie aanwezig |
| V-036 | Secties X/Y/Z | PASS | Section state en rendering aanwezig |
| V-037 | Section from face/flip | PASS | Tooling aanwezig |
| V-038 | Clipbox | PASS | Tooling aanwezig |
| V-039 | Explode | PASS | Tooling plus history aanwezig |
| V-040 | Undo/redo | PASS | Workbench/history aanwezig |
| V-041 | Saved views | PASS | Persistente saved-viewfunctionaliteit |
| V-042 | Groepen | PASS | Groepsfunctionaliteit aanwezig |
| V-043 | Slideshow | PASS | Presentatiepad aanwezig |
| V-044 | Markups | PASS | Reviewtooling aanwezig |
| V-045 | Issues/ToDo/comments | PASS | Reviewdata en UI aanwezig |
| V-046 | Portable .cwsreview | PASS | Ondersteund reviewpakket |
| V-047 | Schema-gecertificeerde BCF | FAIL | Bewust niet als BCF uitgegeven |
| V-048 | Revision compare | PARTIAL | Gebouwd; current-HEAD packaged schaalbewijs ontbreekt |
| V-049 | Deviation/impact | PARTIAL | Gebouwd; current-HEAD packaged schaalbewijs ontbreekt |
| V-050 | Clash broad phase | PASS | Model-controlarchitectuur aanwezig |
| V-051 | Exact selected-pair clash | PARTIAL | Aanwezig; representatieve release-evidence ontbreekt |
| V-052 | Properties/search/filter | PASS | Controls en virtuele dataweergave aanwezig |
| V-053 | Vijf hoofdwerkruimtes | PASS | Project, Viewer, Productie, Controle, Uitvoer |
| V-054 | Persistente Viewer bij workspacewissel | PARTIAL | Ontwerp aanwezig; restart/current-packagebewijs vereist |
| V-055 | 226 UI-controls uitvoerbaar | PASS | 226/226 runtime-actionresultaten PASS |
| V-056 | 31 schermoppervlakken | PASS | Screen coverage PASS |
| V-057 | DPI 100/125/150/200 | PASS | Geen geclipte kerncontrols in gecapteerde run |
| V-058 | Modeldominante Viewer-layout | FAIL | Runtime is te dicht en te veel paneel/gridgedreven |
| V-059 | Volledige native Qt+VTK screenshot | FAIL | Native QVTK-child ontbreekt in Qt-screenshot |
| V-060 | Referentie-visuele acceptatie | FAIL | Alle diffs HUMAN_REVIEW_REQUIRED |
| V-061 | Objectcompleetheid HVPC | PASS | 5.725/5.725, geen missers of duplicaten |
| V-062 | Warm cache open | PASS | 0,075 s mesh-cache warm |
| V-063 | Same-session open | PASS | 0,0207 s |
| V-064 | Eerste usable exact frame | PARTIAL | 3,264 s; dichtbij maar niet als eindgrens gesloten |
| V-065 | Cold exact ≤5 s | FAIL | 7,939 s |
| V-066 | Interactie ≥30 FPS | FAIL | 20,392 FPS |
| V-067 | Frame-p95 ≤33 ms | FAIL | 50,661 ms |
| V-068 | Input-to-render-p95 ≤35 ms | FAIL | 269,676 ms |
| V-069 | Pick-p95 ≤150 ms | PASS | 116,308 ms |
| V-070 | Wrong picks = 0 | PASS | Nul verkeerde picks |
| V-071 | Geen freezes >100 ms | FAIL | Eén freeze gemeten |
| V-072 | RSS-drift <10% | FAIL | 11,519% in representatieve run |
| V-073 | Reproduceerbare 10-minuten-soak | NOT VERIFIABLE | Traceability noemt PASS, doelbestand ontbreekt |
| V-074 | Zelfde-machine timing vs Trimble | PASS | CWS warm duidelijk sneller in gemeten scenario |
| V-075 | Object-voor-object Trimble-pariteit | BLOCKED | Externe visuele/gedrags-evidence ontbreekt |
| V-076 | Veilige machineblokkade | PASS | machine_transfer.allowed blijft false |
| V-077 | One-folder current HEAD | FAIL | Alleen oudere SHA volledig bewezen |
| V-078 | Portable current HEAD | FAIL | Alleen oudere SHA volledig bewezen |
| V-079 | Installer/associations/uninstall current HEAD | FAIL | Alleen oudere SHA volledig bewezen |
| V-080 | Dynamische 317-requirement releasegate | FAIL | Workflow hard-codeert 51 of 51 |
| V-081 | Current-HEAD commitstatus/PR-proof | FAIL | Geen complete status- of releasebinding |
| V-082 | Default branch als autoriteit | FAIL | main is een verouderde placeholder |
| V-083 | Eenduidige versie-identiteit | FAIL | Product-, Viewer- en previewversies lopen uiteen |
| V-084 | Onafhankelijke lichte contracttests | PARTIAL | Eager CadQuery/VTK-imports blokkeren lichte omgeving |
| V-085 | Multi-hardware Vieweracceptatie | FAIL | Geen complete GPU/resolutiematrix op current HEAD |
| V-086 | Accessibility/keyboarddiepte | PARTIAL | Test-ID’s bestaan; volledige a11y/keyboardbewijsset niet aangetoond |

---

## 6. Performanceanalyse

### 6.1 Exacte HVPC-load

| Metriek | Gemeten | Doel | Status |
|---|---:|---:|---|
| Fysieke objecten | 5.725 | 5.725 | PASS |
| Ontbrekende objecten | 0 | 0 | PASS |
| Dubbele objecten | 0 | 0 | PASS |
| Eerste persistent-session exact | 7,939 s | ≤5,0 s | FAIL |
| Herhaalde persistent-session exact | 5,380 s | ≤5,0 s | FAIL |
| Mesh-cache warm | 0,075 s | ≤5,0 s | PASS |
| Same-session | 0,0207 s | ≤5,0 s | PASS |
| Eerste exact interactive frame | 3,264 s | voorkeur ≤3,0 s | PARTIAL |
| Volledige exacte achtergrondload | 32,142 s | niet blokkerend vereist | PARTIAL |

De architectuur bewijst dat cache en warmstart uitstekend kunnen presteren. Het resterende gat zit in de eerste exact-load en de manier waarop exacte geometrie tijdens interactie wordt opgebouwd en geüpload.

### 6.2 Werkelijke interactie

| Metriek | Gemeten | Doel | Status |
|---|---:|---:|---|
| Gemiddelde FPS | 20,392 | ≥30 | FAIL |
| Frame p95 | 50,661 ms | ≤33 ms | FAIL |
| Eerste-frame p95 | 28,846 ms | ≤33 ms | PASS |
| Input-to-render p95 | 269,676 ms | ≤35 ms | FAIL |
| Input-to-render p99 | 783,575 ms | ≤50 ms | FAIL |
| Pick p95 | 116,308 ms | ≤150 ms | PASS |
| Selection p95 | 100,873 ms | ≤150 ms | PASS |
| Wrong picks | 0 | 0 | PASS |
| Freezes >100 ms | 1 | 0 | FAIL |
| RSS-drift | 11,519% | <10% | FAIL |

De doorslaggevende productbeleving wordt bepaald door input-to-render en frame-p95, niet alleen door het eerste plaatje. Op die twee punten faalt de huidige representatieve Viewer.

### 6.3 Waarom eerdere microtuning het gat niet sloot

De geaccepteerde runtime gebruikt een exact consolidated shaded actor, 2x MSAA en geen FXAA. Snellere LOD-experimenten werden terecht afgewezen omdat ze:

- een eerste-interactiestop van circa 32,12 seconden veroorzaakten;
- bronkleuren of objectidentiteit verloren;
- of nog steeds onder 30 FPS bleven met een lange stall.

De vereiste oplossing is dus geen “kwaliteit uitzetten”, maar een LOD- en uploadpad dat tegelijk behoudt:

- stabiele selectie-ID’s;
- object- en bronkleuren;
- correcte whole-object highlighting;
- sectie- en meetnauwkeurigheid;
- progressieve exactheid;
- geen merkbare stall.

### 6.4 Synthetische test versus echt project

De 1.000-node synthetische fixture presteert goed:

- frame-p95 1,94 ms;
- input-p95 16,88 ms;
- pick-p95 24,82 ms;
- RSS-drift 1,57%.

Dit bewijst dat de event- en controllerlaag op beperkte schaal snel kan zijn. Het bewijst niet dat de echte HVPC-renderpipeline voldoende snel is. De echte dataset moet daarom de primaire releasegate blijven.

---

## 7. Visuele en ergonomische analyse

### 7.1 Wat de UI-evidence wel bewijst

- 226 vereiste controls zijn aanwezig.
- Geen ontbrekende controls.
- Geen dubbele test-ID’s.
- Geen verkeerde labels.
- Geen screen failures.
- Geen DPI-failures op 100%, 125%, 150% en 200%.
- 31 surfaces zijn gecapteerd; 25 zijn aan een referentie gekoppeld.

### 7.2 Wat de UI-evidence niet bewijst

Alle visuele vergelijkingen staan nog op HUMAN_REVIEW_REQUIRED. Voor de vijf Viewerreferenties ligt de normalized pixel MAE tussen 0,509 en 0,688, gemiddeld circa 0,643. Die waarde is geen formele acceptatiemetriek, maar bevestigt wel een grote visuele afwijking.

De zichtbare verschillen:

- referenties zijn donkerder, rustiger en modeldominant;
- runtimecaptures zijn licht, dicht en paneel-/gridgedreven;
- meerdere informatielagen concurreren tegelijk om aandacht;
- centrale 3D-ruimte is te klein of ontbreekt in de samengestelde capture;
- de native QVTK-child wordt niet meegecaptured in het Qt-windowbeeld;
- de losse native rendercapture toont geometrische volledigheid, maar nog niet hetzelfde realistische, rustige Trimble-gevoel.

### 7.3 UX-gap

De Viewer heeft veel functies, maar presenteert ze nog te gelijktijdig. Dat veroorzaakt:

- visuele drukte;
- minder modeloppervlak;
- hogere cognitieve belasting;
- moeilijker onderscheid tussen primaire en secundaire acties;
- het gevoel van een technisch cockpitdashboard in plaats van een directe modelviewer.

De closure-build moet daarom:

1. het model standaard dominant maken;
2. secundaire grids en inspectors inklapbaar of contextueel tonen;
3. selectie, properties en issuecontext in één rustige rechterkolom consolideren;
4. Viewerstatus compact in plaats van als meerdere concurrerende panelen tonen;
5. zowel een native rendererbeeld als een volledige Qt+VTK-windowcapture leveren;
6. elke referentie door menselijke visuele review laten tekenen.

---

## 8. Bewijs- en governanceconflicten

### 8.1 Traceability versus actuele controltests

De mastertraceability van 1 september vermeldt:

- 317 actieve requirements;
- 291 PASS;
- 26 FAIL.

De 26 FAIL-items zitten in de packaged/releasefase, waaronder hoofdnav en globale controls. Een nieuwere runtime-controlcapture meldt echter 226/226 controls PASS. Dit betekent waarschijnlijk dat de implementatie verder is dan de traceability, maar ook dat de formele matrix niet opnieuw is gegenereerd en gebonden.

**Gap:** één generator moet de current-HEAD evidence verwerken en elke requirement deterministisch herberekenen.

### 8.2 Workflow 51 versus traceability 317

De releaseworkflow gebruikt nog de stapnaam “Full Product Acceptance 51 of 51”. Daarmee kan een groene pipeline ontstaan die niet de actuele 317 requirements controleert.

**Risico:** false green release.

**Vereiste:** de workflow moet de actieve traceabilitybron lezen, het verwachte aantal dynamisch bepalen en alleen slagen als alle toepasselijke requirements een geldige current-HEAD bewijsbinding hebben.

### 8.3 Oud releasebewijs versus huidige HEAD

De laatste finale phase-4-gate is gebonden aan commit 1513ae3ad91f…, terwijl de geaudite HEAD a2cd946d… is. Daartussen liggen elf commits, inclusief MGI V3 en volledige converterroutes.

**Gevolg:** oudere packaging-PASS-resultaten mogen niet als bewijs voor de huidige build worden gebruikt.

### 8.4 Autoriteitsdocumentatie

- CURRENT_PRODUCT_AUTHORITY staat nog op current_authority_in_progress.
- Branch, HEAD, parent en worktree zijn daar NOT_TESTED.
- CODEX_HANDOVER_STATUS verwijst naar oudere productnamen, schema’s en branches.
- main is nog een verouderde placeholder.
- oudere draft-PR’s staan open en kunnen voor verwarring zorgen.

**Vereiste:** één actuele autoriteitsfile, één releasebranch, één PR en één exact commit-ID.

### 8.5 Soakbewijs

F1-009 staat als PASS in traceability en wijst naar een 10-minuten OpenGL-soakbestand, maar dat bestand is niet aanwezig in de huidige branchsnapshot.

**Oordeel:** niet als current-HEAD bewijs bruikbaar.

### 8.6 Versie-identiteit

De applicatie noemt 0.10.18-beta-dev, het Viewer-package 1.0.0-dev0 en het previewcontract 1.4.0-v15-preview.2.

**Risico:** onduidelijk welke Viewer-runtime, state-API en evidence exact bij een release horen.

---

## 9. Geprioriteerd gapregister

| Gap | Prio | Probleem | Vereiste sluiting |
|---|---|---|---|
| GAP-V-001 | P0 | Geen volledige release-evidence op a2cd946 | Alle gates opnieuw draaien en aan exact SHA binden |
| GAP-V-002 | P0 | HVPC-interactie 20,39 FPS en frame-p95 50,66 ms | ≥30 FPS en frame-p95 ≤33 ms zonder functieverlies |
| GAP-V-003 | P0 | Input-to-render-p95 269,68 ms | p95 ≤35 ms, p99 ≤50 ms |
| GAP-V-004 | P0 | Cold exact load 7,939 s | ≤5,0 s; first usable bij voorkeur ≤3,0 s |
| GAP-V-005 | P0 | Eén freeze >100 ms | Nul freezes in representatieve 10-minuten-soak |
| GAP-V-006 | P0 | RSS-drift 11,52% | <10% en stabiele actor-/worker-counts |
| GAP-V-007 | P0 | Viewer visueel niet geaccepteerd | 25/25 gekoppelde surfaces HUMAN PASS |
| GAP-V-008 | P0 | Qt-capture mist native QVTK-child | Volledige samengestelde windowcapture plus native rendererbewijs |
| GAP-V-009 | P0 | CI controleert 51 in plaats van 317 | Dynamische 317-requirement gate |
| GAP-V-010 | P0 | Current-HEAD one-folder/portable/installer niet bewezen | Schone Windows-VM matrix volledig PASS |
| GAP-V-011 | P0 | Trimble visuele/gedragspariteit geblokkeerd | Zelfde model, camera, viewport en acties object-voor-object vergelijken |
| GAP-V-012 | P1 | Echte hidden-line ontbreekt | Correct depth-aware hidden-line pad plus regressietests |
| GAP-V-013 | P1 | BCF niet schema-gecertificeerd | Certificeer BCF 2.x of verklaar formeel buiten scope |
| GAP-V-014 | P1 | Te dichte Viewer-layout | Modeldominante, contextuele UI met menselijke UX-PASS |
| GAP-V-015 | P1 | 10-minuten-soakbewijs ontbreekt | Evidencebestand opnieuw genereren en committen |
| GAP-V-016 | P1 | Autoriteits- en versiedrift | Eén versiebron en gegenereerde authority/handoverdocs |
| GAP-V-017 | P1 | Default main is niet canoniek | Current authority via beoordeelde PR naar releasebranch/main |
| GAP-V-018 | P1 | Eager CadQuery/VTK-importkoppeling | Lichte contracts/modules zonder native runtime importeerbaar |
| GAP-V-019 | P1 | Multi-hardwarebewijs ontbreekt | Minimaal iGPU, middenklasse dGPU, 1080p en 4K |
| GAP-V-020 | P1 | A11y/keyboardbewijs onvolledig | Volledige focus-, shortcut-, contrast- en screenreadercheck |
| GAP-V-021 | P2 | Compatibilitylagen en dubbele constanten | Reduceren en migraties expliciet testen |
| GAP-V-022 | P2 | Revision/clash schaalbewijs onvolledig | HVPC en tweede groot regressiemodel packaged testen |

---

## 10. Aanbevolen closure in één build

De scope kan in één gecontroleerde build worden gesloten, zolang het werk intern in harde gates wordt uitgevoerd.

### Gate A — autoriteit en baseline

- Freeze a2cd946 of een expliciete opvolger als enige authority.
- Maak één release-PR.
- Sluit of label verouderde draft-PR’s.
- Harmoniseer product-, Viewer-, schema- en previewversies.
- Genereer authority- en handoverdocumenten vanaf dezelfde manifestbron.

### Gate B — render- en inputperformance

- Profileer de echte HVPC-load, niet alleen de 1.000-node fixture.
- Maak sceneupload tijdgebudgetteerd en interaction-aware.
- Coalesce mousemove/wheel events zonder eindpositie te verliezen.
- Gebruik een identity-preserving gesloten-surface LOD.
- Behoud bronkleur, object-ID, selectie, secties en meetnauwkeurigheid.
- Verwijder de first-interaction stall.
- Reduceer cold exact tot maximaal 5 seconden.
- Behaal ≥30 FPS en frame-p95 ≤33 ms.
- Behaal input-to-render-p95 ≤35 ms.

### Gate C — Viewer-UX en ontbrekende eindfuncties

- Maak het model standaard dominant.
- Consolideer panels en verplaats secundaire tabellen naar context/drawer.
- Lever echte hidden-line removal als dit onderdeel van de definitieve productscope is.
- Certificeer BCF of verklaar het expliciet buiten de release.
- Rond keyboard- en accessibilitygedrag af.
- Maak een capturepad dat Qt-chrome en native VTK samen vastlegt.

### Gate D — representatieve functionele regressie

Test op de echte HVPC-dataset:

- navigatie;
- whole-object, multiselect, box en crossing;
- tree/grid/BOM-sync;
- hide/isolate/ghost;
- alle meettypen;
- secties, clipbox en explode;
- saved views, groepen en slideshow;
- review en markups;
- revision compare;
- model control;
- screenshots en exports;
- workspacewissel plus herstart;
- veilige machineblokkade.

### Gate E — finale releasebewijsset

- Genereer de 317-requirement matrix dynamisch.
- Draai een echte 10-minuten OpenGL-soak.
- Test minimaal twee GPU-klassen en twee resoluties.
- Voer de zelfde-machine Trimblevergelijking uit.
- Laat alle referenties menselijk beoordelen.
- Bouw one-folder, portable en installer vanaf dezelfde exact HEAD.
- Test file associations, upgrade, uninstall en schone VM.
- Schrijf SHA256SUMS en release manifest.
- Sta release alleen toe als elke toepasselijke gate PASS is.

---

## 11. Harde Definition of Done

De Viewer is pas “100% gereed” als aan alle onderstaande punten is voldaan:

### Functionaliteit

- Alle matrixitems V-001 tot en met V-086 zijn PASS of formeel, vooraf goedgekeurd OUT_OF_SCOPE.
- Hidden-line en BCF zijn ofwel geleverd, of expliciet uit de productscope gehaald.
- Geen stub-, placeholder- of silent-fallbackgedrag in kritieke Viewerflows.

### Correctheid

- HVPC: 5.725/5.725 fysieke objecten zichtbaar en selecteerbaar.
- Missing, duplicate, empty en box fallback: nul.
- Wrong picks: nul.
- Tree, grid, BOM en 3D blijven synchroon na edits, reload en workspacewissel.
- Exact/proxy-status is altijd zichtbaar en exporteerbaar.

### Performance

- Cold exact open ≤5,0 s.
- First usable bij voorkeur ≤3,0 s.
- Warm cache ≤1,0 s.
- Same-session ≤0,5 s.
- Gemiddeld ≥30 FPS op de afgesproken referentiemachine.
- Frame-p95 ≤33 ms.
- Input-to-render-p95 ≤35 ms en p99 ≤50 ms.
- Pick-p95 ≤150 ms op het grote model.
- Freezes >100 ms: nul.
- RSS-drift na 10 minuten <10%.
- Actor-, worker- en procescounts blijven begrensd.

### UX en visueel

- 31/31 surfaces aanwezig.
- 226/226 controls uitvoerbaar.
- 25/25 referentieparen menselijk PASS.
- Volledige Qt+VTK-capture toont exact wat de gebruiker ziet.
- DPI 100/125/150/200 PASS.
- Licht en donker thema zonder contrast- of clippingfouten.
- Model blijft het primaire visuele object.

### Release

- Alle 317 actieve requirements automatisch geëvalueerd.
- Geen hard-coded oud requirementaantal.
- Evidence, executables en manifest verwijzen naar dezelfde commit.
- One-folder, portable, installer, associations, upgrade en uninstall PASS.
- Geen ongekwalificeerde fysieke machineactie.
- Geen open P0 of P1.

---

## 12. Bewijsbronnen in de repository

De belangrijkste geaudite bronnen:

- requirements/MASTER_REQUIREMENT_TRACEABILITY.md
- requirements/MASTER_REQUIREMENT_TRACEABILITY.json
- validation/master_completion/HVPC_LOAD_CLOSEOUT.json
- validation/master_completion/QT_PROGRESSIVE_EXACT_WARMSTART_PASS.json
- validation/master_completion/HVPC_RENDER_MICROTUNING_CLOSEOUT.json
- validation/master_completion/HVPC_TRIMBLE_VISUAL_COMPARISON.md
- validation/master_completion/TRIMBLE_SAME_MACHINE_COMPARISON.md
- validation/master_completion/ui_v52_hvpc_surface_capture_final/control_action_results.json
- validation/master_completion/ui_v52_hvpc_surface_capture_final/UI_BINDING_ACCEPTANCE.md
- validation/master_completion/ui_v52_hvpc_surface_capture_final/UI_VISUAL_DIFF_REPORT.md
- validation/master_completion/FINAL_PHASE4_GATE.json
- .github/workflows/final-release-proof.yml
- docs/CURRENT_PRODUCT_AUTHORITY.md
- docs/CODEX_HANDOVER_STATUS.md
- cws_convertor/product.py
- cws_viewer/version.py
- cws_viewer/core/controller.py
- cws_viewer/review/bcf.py

---

## 13. Eindadvies

De CWS Viewer hoeft niet opnieuw te worden ontworpen. De functionele kern is sterk en de objectcompleetheid is overtuigend. De resterende 8% functionele bronlacune zit vooral in hidden-line, BCF-certificering, enkele current-packagebewijzen en diepere niet-functionele aspecten.

Het werkelijke releasegat is groter dan 8%, omdat performance, visuele rust, bewijsbinding en packaging binaire gates zijn. Een Viewer die 92% van de functies heeft maar input pas na 270 ms toont, visueel niet is goedgekeurd en geen current-HEAD installerbewijs heeft, is nog niet 100% gereed.

**Besluit:** voer één closure-build uit, bevries de authority, sluit de P0’s in volgorde performance → UX → dynamic acceptance → exact-HEAD packaging, en geef pas daarna het label Viewer 100%.

---

## Bijlage A — verificatiebeperkingen van deze analyse

- Broncompilatie van cws_viewer en cws_convertor is op de geaudite HEAD geslaagd.
- Een lokale brede unittest-discovery kon niet representatief afronden doordat de analyseomgeving geen CadQuery- en VTK-runtime bevatte. Dit is geen bewijs van productregressie.
- Die blokkade onderstreept wel dat contracttests te vroeg aan native CAD/renderimports gekoppeld zijn.
- Voor Windows-, GPU- en installeracceptatie is de gecommitteerde packaged evidence leidend.
- Waar evidence aan een oudere commit is gebonden, is die als historisch bewijs behandeld en niet als current-HEAD PASS.

## Bijlage B — audituitspraak in één zin

> **CWS Convertor Viewer is inhoudelijk bijna compleet, maar release 100% blijft FAIL totdat echte HVPC-interactie, visuele pariteit, dynamische 317-requirementacceptatie en exact-HEAD Windows-packaging aantoonbaar PASS zijn.**
