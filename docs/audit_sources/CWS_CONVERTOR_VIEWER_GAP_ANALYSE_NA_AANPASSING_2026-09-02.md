# CWS Convertor Viewer — gap-analyse na aanpassing

Datum: 2026-09-02  
Repository: `CoenWessselink/Convertor`  
Branch: `agent/cws-product-ui-reintegration-v1`  
Exact gepubliceerde HEAD: `9feb78c701f9551745d204a0446746b6d88513bd`  
Pull request: [#9](https://github.com/CoenWessselink/Convertor/pull/9)

## Eindconclusie

De ontbrekende bronfunctionaliteit is aangevuld: echte hidden-line rendering, XSD-gevalideerde BCF 2.1-export, volledige Qt+VTK-capture, modeldominante Viewer-layout, één Viewer-versiebron, lichte imports en een dynamische 317-requirementreleasegate zijn geleverd.

De Viewer mag nog niet als **100% releasegereed** worden aangeduid. De actuele lokale harde cold-loadmeting is `6,450 s` bij een maximum van `5,000 s`. Daarnaast is de exacte Windows-releaseworkflow voor de nieuwe HEAD nog niet verifieerbaar en vereisen visuele/Trimble- en multi-hardwarekwalificatie externe, menselijke bewijsvoering. De releasegate blijft fail-closed wanneer een meetdrempel niet wordt gehaald.

## Geleverde aanpassingen

| Onderdeel | Resultaat |
|---|---|
| Hidden-line | Depth-writing oppervlak plus afzonderlijke `vtkFeatureEdges`-glyphactors; geen zichtbare triangulatieranden |
| BCF | Deterministische BCF 2.1-archive, officiële buildingSMART 2.1-XSD-validatie, veilige ZIP/XML-verificatie, viewpoints, comments en IFC-GlobalId-selecties |
| Performancepad | Geen dubbele render per orbitmeting; trage geconsolideerde interaction actor uitgeschakeld; interactie-MSAA 0; hard-fail drempels voor FPS, frame/input, pick, freezes, memory en foutieve picks |
| Cold load | Drie geïsoleerde workers worden tijdens applicatiestart vooraf opgewarmd; gebalanceerd tessellatieprofiel en vernieuwde cachefingerprint |
| Capture/UX | Composietcapture van Qt-chrome plus native VTK-framebuffer; centrale viewport standaard ongeveer 70% van de breedte |
| Releasebewijs | Exact-SHA HVPC-closeout toegevoegd; matrix wordt uit de actieve mastertraceability afgeleid, niet uit `51` |
| Versie/imports | Viewer `1.4.0-v15-preview.2` komt uit één bron; lichte contractimports laden CadQuery, VTK en PySide6 niet eager |
| Governance | Wijzigingen fast-forward gepubliceerd op de canonieke werkbranch en gekoppeld aan bestaande PR #9; een merge naar de default/releasebranch is nog niet uitgevoerd |

## Nieuwe meet- en testresultaten

| Bewijs | Uitkomst |
|---|---|
| Compileall | PASS |
| Fase 1 bronacceptatie | PASS |
| Fase 2 bronacceptatie | `16/16 PASS` |
| Lokale 10-minutensoak | PASS, `602,032 s` |
| BCF 2.1 schema + componentselectie | `7/7 PASS` |
| Performance-loader | `9/9 PASS` |
| Dynamische mastertraceability | `317` actieve requirements; dynamische release-simulatie `317/317 PASS` |
| Lichte imports/één versiebron | `2/2 PASS` |
| Hidden-line broncontract | PASS; native OpenGL-test alleen op gekwalificeerde runner |
| HVPC exacte objecten | `1.496/1.496` geometry resources, nul workerfouten |
| HVPC cold exact | **FAIL: `6,450 s` > `5,000 s`** |
| HVPC warm cache | PASS: `0,084 s` |
| HVPC same-session | PASS: `0,024 s` |
| Exact-SHA Windows one-folder/portable/installer | PENDING / nog niet verifieerbaar via beschikbare workflowstatusbron |

De lokale fase-3 verzamelrun bevatte daarnaast vier reeds bestaande platformafhankelijke Linux-fouten: Windows-DLL-controles voor CasADi, twee source-selftests die dezelfde Windows-runtimeverwachting gebruiken en een VTK/EGL-renderproef zonder bruikbare lokale EGL-device. De echte fase-3 real-filematrix is na generatie van het ontbrekende fase-1-evidencebestand afzonderlijk PASS. Deze platformfouten zijn niet als Viewer-PASS geboekt.

## Gapregister na aanpassing

| Gap | Nieuwe status | Beoordeling |
|---|---|---|
| GAP-V-001 | PENDING_CI | Code is aan exacte remote HEAD gebonden; volledige releasebundel nog niet bewezen |
| GAP-V-002 | PENDING_CI | Interactierootcause aangepast; nieuwe native HVPC-FPS vereist |
| GAP-V-003 | PENDING_CI | Dubbele render verwijderd; nieuwe native input-p95/p99 vereist |
| GAP-V-004 | **FAIL** | Lokale actuele cold exact is 6,450 s en overschrijdt 5 s |
| GAP-V-005 | PENDING_CI | Lokale 602 s-soak PASS; exacte real-HVPC OpenGL-soak volgt in workflow |
| GAP-V-006 | PENDING_CI | Harde `<10%`-gate aanwezig; actuele native HVPC-uitkomst ontbreekt |
| GAP-V-007 | BLOCKED_EXTERNAL_EVIDENCE | Nieuwe captures zijn beschikbaar na Windows-run; menselijke acceptatie ontbreekt |
| GAP-V-008 | **CLOSED** | Qt en native VTK worden in één deterministische capture gecomposeerd |
| GAP-V-009 | **CLOSED** | Releasegate deriveert alle 317 actieve requirements dynamisch |
| GAP-V-010 | PENDING_CI | Exacte Windows package-matrix voor nieuwe HEAD is nog niet bewezen |
| GAP-V-011 | BLOCKED_EXTERNAL_EVIDENCE | Zelfde-machine Trimblevergelijking vereist een externe Trimble-sessie |
| GAP-V-012 | **CLOSED** | Echte depth-aware hidden-line pipeline geleverd |
| GAP-V-013 | **CLOSED** | BCF 2.1 wordt vóór promotie tegen officiële XSD’s gevalideerd |
| GAP-V-014 | PARTIAL | Viewport is modeldominant; menselijke UX-PASS ontbreekt |
| GAP-V-015 | PENDING_CI | Lokale soak bestaat; exact-SHA HVPC-soak is in de releaseworkflow opgenomen |
| GAP-V-016 | **CLOSED** | Viewer- en previewversies hebben één bron; authority verwijst naar releasebinding |
| GAP-V-017 | PARTIAL | PR #9 bestaat; merge/default-branchbesluit vereist reviewbevoegdheid |
| GAP-V-018 | **CLOSED** | Contract- en namespace-imports werken zonder native CAD/renderstack |
| GAP-V-019 | BLOCKED_EXTERNAL_EVIDENCE | iGPU/dGPU en 1080p/4K hardwarematrix ontbreekt |
| GAP-V-020 | PARTIAL | DPI en keyboardfocus zijn getest; volledige screenreader/contrastacceptatie ontbreekt |
| GAP-V-021 | PARTIAL | Versieduplicaten/eager compatibiliteit zijn verwijderd; bredere legacyreductie blijft onderhoudswerk |
| GAP-V-022 | PARTIAL | HVPC real-filepad is aanwezig; tweede grote revision/clash-regressiedataset ontbreekt |

Statusverdeling: **6 CLOSED, 7 PENDING_CI, 1 FAIL, 3 BLOCKED_EXTERNAL_EVIDENCE en 5 PARTIAL**.

## Wat nog nodig is voor echte 100%

1. Behaal cold exact `≤5,000 s` op de overeengekomen referentiemachine; de huidige lokale uitkomst is een harde FAIL.
2. Laat de exacte-SHA Windows-run volledig slagen en archiveer one-folder, portable, installer, uninstall, 10-minuten-HVPC-soak en de 317/317-matrix.
3. Laat de 25 referentieparen en de modeldominante UX menselijk accepteren.
4. Voer de object-voor-object Trimblevergelijking uit met hetzelfde model, camera, viewport en acties.
5. Kwalificeer minimaal iGPU/dGPU en 1080p/4K, rond accessibility af en test een tweede groot revision/clash-model.
6. Merge PR #9 na review naar de aangewezen release/default branch.

Tot die punten aantoonbaar PASS zijn, is de correcte vrijgavestatus: **NIET RELEASEGEREED**.
