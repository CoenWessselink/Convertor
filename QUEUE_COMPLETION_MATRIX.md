# QUEUE COMPLETION MATRIX

Gereconstrueerd uit prompts, overdrachten, broncode, git-history en echte validatiebestanden. Niet uitgevoerde externe proeven zijn niet groen gemaakt.

Recente commits: bdc449c Ignore untracked evidence in release preflight<br>9a51606 Measure worker speedup across independent IFC sources<br>122804e Prove complete geometry worker recovery<br>f62f897 Separate explicit transitions from soak stalls<br>7e0aa56 Use scene bundles in packaged warm probes

| Opdracht/milestone | Verwacht resultaat | Gevonden implementatie | Relevante commit(s) | Relevante tests | Status |
|---|---|---|---|---|---|
| Viewer basis en Trimble-functies | Permanente ViewerHost, selectie/meten/doorsnede | Geïntegreerde VTK Viewer workspace met selectie, meten, doorsnede en exacte geometrie | 3fa0136, afa8f0b | final closeout en A-Z acceptance | COMPLETE |
| Loader Engine V2 | Workerpool, priority, Cache V2, uploadbudget/governor | Brongegroepeerde persistent workers, herstelbewijs, scene-bundles, scheduler en uploadbudget | 3fa0136, 7e0aa56, 122804e, 9a51606 | packaged Loader V2 8/8 en final closeout | COMPLETE |
| HVPC 3-5 seconden | Volledig exact model binnen doel | 5.725 exacte meshes en sub-seconde warm/same-session; koude exacte load blijft ruim boven 5 s | 3fa0136, 7e0aa56, 122804e | 20 cold, 40 warm, same-session runs | PARTIAL |
| 10 minuten Viewer soak | Geen onbedoelde stall >100 ms en geen lekken | 600 s, 8.733 acties, nul onbedoelde stalls/leaks/verkeerde picks, 0,075% RSS-drift | f62f897, 122804e | REAL_10MIN_SOAK.json | COMPLETE |
| Same-machine Trimble | Gepaarde observatie op dezelfde IFC en machine | Trimble is aanwezig, maar geen betrouwbare gepaarde bedienings- en tijdmeting vastgelegd | - | TRIMBLE_COMPARISON.md | NOT_PROVEN |
| UI Master V5/V5.1/V5.2 | 5 domeinen, 25 taakschermen, industrieel donker ontwerp | V5-domeinen en concrete workspaces aanwezig; pixel-/schermpariteit met alle referenties niet bewezen | 3fa0136, afa8f0b | A-Z workspace screenshots en UI-smokes | PARTIAL |
| BOM, machines en optimalisatie | BOM, routing, profiel- en plaatnesting | BOM/routing/nestingkernen en concrete panelen aanwezig; volledige praktijkpariteit niet bewezen | 3fa0136 | phase2, phase3 en A-Z acceptance | PARTIAL |
| Bewerken en scribing | Alle maakbewerkingen en markeringen | Part Workbench en M18 scribing geïntegreerd | 3fa0136 | phase2/phase3 smokes | COMPLETE |
| Converteren IFC/STEP/NC | Exact en zonder Part Workbench-afhankelijkheid | IFC/STEP/NC-richtingen, NC1 naar STEP en productiepaketten werken packaged | 3fa0136, afa8f0b | A-Z acceptance en installed packaged runtime | COMPLETE |
| Tekeningen en PDF | Vectorprojectie, maten en PDF | DrawingProjectionModel en vector-native PDF met gedeelde outputservice | 3fa0136 | final gap closure en A-Z acceptance | COMPLETE |
| Print Center en uitvoer | Eén DocumentOutputService | Singleton DocumentOutputService en concreet Print Center | 3fa0136 | final gap closure en A-Z acceptance | COMPLETE |
| Manufacturing Geometry Interpreter V2 | Profielherkenning en onafhankelijke BREP-proof | Profielkandidaten en geometriepad verbeterd; volledige aangeleverde corpuspariteit niet bewezen | 3fa0136 | fase-1 smoke en regressietests | PARTIAL |
| Release en installer | Nieuwe EXE, portable en installer met packaged bewijs | Installer-upgrades, associaties, portable en installed native runtime bewezen | d9cc741, eb9f4eb, bdc449c | installed packaged runtime en association smoke | COMPLETE |

## Gate

De technische Viewer-closeout en packaged release zijn groen. De totale opdracht blijft PARTIAL zolang de koude HVPC-load niet 3-5 seconden haalt, dezelfde-machine Trimble-pariteit niet gepaard is gemeten en 100% visuele UI-pariteit niet onafhankelijk is bewezen.
