# CWS Viewer V14 — UX- en functiegaponderzoek

## Doel en grens

Dit document vertaalt de door de fysieke Windows-test zichtbaar geworden tekortkomingen naar een concrete CWS Viewer V14-oplossing. Trimble Connect is uitsluitend gebruikt als **functionele en interactionele benchmark** op basis van reeds aangeleverde bestandsmetadata/XML-documentatie en publiek beschreven gebruikersgedrag. Er worden geen Trimble-binaries, gedecompileerde method bodies, iconen, BAML-resources of andere proprietary assets in CWS opgenomen.

De CWS-architectuur blijft leidend:

`Canonical Project Model → ProjectScene → Viewer controller → VTK display renderer / OCCT exact renderer → Qt cockpit`

Displaymeshes blijven review-/weergavegeometrie en worden nooit manufacturing truth.

## Fysieke rc3-bevindingen

De Windows rc3-test bewees dat direct IFC-openen en de frozen IFC-worker nu functioneren, maar legde zes UX-problemen bloot:

1. de gebruiker kwam terecht in de oude donkere ontwikkelaarsshell;
2. klikselectie en VTK-draginteractie vochten om hetzelfde linkermuisevent;
3. de bediening was daardoor niet voorspelbaar als engineering viewer;
4. IFC-stamienen werden door de semantische/viewerketen niet getoond;
5. de meetengine bestond, maar was niet duidelijk zichtbaar/bedienbaar in de primaire viewer;
6. functies als Model Control, exacte part review, lagen en herkomst waren technisch aanwezig maar slecht vindbaar.

### Root cause lichte UI

De rc3-launcher probeerde `cws_viewer.ui_qt.cockpit` te importeren en viel bij importfailure terug op de oude `project_viewer`-shell. De bedoelde lichte cockpit uit het eerdere integratiepakket stond niet daadwerkelijk in de GitHub-bron waarvan rc3 werd gebouwd. V14 levert daarom de cockpit als echte bronmodule én certificeert de import in source en frozen self-tests.

### Root cause navigatie

De oude `VtkRealProjectWidget.mousePressEvent` voerde bij linkermuisknop eerst een CWS-pick uit en stuurde daarna hetzelfde event door naar `QVTKRenderWindowInteractor`. Selectie en navigatie waren dus niet als exclusieve gebaren gemodelleerd. V14 scheidt click, drag, context click en rectangle selection expliciet.

## Trimble-benchmark die functioneel is overgenomen

De onderzochte Trimble-bestanden/API-signalen tonen concepten voor camera/navigatie, selectie, hide/isolate, opacity, kleuren, properties, hierarchy, section planes, snapshots, measurement markups en workspace-state. V14 implementeert dezelfde **categorieën van gebruikersgedrag** met eigen CWS-contracten.

Belangrijkste bedieningsdoelen:

- linkersleep roteert in Rotate-modus;
- middelste muisknop pant;
- scrollwiel zoomt;
- klik selecteert zonder meteen te orbitten;
- Ctrl voegt aan selectie toe, Shift toggelt;
- vensterselectie ondersteunt contained/crossing-richting;
- Rotate/Pan/Walk/Look zijn expliciete modi;
- Space = fit selectie, F = fit model, F11 = volledig scherm, Esc = huidige tool beëindigen;
- standaardaanzichten zijn direct beschikbaar;
- meten blijft actief totdat gebruiker stopt;
- hide/isolate/ghost/show all staan in hoofdtoolbar en contextmenu;
- grids/stamienen zijn een afzonderlijke viewerlaag met niveaukeuze;
- viewpoints/workspace-state moeten camera, visibility, sections en measurements reproduceerbaar bewaren.

## Kleuren en thema

V14 maakt **licht** de standaard voor het hele programma. Het thema is niet een gekopieerde Trimble-resource. Het is een originele CWS engineering theme registry met:

- witte panelen;
- zeer lichtgrijze application background;
- donkere neutrale tekst;
- subtiele borders;
- CWS-blauw voor actieve tools/selectie;
- statuskleuren voor OK/warning/fail;
- drie applicatiethema's: `Engineering licht`, `CWS licht`, `CWS donker`.

De keuze wordt via `QSettings` op applicatieniveau opgeslagen en kan later worden uitgebreid met bedrijfsthema's/accentkleur/configurabele viewer-backgrounds.

## Stamienen / IFC grids

### Probleem

`IFCGRID` en `IFCGRIDAXIS` waren geen productiedelen en verdwenen daardoor uit de normale semantic product materialisation. Voor een projectviewer is dat onjuist: gridlijnen zijn essentiële review-/oriëntatiecontext.

### V14-oplossing

Nieuwe `cws_convertor.importers.ifc_grid`:

- leest `IFCGRID` en `IFCGRIDAXIS` rechtstreeks uit hetzelfde Part 21-document;
- verwerkt `IFCLOCALPLACEMENT` recursief;
- respecteert IFC length units en converteert naar mm;
- bewaart bron-entity-ID, gridnaam, U/V/W-familie en axis tag;
- rendert gridlijnen als niet-pickable VTK overlay;
- labelt assen in de viewer;
- ondersteunt Auto, specifiek gridniveau of alle niveaus;
- maakt grids nooit onderdeel van manufacturing geometry.

Op het bekende defensie-IFC-model zijn zes gridniveaus en negentig assen aangetroffen; dit is precies het soort broninformatie dat in rc3 niet zichtbaar werd.

## Meten

V14 maakt meten een primaire toolbarfunctie en gebruikt de werkelijk gepickte mesh-surfacepositie. Beschikbaar in de hoofdviewer:

- puntcoördinaten;
- afstand;
- horizontale afstand;
- verticale afstand;
- driepunts-hoek.

