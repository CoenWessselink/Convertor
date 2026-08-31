# CWS CONVERTOR — COMPLETE GAP ANALYSE
## Huidige canonical code versus volledige actuele doelarchitectuur

**Auditdatum:** 31-08-2026  
**Repository:** `CoenWessselink/Convertor`  
**Canonical branch:** `agent/cws-product-ui-reintegration-v1`  
**Canonical SHA:** `dc4e3e2ec2f91c40aad271d985b3fe59a44c7325`  
**Versie:** `0.10.18-beta-dev`  
**Project Model:** `2.25`  
**Canonical Part:** `1.1`

> De percentages zijn engineering-inschattingen van dekking op de canonical GitHub-SHA. Ze zijn geen acceptance-PASS. Lokaal/on-gepusht Codexwerk wordt bewust niet als uitgevoerd geteld.

# 1. Samenvatting

De 29-augustus codebasis is **geen onaf product**. De onderliggende canonical architectuur, Workbench, manufacturing faces/contact/scribing, Profile Nesting, BOM, Quality, conversion, readiness/export en Windows releaseketen zijn substantieel.

Maar het **actuele einddoel is groter geworden na 29 augustus**. De requirements van 30–31 augustus voegen onder andere toe:

- harde Viewer Performance Closeout;
- volledige V5/V5.1/V5.2 product-UI;
- machine routing vanuit BOM;
- full Plate Nesting;
- Manufacturing Geometry Interpreter V2;
- vector production drawing/PDF consolidation;
- centrale Print Center;
- Planning/Shopfloor;
- nieuwe master traceability en total acceptance.

Daarom zijn de huidige gewogen scores voor de **volledige actuele scope**:

- **Implementation:** 58.5%
- **Integration:** 53.5%
- **Testing:** 46.8%
- **Release-proven:** 38.9%

De succesvolle 29-augustus `Final release proof` blijft waardevol, maar bewijst alleen de toenmalige scope. Het huidige programma kan pas opnieuw als 100% eindresultaat worden beschouwd nadat alle actieve requirements op één nieuwe exact-SHA opnieuw zijn bewezen.

# 2. Belangrijkste bevindingen

## 2.1 Wat al zeer sterk is
- één canonical Project/Part Model;
- één Unified Application Context;
- permanente Viewer-context;
- één Workbench write path;
- BOM met hashes/traceability;
- Manufacturing Faces, Contact Geometry, Scribing/Identification, Neutral Jobs;
- Profile Nesting is een volwassen subsystem;
- fail-closed machine capability;
- Trusted PDF/external PDF foundation;
- quality/NCR/reinspection foundation;
- production readiness/export/release backend;
- exact-SHA Windows build/release infrastructuur.

## 2.2 De tien grootste gaps
1. Viewer throughput/performanceproof.
2. V5.2 UI/control system.
3. BOM & Machines routing.
4. Manufacturing Geometry Interpreter.
5. Full Plate Nesting.
6. Canonical vector Drawing/PDF integration.
7. Central Print/DocumentOutputService.
8. Unified all-format project intake.
9. Planning/Shopfloor.
10. Nieuwe complete requirement traceability + acceptance.

# 3. Volledige statusmatrix

