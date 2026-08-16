# CWS Viewer / Convertor V15 — T0 Baseline Audit & Gap Matrix

Auditdatum: 2026-08-16  
Status: **T0 BASELINE LOCKED — featurewerk mag hierna starten**  
Actieve branch: `feature/trimble-parity-v15`

## 1. Exacte Git-basis

| Onderdeel | Waarde |
|---|---|
| V15 branch | `feature/trimble-parity-v15` |
| V15 startbasis | `delivery/cws-viewer-v14-rc1` |
| Startbasis commit | `06ce7a31cfc2e1e5619f1e35cdc423131ad26900` |
| Plan-lock commit | `501a72bf72a3ee6a1749bad95137d8a846597d21` |
| V14 succesvolle Windows Actions evidence-run | `31894173867` |
| Evidence-run source commit | `b0faab258a95376236153914827f494266601862` |
| Default branch `main` bij audit | `a2872b2f1ff8798bd8e395eddb5ce71e4e98c61f` |

### Belangrijk repositoryfeit

De huidige `main`-historie en de volledige Python Viewer/Convertor-historie hebben geen gemeenschappelijke ancestor in GitHub Compare. Daarom wordt V15 **niet blind over `main` heen geschreven**. De nieuwe V15-paritybranch is bewust gestart vanaf de bewezen V14 Windows-deliverylijn. Integratie naar `main` is een aparte, expliciete release-/migratiestap nadat de parity- en regressiegates groen zijn.

## 2. Bestaande Windows delivery baseline

De V14 Windows pipeline heeft reeds echte artifacts geproduceerd in GitHub Actions:

- `CWS_Viewer_1.3.0-rc1_x64`
- `CWS_Viewer_1.3.0-rc1_INSTALLER_x64`
- `CWS_Viewer_1.3.0-rc1_EVIDENCE`

Uit de bestaande evidence:

- `CWS_Viewer.exe` SHA-256: `24a24aac18d8cebfcd1ae2f1ad4eb4092d754152ae3e55cddff2df96eb3c784c`
- opnieuw opgehaald installer-artifact ZIP SHA-256: `2aada68d1bc2f197d6bd06e94b86c066da17edeb72b8b84f34efcbea9aad6afc`

Deze EXE is **baselinebewijs**, niet de finale V15-parity-EXE. V15 krijgt een nieuwe source-commit binding en nieuwe Windows evidence.

## 3. Aangeleverde referenties — checksum lock

| Bestand | SHA-256 |
|---|---|
| `Trimble Connect.zip` | `6298196885a51784f557e0f9e6cf18d1f60bc68c35b4c03913f3771e1923455e` |
| `CWS_Viewer_V14_COMPLETION_HANDOVER.zip` | `2c81186879ba7432c1d21a437e80286ab99b3ff920c4214c17bdbd2dd9714b51` |
| `CWS_CONVERTOR_MASTER_HANDOVER_V15.zip` | `ddde36f0642391b760291c8b4b4e055640356219173a37daca7085e57973ae68` |
| `CWS_MANUFACTURING_FACES_SCRIBING_MARKING_MULTICONVERTER_MEGA_SUPERPROMPT.md` | `4ea11eb1ba2eb0855e22c5c7795ae8e71783a3a03685892cb5168d3581dc8d66` |
| `CWS_MANUFACTURING_FACES_SCRIBING_REFERENCE_AUDIT.md` | `f901f1f166f23d432030bcddb4117b3d6582f3537bc1f49f9a4d360334be46e8` |

## 4. Forensic functionele inventaris van de meegeleverde Trimble Connect package

De package bevat 442 entries, waaronder 8 executables en 253 DLL's. Zichtbare productcomponenten bevestigen onder meer:

- `TrimbleConnect.exe` met package/version strings rond `1.30.0.769`;
- desktop shell/componentnamen zoals `VerticalToolbar`, `UserPanel`, `WorkspaceSelector`, import-/exportjob popups en notifications;
- aparte geometry-/IFC-gerelateerde componenten;
- .NET Framework 4.8 runtimeconfiguratie;
- verbinding naar `connect.trimble.com` in configuratie.

Deze inventaris wordt **niet** gebruikt om private implementatielogica te kopiëren. De package is uitsluitend een gedrag-/workflowreferentie en een local acceptance oracle voor zichtbare gebruikersfuncties.

## 5. Proprietary reference boundary

Voor V15 geldt:

1. Geen Trimble/ConstruSteel/Tekla broncode decompileren of overnemen.
2. Geen Trimble merkassets/iconen/credentials/private endpoints in CWS opnemen.
3. Alleen zichtbare workflowconcepten/functioneel gedrag namaken met eigen CWS-contracten en eigen UI.
4. Geen native Trimble cloudcompatibiliteit claimen zonder officiële API/spec en eigen tests.
5. Geen proprietary machine/controlleroutput gokken.
6. Canonical CWS manufacturing geometry blijft leidend; DSTV/machineformaten blijven adapters.

## 6. Officiële Trimble Help — functionele referentiematrix

De audit vergelijkt CWS met de officieel gedocumenteerde Trimble Connect for Windows gebruikersfuncties. Belangrijke families uit de officiële documentatie zijn:

- Project Navigation met side pane + Explorer/Map/3D Viewer-context;
- 3D Viewer navigation/view actions, predefined views en perspective/orthographic;
- selection/model tree/properties;
- hide/show/transparency/display controls;
- measurement tools;
- clipping planes;
- saved views / Views browser;
- markups en reviewcontext;
- ToDos gekoppeld aan model/object/file/view-context;
- model comparison;
- assembly navigation;
- presentations/view sequencing.

