# QUEUE COMPLETION MATRIX

Gereconstrueerd uit prompts, overdrachten, broncode, git-history en echte validatiebestanden. Niet uitgevoerde externe proeven zijn niet groen gemaakt.

Recente commits: 9ed87cb perf(viewer): render exact HVPC within warmstart gate<br>0e4a2b4 chore(acceptance): sync generated requirement ledgers<br>d694a3e chore(acceptance): refresh master traceability<br>a8ce830 fix(ui): route HVPC surfaces through canonical workspaces<br>bcb2c87 fix(manufacturing): close interpreter corpus parity

| Opdracht/milestone | Verwacht resultaat | Gevonden implementatie | Relevante commit(s) | Relevante tests | Status |
|---|---|---|---|---|---|
| Viewer basis en Trimble-functies | Permanente ViewerHost, selectie/meten/doorsnede | Geïntegreerde VTK Viewer workspace met selectie, meten, doorsnede en exacte geometrie | 3fa0136, afa8f0b | final closeout en A-Z acceptance | COMPLETE |
| Loader Engine V2 | Workerpool, priority, Cache V2, uploadbudget/governor | Brongegroepeerde persistent workers, herstelbewijs, scene-bundles, scheduler en uploadbudget | 3fa0136, 7e0aa56, 122804e, 9a51606 | packaged Loader V2 8/8 en final closeout | COMPLETE |
| HVPC 3-5 seconden | Volledig exact model binnen doel | Native exact warmstart toont 5.725 fysieke objecten via 1.496 gedeelde meshes in 3,264 s; cacheloze eerste IFC-tessellatie blijft 7,939 s | 9ed87cb, 3fa0136, 7e0aa56, 122804e | QT_PROGRESSIVE_EXACT_WARMSTART_PASS en cold/warm/same-session matrix | PARTIAL |
| 10 minuten Viewer soak | Geen onbedoelde stall >100 ms en geen lekken | 600 s, 8.733 acties, nul onbedoelde stalls/leaks/verkeerde picks, 0,075% RSS-drift | f62f897, 122804e | REAL_10MIN_SOAK.json | COMPLETE |
| Same-machine Trimble | Gepaarde observatie op dezelfde IFC en machine | Trimble is aanwezig, maar geen betrouwbare gepaarde bedienings- en tijdmeting vastgelegd | - | TRIMBLE_COMPARISON.md | NOT_PROVEN |
| UI Master V5/V5.1/V5.2 | 5 domeinen, 25 taakschermen, lichte professionele V5.2-primary UI | 31 native HVPC-surfaces, 25 referentieparen en native VTK-framebuffer aanwezig; pixelpariteit blijft human-review-required | a8ce830, 89ef113, 9ed87cb | UI_V52_SURFACE_ACCEPTANCE en QT_PROGRESSIVE_EXACT_WARMSTART_PASS | PARTIAL |
| BOM, machines en optimalisatie | BOM, routing, profiel- en plaatnesting | Een productieauthority, fail-closed routing en concrete BOM/routing/nestingworkspaces zijn door phase 2 bewezen | 3fa0136, a8ce830 | phase2 gate en A-Z acceptance | COMPLETE |
| Bewerken en scribing | Alle maakbewerkingen en markeringen | Part Workbench en M18 scribing geïntegreerd | 3fa0136 | phase2/phase3 smokes | COMPLETE |
| Converteren IFC/STEP/NC | Exact en zonder Part Workbench-afhankelijkheid | IFC/STEP/NC-richtingen, NC1 naar STEP en productiepaketten werken packaged | 3fa0136, afa8f0b | A-Z acceptance en installed packaged runtime | COMPLETE |
| Tekeningen en PDF | Vectorprojectie, maten en PDF | DrawingProjectionModel en vector-native PDF met gedeelde outputservice | 3fa0136 | final gap closure en A-Z acceptance | COMPLETE |
| Print Center en uitvoer | Eén DocumentOutputService | Singleton DocumentOutputService en concreet Print Center | 3fa0136 | final gap closure en A-Z acceptance | COMPLETE |
| Manufacturing Geometry Interpreter V3 | Volledige V2-gap closure, 45 categorieen en exact-SHA package | Feature-aware pipeline, compound proof, fail-closed routing, transactionele promotie en Controle-workspace | aee2466, f740daf, 661cf7e, aea07b4 | V3 fase 1/2/3, final acceptance en packaged runtime | COMPLETE |
| Release en installer | Nieuwe EXE, portable en installer met packaged bewijs | Eerdere packages zijn bewezen, maar een fresh release voor de actuele exact-SHA en finale gate ontbreekt | d9cc741, eb9f4eb, bdc449c | installed packaged runtime en association smoke | PARTIAL |

## Gate

De native exacte Viewer-warmstart en interactierendering zijn groen. De totale opdracht blijft PARTIAL zolang de cacheloze eerste IFC-tessellatie niet 3-5 seconden haalt, dezelfde-machine Trimble-pariteit niet gepaard is gemeten, 100% visuele UI-pariteit niet onafhankelijk is bewezen en geen fresh exact-SHA releasegate bestaat.