| ID | Domein | Implemented | Integrated | Tested | Release-proven | Prio | Status |
|---|---|---:|---:|---:|---:|---|---|
| D01 | Canonical architectuur / één waarheid | 92% | 90% | 85% | 80% | P0 | STERK |
| D02 | Project Model / storage / hashes / Workbench persistence | 90% | 90% | 85% | 80% | P0 | STERK |
| D03 | Unified project intake — IFC/STEP/NC1/PDF/batch/revision | 55% | 50% | 45% | 40% | P0 | PARTIAL |
| D04 | Classificatie / profiel / materiaal / productie-identiteit | 80% | 75% | 70% | 65% | P1 | GOEDE FOUNDATION |
| D05 | Viewer functionele breedte | 85% | 82% | 75% | 65% | P0 | STERK |
| D06 | Viewer performance closeout | 45% | 40% | 30% | 20% | P0 | GROOTSTE TECHNISCHE GAP |
| D07 | Trimble observable parity | 65% | 60% | 40% | 20% | P0 | FOUNDATION, NIET BEWEZEN |
| D08 | V5/V5.1/V5.2 visuele product-UI | 15% | 10% | 5% | 0% | P0 | NIET DOORGEVOERD |
| D09 | UI control binding / design system / icon authority | 5% | 5% | 0% | 0% | P0 | SPEC BESTAAT, REPO NIET |
| D10 | Part Workbench / edit / canonical rebuild / roundtrip | 88% | 85% | 80% | 70% | P0 | STERK |
| D11 | Canonical BOM / quantities / traceability | 85% | 82% | 75% | 70% | P0 | STERK |
| D12 | BOM & Machines / automatische routing / manual override | 35% | 25% | 15% | 5% | P0 | GROTE GAP |
| D13 | Machine capability / reachability / fail-closed safety | 80% | 75% | 70% | 65% | P0 | STERKE FOUNDATION |
| D14 | Manufacturing Faces / Contact / Scribing / Identification / Neutral Job | 90% | 88% | 82% | 75% | P0 | ZEER STERK |
| D15 | Manufacturing Geometry Interpreter V2 | 10% | 5% | 0% | 0% | P0 | NIEUW SUBSYSTEEM ONTBREEKT |
| D16 | Profile Nesting | 85% | 75% | 70% | 60% | P1 | STERKE BACKEND |
| D17 | Plate Nesting | 30% | 25% | 20% | 10% | P0 | GROTE GAP |
| D18 | Converter / capability registry / roundtrip | 75% | 70% | 65% | 55% | P1 | GOEDE FOUNDATION |
| D19 | Trusted PDF / external PDF analyse / AI review | 75% | 65% | 60% | 50% | P1 | GOEDE FOUNDATION |
| D20 | Productietekeningen / vector PDF | 40% | 35% | 25% | 10% | P0 | KRITIEKE DUBBELE ROUTE |
| D21 | DocumentOutputService / Print Center / Ctrl+P / batchprint | 25% | 20% | 10% | 0% | P0 | GROTE GAP |
| D22 | Validatie / revisiecompare / maakbaarheid / evidence | 70% | 65% | 55% | 45% | P1 | GOEDE FOUNDATION |
| D23 | Quality / Inspection / NCR / release | 78% | 65% | 55% | 45% | P1 | STERKE FOUNDATION |
| D24 | Planning / Shopfloor / finite capacity | 15% | 10% | 5% | 0% | P1 | SUBSYSTEEM ONTBREEKT GROTENDEELS |
| D25 | Export / readiness / scope / verify / release backend | 85% | 80% | 75% | 70% | P0 | STERK |
| D26 | Viewer/project/user preference persistence | 65% | 55% | 45% | 35% | P1 | PARTIAL |
| D27 | Master traceability / acceptance voor ALLE actuele prompts | 40% | 35% | 30% | 20% | P0 | OUTDATED |

# 4. Belangrijke architectuurconflicten die expliciet moeten worden opgelost

## A. Oude 51/51 acceptance versus nieuwe scope
De bestaande workflow kan 51/51 groen zijn op de 29-aug scope, terwijl V5.2, Viewer closeout en Manufacturing Interpreter nog ontbreken. De nieuwe acceptance moet daarom requirements dynamisch uit een Master Requirement Traceability Matrix afleiden; een vaste oude checklist-count mag niet langer de definitieve productclaim zijn.

## B. Twee tekenroutes
`pdf_support.py` bevat een vector/Trusted-PDF foundation, maar de geïntegreerde `DrawingWorkspacePanel` roept `EngineeringDrawingGenerator` aan, dat de pagina met PIL bouwt en als raster-PDF opslaat. Dit moet één production vector Drawing authority worden.