Deze lijst is een **functionele benchmark**, niet een verplichting om Trimble's productarchitectuur of cloudplatform te kopiëren.

## 7. Wat de huidige V14 code al aantoonbaar bevat

Code-inspectie van de actieve basis bevestigt in de eigen CWS cockpit minimaal:

- professionele Qt desktop shell;
- project tree links;
- centrale VTK 3D Viewer;
- properties/herkomst rechts;
- onderste tab-workspace;
- tree ↔ viewport selection synchronization;
- tree search/filter;
- visibility via tree;
- orbit/pan/walk/look;
- fit all / fit selection;
- predefined views;
- perspective/orthographic;
- shaded, shaded+edges, wireframe, hidden-line;
- IFC grid/stamien overlay;
- distance/horizontal/vertical/coordinates/angle measurements;
- hide/isolate/ghost/show-all;
- color schemes;
- theme system;
- model-control/clash UI;
- integrated measurement/section tools;
- exact part workbench linkage;
- standalone Windows packaging/self-tests/crash-isolated IFC worker.

Daarmee is V14 duidelijk verder dan de oudere V15 handover/gapdocumenten suggereren; die oudere documenten blijven requirements, maar hun historische `MISSING`-veronderstellingen mogen niet blind worden overgenomen.

## 8. V15 parity gap matrix — status na T0

Statuscodes:

- `VERIFIED_BASELINE`: code + eerdere evidence aanwezig;
- `IMPLEMENTED_UNVERIFIED_V15`: aanwezig maar moet in nieuwe V15 gate opnieuw bewezen worden;
- `PARTIAL`: kern aanwezig, parity-/UX-/testdekking onvoldoende;
- `MISSING`: nog te bouwen;
- `EXTERNAL_BOUNDARY`: bewust niet als lokale clone geclaimd.

| Domein | T0 status | V15 actie |
|---|---|---|
| Windows standalone start/installer | VERIFIED_BASELINE | nieuwe V15 build/evidence genereren |
| Eigen CWS engineering shell | VERIFIED_BASELINE | workspace persistence/docking verder hardenen |
| Project/model tree | PARTIAL | richer hierarchy, context actions, virtualization/lazy loading |
| Tree ↔ viewport selection | VERIFIED_BASELINE | regressie + large-model test |
| Search/filter | PARTIAL | property/GUID/source-wide search verdiepen |
| 3D orbit/pan/zoom/fit | VERIFIED_BASELINE | camera history/zoom-area/view-from-face aanvullen |
| Standard views + projection | VERIFIED_BASELINE | state persistence/shortcuts hardenen |
| Render modes/transparency/ghost | IMPLEMENTED_UNVERIFIED_V15 | nieuwe screenshots/regressies |
| Grid/stamien | IMPLEMENTED_UNVERIFIED_V15 | snapping/level UX/labels bewijs |
| Measurement | PARTIAL | snapping, persistent labels, export, exactness UX |
| Clipping/sections | PARTIAL | manipulators, meerdere planes, state persistence |
| Explode | PARTIAL | hiërarchische UX + persistence |
| Properties/provenance | IMPLEMENTED_UNVERIFIED_V15 | deeper property sets/search/copy |
| Saved views/viewpoints | PARTIAL | volledig canonical view contract + thumbnails/browser |
| Markups | MISSING/PARTIAL | eigen canonical markup contract + viewer UX |
| ToDos/issues | MISSING | lokale CWS review workflow; externe sync alleen via geldige API |
| Assemblies | PARTIAL | drill-down/context/selection verdieping |
| Model comparison | MISSING/PARTIAL | deterministic revision comparison + viewer overlay |
| Presentations/sequence | MISSING/PARTIAL | saved view/sequence playback |
| Clash/model control | IMPLEMENTED_UNVERIFIED_V15 | exact/spatial evidence + UX polish |
| Scope-first export center | PARTIAL | centrale scope/preflight/output matrix |
| NC1/IFC/STEP converter | PARTIAL/EXISTING OTHER MODULES | integratie + roundtrip evidence |
| Manufacturing faces/contact/marking | MISSING IN V14 VIEWER LINE | implementatie volgens M1–M4/T8 |
| Machine/nesting/operation sequence | MISSING IN V14 VIEWER LINE | implementatie volgens M5–M9/T9 |
| Native Trimble cloud/server-private behavior | EXTERNAL_BOUNDARY | niet klonen; alleen officiële/owner-approved integratie |
| Proprietary machine controller formats | EXTERNAL_BOUNDARY | alleen gevalideerde adapters |

## 9. No-regression contract

V15 mag geen bestaande bewezen CWS-functie verwijderen. Iedere fase moet minimaal opnieuw controleren:

- canonical project openen;
- IFC/STEP intake;
- 3D scene load;
- tree/selection sync;
- measurement basics;
- grid/stamien;
- model control;
- standalone self-test;
- Windows packaging;
- productie-release flags blijven veilig gesloten waar externe evidence ontbreekt.

## 10. T0 conclusie

**T0 gate is open voor featurebouw.**

De correcte ontwikkellijn is niet de losse `main`-prototypehistorie, maar de bewezen V14 Python/Windows deliverylijn. V15 bouwt daarop voort met een eigen CWS-uitstraling en een expliciete paritymatrix. De eerste implementatiefocus is T1/T2/T3: de bestaande cockpit niet herschrijven, maar de workspace, projectexplorer en view/navigation contracts tot een volledig testbare engineeringdesktop verheffen.