Meetrecords blijven onderdeel van de bestaande deterministic measurement contracts en krijgen een zichtbare VTK overlay met anchors, lijn en maattekst. De bestaande Viewer Tools-workspace blijft beschikbaar voor sections/clipping en verdere meetworkflow.

Exacte radius/diameter/face/edge-analyses blijven via de OCCT Exact Part Workbench lopen wanneer source-BREP exact beschikbaar is. Displayproxy-resultaten mogen niet als productie-exact worden gepresenteerd.

## Selectie en picking

V14 voegt een surface-oriented `vtkCellPicker`-pad toe vóór de oude center-proxy fallback. Omdat identieke meshes als instances kunnen worden gerenderd, wordt het actor-hitpunt teruggekoppeld naar de dichtstbijzijnde stabiele CWS-node/world-bounds. Hierdoor blijft selectie gekoppeld aan Canonical entity IDs in plaats van een los VTK-objectnummer.

Vensterselectie projecteert world bounds naar schermcoördinaten en ondersteunt:

- links→rechts: object volledig binnen venster;
- rechts→links: object kruist venster;
- selectie op het bestaande selection level;
- Ctrl/Shift selection operations.

## Model Control

V14 brengt Model Control in de hoofdcockpit:

1. projectbrede broad phase voor candidate reduction;
2. intended-contact filtering via weld/fastener-relaties;
3. geselecteerde kandidaat kan on-demand exact worden gecontroleerd met OCCT source-BREP;
4. exacte narrow phase bepaalt intersection volume en minimum distance;
5. wanneer bronisolatie niet exact/veilig is, blijft het resultaat approximate/review en wordt niets verzonnen;
6. reviewstate kan bij rescan worden gereconcilieerd als NEW/UNCHANGED/CHANGED/RESOLVED.

## Review en samenwerking

Nieuwe niet-destructieve CWS reviewlaag bevat:

- text/arrow/cloud/freehand markup-contracten;
- review issues;
- assignee/status/comments/audit;
- clash references;
- screenshot/attachment references;
- checksum-protected sidecar store;
- portable `.cwsreview` ZIP met manifest en SHA-256;
- BCF topic mapping als expliciete extension point.

Er wordt bewust nog geen bestand als BCF geëxporteerd zolang geen concrete buildingSMART BCF-versie tegen het officiële schema is gecertificeerd.

## Functiematrix V14

| Gebied | rc3 fysieke toestand | V14 |
|---|---|---|
| Programma/start/model-open | werkend | rc3 workertransport behouden |
| Whole-app thema | donker fallbackscherm | licht standaard + theme registry |
| Orbit/pan/zoom | conflicterend | expliciete gebaren/modi |
| Walk/look | niet vindbaar | toolbar + shortcuts + WASD/QE |
| Fit/standard views | aanwezig maar compact | primaire toolbar |
| Single/multi select | aanwezig, drag conflict | click/drag gescheiden |
| Window selection | niet zichtbaar | contained/crossing rubber-band |
| Tree ↔ 3D ↔ grid sync | gedeeltelijk | expliciete stable-ID bus |
| Surface picking | fallback/actor ambigu | cell picker + stable-node resolution |
| Hide/isolate/ghost | aanwezig | primaire toolbar + contextmenu |
| Kleurschema's | aanwezig in developer UI | hoofdmenu + whole-app theme apart |
| Stamienen | ontbrekend | IFCGRID/IFCGRIDAXIS overlay |
| Meten | engine aanwezig, UX verborgen | hoofdtoolbar + live overlay |
| Section/clipping | technisch aanwezig | Viewer Tools direct tab/toolbar |
| Lagen | technisch aanwezig | aparte cockpit-tab |
| Model Control | niet vindbaar | cockpit-tab + on-demand exact OCCT |
| Exact part review | technisch aanwezig | contextmenu / parts grid |
| Properties/provenance | aanwezig | permanent rechterpaneel |
| Workspace/review package | deels | checksum-protected portable review core |
| Point clouds/panorama | niet core | bewust deferred plugin/roadmap |
| Cloud collaboration | niet core | bewust local-first/deferred |

## Definitie van gereed voor V14 RC

V14 RC mag pas worden aangeboden voor fysieke test wanneer:

- source `compileall` groen is;
- V14 contract self-test de cockpit, theme registry, gridparser, V14 surface backend/controller en reviewpackage importeert/test;
- rc3 native IFC-worker selftest groen blijft;
- PyInstaller frozen V14 contract groen is;
- frozen IFC-worker expliciet `frozen_subprocess` blijft;
- portable build zonder externe Python groen is;
- installed build zonder externe Python groen is;
- startup/project headless gates groen blijven;
- installer + uninstaller groen zijn;
- fysieke Windows/GPU-test daarna expliciet bediening, gridweergave, meten en weergavekwaliteit accepteert.

## Nog fysieke acceptatie nodig

Hosted Windows CI kan modulecontracten, workertransport en offscreen/headless projectstate bewijzen, maar is geen vervanging voor de echte GPU/VTK desktopinteractie. De fysieke test moet daarom minimaal controleren:

- model opent en blijft zichtbaar;
- licht theme over de hele cockpit;
- linkersleep rotate zonder onbedoelde selectie;
- clickselectie zonder camerabeweging;
- middle pan en wheel zoom;
- rectangle selection;
- gridlijnen en labels op relevante niveaus;
- afstand/hoek/coördinaten met zichtbare maatmarkup;
- hide/isolate/ghost/show all;
- standard views/projection/display modes;
- selectie synchronisatie tussen tree, 3D en parts grid;
- properties/provenance;
- Model Control broad phase en een exact geselecteerd paar;
- geen regressie van rc3 frozen IFC-worker.