## C. Machine capability zonder routingauthority
Machine capability/reachability bestaat, maar BOM → voorgestelde machine → toegewezen machine → Auto/Manual → route validation is nog geen centrale authority.

## D. Manufacturing foundation zonder interpreter
Manufacturing Faces/Contact/Scribing zijn sterk ná reviewed canonical geometry. De nieuwe source-BREP interpreter moet upstream evidence leveren, onafhankelijk reconstrueren/bewijzen en pas daarna transactioneel naar Workbench promoveren.

## E. Sterke Profile Nesting versus minimale Plate Nesting
Profile Nesting heeft solvers/validators/stock/reservations/manual planning. Plate Nesting is nog rechthoekige shelf placement. Plate moet op hetzelfde kwaliteitsniveau komen zonder Profile Nesting te herschrijven.

## F. Project intake versus losse converterroutes
Project intake is canonical sterk voor IFC/STEP, terwijl NC1/PDF elders bestaan. V5 vraagt één consistente intake UX en project/source registration policy over ondersteunde formaten.

## G. V9 UI versus V5.2 UI
De huidige app toont nog 12 oude tabs, monolithische QSS en legacy V9/V6-teksten. Het eindproduct vereist exact `Project | Viewer | Productie | Controle | Uitvoer`, Light default, versioned visual references, design system, IconRegistry en stable `ui_test_id`.

# 5. Domeindetails

### D01 — Canonical architectuur / één waarheid
**Status:** STERK · **Prioriteit:** P0

**Gap:** Nieuwe subsystemen moeten aansluiten op bestaande authorities; legacy UI-surfaces en oude naming nog consolideren.

**Belangrijkste code/evidence:** `docs/CURRENT_PRODUCT_AUTHORITY.md`, `cws_convertor/integration/ui_context.py`, `cws_convertor/project/model.py`
### D02 — Project Model / storage / hashes / Workbench persistence
**Status:** STERK · **Prioriteit:** P0

**Gap:** Laatste V5 state/user-preference scheiding en migration/corruption/cross-project acceptance nog verbreden.

**Belangrijkste code/evidence:** `cws_convertor/project/model.py`, `cws_convertor/project/storage.py`, `cws_convertor/project/workbench.py`
### D03 — Unified project intake — IFC/STEP/NC1/PDF/batch/revision
**Status:** PARTIAL · **Prioriteit:** P0

**Gap:** Project baseline/service materialiseert primair IFC/STEP; NC1/PDF bestaan elders maar nog niet als één project-intake authority met alle edge cases.

**Belangrijkste code/evidence:** `cws_convertor/project/service.py`, `cws_convertor/project/baseline.py`, `cws_convertor/ui_qt/project_intake.py`
### D04 — Classificatie / profiel / materiaal / productie-identiteit
**Status:** GOEDE FOUNDATION · **Prioriteit:** P1

**Gap:** Geometry-based profielbewijs ontbreekt nog als onderdeel van de Manufacturing Geometry Interpreter; metadata/text recognition blijft reviewplichtig.

**Belangrijkste code/evidence:** `cws_convertor/project/classification.py`, `profile_database.py`, `material_database.py`
### D05 — Viewer functionele breedte
**Status:** STERK · **Prioriteit:** P0

**Gap:** Volledige V5.2 control mapping, box/crossing-selection parity, state persistence en actuele packaged acceptance opnieuw bewijzen.

**Belangrijkste code/evidence:** `cws_viewer/ui_qt/vtk_real_project_widget_feel_v2.py`, `cws_convertor/ui_qt/viewer_tools.py`, `tests/viewer_v15_trimble_feel_v2_smoke.py`
### D06 — Viewer performance closeout
**Status:** GROOTSTE TECHNISCHE GAP · **Prioriteit:** P0

**Gap:** Single-worker exact load, Cache V1, selected-only priority, geen echte frame-upload governor, 8x interactive MSAA, geen volledige packaged cold/warm/soak proof.

**Belangrijkste code/evidence:** `cws_convertor/ui_qt/project_workspace.py`, `cws_viewer/cache/mesh_cache.py`, `cws_convertor/viewer/progressive_loader.py`, `cws_viewer/backends/vtk_project_mesh_adaptive.py`
### D07 — Trimble observable parity
**Status:** FOUNDATION, NIET BEWEZEN · **Prioriteit:** P0

**Gap:** Gedragstestfoundation bestaat; complete same-machine/model behavior + performance matrix ontbreekt.

**Belangrijkste code/evidence:** `tests/viewer_v15_trimble_feel_v2_smoke.py`, `cws_viewer/core/viewer_feel_navigation_v2.py`
### D08 — V5/V5.1/V5.2 visuele product-UI
**Status:** NIET DOORGEVOERD · **Prioriteit:** P0

**Gap:** Canonical main window is nog V9/12-tab shell met legacy teksten/QSS; definitieve vijfdeling Project|Viewer|Productie|Controle|Uitvoer ontbreekt.

**Belangrijkste code/evidence:** `cws_convertor/ui_qt/main_window.py`
### D09 — UI control binding / design system / icon authority
**Status:** SPEC BESTAAT, REPO NIET · **Prioriteit:** P0

**Gap:** SCREEN_MANIFEST/control binding/ui_test_id/IconRegistry/V5.2 design system ontbreken in canonical repo.

**Belangrijkste code/evidence:** `cws_convertor/ui_qt/main_window.py`, `cws_convertor/ui_qt/ribbon_icons.py`
### D10 — Part Workbench / edit / canonical rebuild / roundtrip
**Status:** STERK · **Prioriteit:** P0

**Gap:** Legacy editor volledig terugtrekken na parity; unsupported richer feature rebuild/roundtrip uitbreiden; interpreter promotion koppelen.

**Belangrijkste code/evidence:** `cws_convertor/project/workbench.py`, `cws_convertor/project/canonical_rebuild.py`, `cws_convertor/project/roundtrip.py`, `cws_convertor/ui_qt/functional_workspaces.py`
### D11 — Canonical BOM / quantities / traceability
**Status:** STERK · **Prioriteit:** P0

**Gap:** Nieuwe production-status joins en V5 hub moeten bovenop BOM truth komen zonder quantity truth te muteren.

**Belangrijkste code/evidence:** `cws_convertor/bom/models.py`, `cws_convertor/bom/engine.py`
### D12 — BOM & Machines / automatische routing / manual override
**Status:** GROTE GAP · **Prioriteit:** P0

**Gap:** Geen centrale MachineRoutingService/assignment authority, recommended/assigned/auto-manual flow en V5 production hub gevonden.

**Belangrijkste code/evidence:** `cws_convertor/bom/models.py`, `cws_convertor/manufacturing/machine_capability.py`
### D13 — Machine capability / reachability / fail-closed safety
**Status:** STERKE FOUNDATION · **Prioriteit:** P0

**Gap:** Capability is diep voor manufacturing/marking; route-aggregate, machine library UI en bredere operation mapping ontbreken.

**Belangrijkste code/evidence:** `cws_convertor/manufacturing/machine_capability.py`, `cws_convertor/manufacturing/machine_capability_model.py`
### D14 — Manufacturing Faces / Contact / Scribing / Identification / Neutral Job
**Status:** ZEER STERK · **Prioriteit:** P0

**Gap:** V5 Control/Manufacturing Geometry integratie, final E2E en interpreter-upstream feeding moeten nog volledig samenkomen.

**Belangrijkste code/evidence:** `cws_convertor/manufacturing/__init__.py`, `cws_convertor/manufacturing/faces.py`, `cws_convertor/manufacturing/contact.py`, `cws_convertor/manufacturing/neutral_job.py`
### D15 — Manufacturing Geometry Interpreter V2
**Status:** NIEUW SUBSYSTEEM ONTBREEKT · **Prioriteit:** P0

**Gap:** Geen source FAG, decomposition hypotheses, independent reconstruction/two-way BREP proof, residual solver of transactionele Workbench promotion aangetroffen.

**Belangrijkste code/evidence:** `cws_convertor/project/source_geometry.py`, `cws_convertor/project/canonical_rebuild.py`
### D16 — Profile Nesting
**Status:** STERKE BACKEND · **Prioriteit:** P1

**Gap:** Complete V5 production flow, packaged E2E, full proof/status/UI reconciliation en current master acceptance nog afronden.

**Belangrijkste code/evidence:** `cws_convertor/optimization/profile_nesting/`
### D17 — Plate Nesting
**Status:** GROTE GAP · **Prioriteit:** P0

**Gap:** Huidige solver is rechthoekige deterministic shelf solver; polygonen/holes/grain/remnants/reservations/manual locks/exact polygon validation ontbreken.

**Belangrijkste code/evidence:** `cws_convertor/optimization/plate_nesting/core.py`
### D18 — Converter / capability registry / roundtrip
**Status:** GOEDE FOUNDATION · **Prioriteit:** P1

**Gap:** Rijkere features dan hole blijven terecht geblokkeerd; scope-first V5 UX en uitgebreide lossless feature coverage nog sluiten.

**Belangrijkste code/evidence:** `cws_convertor/conversion_capabilities.py`, `cws_convertor/conversion_worker.py`, `cws_convertor/project/roundtrip.py`
### D19 — Trusted PDF / external PDF analyse / AI review
**Status:** GOEDE FOUNDATION · **Prioriteit:** P1

**Gap:** Consolidatie met production Drawing engine en actuele V5 PDF Review/evidence flow vereist; external PDF blijft confidence/review-gated.

**Belangrijkste code/evidence:** `pdf_support.py`, `ai_support.py`, `dimension_graph.py`
### D20 — Productietekeningen / vector PDF
**Status:** KRITIEKE DUBBELE ROUTE · **Prioriteit:** P0

**Gap:** Vectorfoundation bestaat in pdf_support, maar de geïntegreerde DrawingWorkspace gebruikt PIL-rastergenerator en slaat de hele pagina als raster-PDF op.

**Belangrijkste code/evidence:** `pdf_support.py`, `cws_convertor/ui_qt/engineering_drawing.py`, `cws_convertor/ui_qt/functional_workspaces.py`
### D21 — DocumentOutputService / Print Center / Ctrl+P / batchprint
**Status:** GROTE GAP · **Prioriteit:** P0

**Gap:** Geen centrale DocumentOutputService/Print Center authority gevonden; output zit verdeeld over drawing/PDF/export.

**Belangrijkste code/evidence:** `cws_convertor/ui_qt/engineering_drawing.py`, `cws_convertor/production_export/`
### D22 — Validatie / revisiecompare / maakbaarheid / evidence
**Status:** GOEDE FOUNDATION · **Prioriteit:** P1

**Gap:** Laatste V5 Controle-structuur, Manufacturing Geometry, Evidence, PDF Review en Problem Center nog integreren en volledig click-through bewijzen.

**Belangrijkste code/evidence:** `cws_convertor/ui_qt/main_window.py`, `cws_viewer/revisions/`, `cws_convertor/production_export/readiness.py`
### D23 — Quality / Inspection / NCR / release
**Status:** STERKE FOUNDATION · **Prioriteit:** P1

**Gap:** Volledige operator-UI, traceability en koppeling met planning/shopfloor/product readiness nog afronden.

**Belangrijkste code/evidence:** `cws_convertor/quality/model.py`
### D24 — Planning / Shopfloor / finite capacity
**Status:** SUBSYSTEEM ONTBREEKT GROTENDEELS · **Prioriteit:** P1

**Gap:** Geen dedicated Resource/WorkCenter/Shift/ProductionOrder/ScheduledOperation finite-capacity subsystem aangetroffen.

**Belangrijkste code/evidence:** `cws_convertor/integration/production_workflow.py`
### D25 — Export / readiness / scope / verify / release backend
**Status:** STERK · **Prioriteit:** P0

**Gap:** V5 scope→formats→preflight→generate→verify→package UX en nieuwe routing/quality/planning gates aan dezelfde releaseauthority koppelen.

**Belangrijkste code/evidence:** `cws_convertor/production_export/`, `cws_convertor/integration/production_workflow.py`
### D26 — Viewer/project/user preference persistence
**Status:** PARTIAL · **Prioriteit:** P1

**Gap:** Projectstate en userprefs versioned scheiden; columns/theme/splitters/printer plus saved views/measurements/sections/markups volledig restart/migration testen.

**Belangrijkste code/evidence:** `cws_convertor/integration/ui_context.py`, `cws_convertor/project/storage.py`
### D27 — Master traceability / acceptance voor ALLE actuele prompts
**Status:** OUTDATED · **Prioriteit:** P0

**Gap:** Repo traceability wijst nog naar 27-aug prompt; 30/31-aug UI/performance/interpreter requirements zijn niet onderdeel van de 29-aug 51/51 acceptance.

**Belangrijkste code/evidence:** `docs/CWS_CONVERTOR_PROMPT_TRACEABILITY.md`, `.github/workflows/final-release-proof.yml`, `tools/run_full_product_acceptance.py`


# 6. Logische bouwvolgorde naar 100%

## Fase 1 — Canonical foundation closeout + Viewer + Intake + V5.2 shell
Eerst performance en architectuur dichtzetten zodat latere UI/productie niet bovenop een instabiele loadpipeline wordt gebouwd. Tegelijk alle actieve requirements en UI references versioned in de repo plaatsen en de definitieve shell/design system invoeren.

## Fase 2 — Productiehart compleet
BOM & Machines, routing, Workbench, Manufacturing Geometry Interpreter, bestaande manufacturing chain, Profile Nesting, full Plate Nesting en Converter vormen één production flow.

## Fase 3 — Documenten, Controle, Quality, Planning en Uitvoer
Vector tekeningen/PDF, external/trusted PDF, Print Center, Controle/Evidence, Quality, Planning/Shopfloor, Rapport en Export Center volledig integreren; alle 31 V5 surfaces/function states afbouwen.

## Fase 4 — Total Product Acceptance + exact-SHA Windows release
Geen nieuwe features. Alleen volledig bewijzen: alle controls, screenshots, DPI, workflows, negative/cancel/rollback, persistence, stress/soak, Viewer performance, Trimble evidence, one-folder, portable, installer, SBOM, checksums, source ZIP, Git bundle en final release manifest.

# 7. Wat “100%” in deze audit betekent

100% betekent:
- alle **actieve software requirements** geïmplementeerd, geïntegreerd en getest;
- geen required `FAIL`, `PARTIAL`, `NOT_IMPLEMENTED` of `NOT_TESTED`;
- product exact-SHA reproduceerbaar;
- geen false GREEN;
- alle safety gates fail-closed.

Het betekent nadrukkelijk NIET dat fysieke machine/controller-kwalificatie wordt verzonnen. Die mag als `BLOCKED_EXTERNAL_EVIDENCE` blijven staan terwijl `machine_transfer.allowed=false` blijft.

# 8. Eindconclusie

De huidige basis is technisch waardevol maar de **nieuwe volledige doeldefinitie is nog niet release-proven**. Het pad naar 100% is geen rewrite; het is een gerichte consolidatie van circa tien grote ontbrekende productblokken, gevolgd door één nieuwe totale acceptance op exact één commit.
