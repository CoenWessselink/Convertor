# CWS Viewer / Convertor V15 — T0–T2 buildstatus

Datum: 2026-08-16  
Branch: `feature/trimble-parity-v15`  
Windows evidence source commit: `ade9824201fb7c2b948250a7ba4dfd81d4047068`  
GitHub Actions run: `31960676494`  
Workflow conclusion: **success**

## Status per fase

| Fase | Status | Bewijs / inhoud |
|---|---|---|
| T0 — baseline / forensic audit | **gereed** | phasing, baseline audit, reference boundary, parity matrix en no-regressioncontract gecommit |
| T1 — CWS workspace shell | **softwaregate groen** | dockable Project Explorer / Eigenschappen / Project-Review, floating panels, persistence, focusmodus, reset-layout, V14 baseline behouden |
| T2 — Project Explorer / objectbeheer | **eerste functionele pass groen** | rijk zoeken op canonical/project-/partmetadata, tree context actions, descendants/parent/assembly selection, canonical ID copy, Workbench route |
| T3–T11 | **nog niet als gereed claimen** | verder bouwen volgens `TRIMBLE_PARITY_V15_BUILD_PHASES.md` |
| Manufacturing M1–M9 / T8–T9 | **nog niet als gereed claimen** | inhoudelijke contracts/gates staan vast in de manufacturing-superprompt |

## Windows x64 build evidence

De build op Windows Server 2022 / Python 3.12 x64 heeft achtereenvolgens groen doorlopen:

1. dependency install + `pip check`;
2. `compileall`;
3. V15 workspace-contract smoke;
4. source V15 self-test;
5. source native/isolated IFC-worker self-test;
6. canonical CWSC fixture;
7. source hosted GUI smoke;
8. PyInstaller onedir build;
9. packaged V15 + frozen-worker gates;
10. packaged hosted GUI smoke;
11. portable package test met externe Python uit PATH;
12. Inno Setup installer build;
13. install + frozen V15 self-test zonder externe Python;
14. uninstall;
15. SHA-256 manifest;
16. artifact upload.

### Installer

`CWS_Viewer_Setup_1.4.0-v15-preview.1_x64.exe`

- bytes: `389577703`
- SHA-256: `cbbf12c584c49f2a007be760e4bc3c80b1ee4c57e3e2a9319fdd132f3659f979`

### Portable package

`CWS_Viewer_Portable_1.4.0-v15-preview.1_x64.zip`

- bytes: `621951840`
- SHA-256: `e86a33009785e2624aa353f19594564996af8f7e4ce3b38b15572a4a422eee70`

### GitHub artifact ZIP digests

- installer artifact: `66992c2a81ba76064e49f471cdeb8ff0fb190e8bcafde7a2cd60266e0a03a773`
- portable artifact: `6220dfd6a808c58b28d39dd6591f4c3682122402196313cbd8b80382eeea6c86`
- evidence artifact: `0f10ef1e6e6b2737eb7f27a9422099f708878ec503172623ae4afdf385c39ee7`

## V15 packaged/installed contract

De frozen EXE en geïnstalleerde build rapporteren:

- `schema = cws-viewer-workspace-15.1`;
- `version = 1.4.0-v15-preview.1`;
- `v15_cockpit_imported = true`;
- `worker_transport_preserved = true`;
- dockable/floating/persistent panels = true;
- rich project search = true;
- project tree context actions = true;
- descendants/parent/assembly selection = true;
- canonical ID copy = true;
- V14 functionality preserved = true.

## Releaseveiligheid

Deze build is een **V15 preview**, geen eindclaim van volledige Trimble-pariteit en geen production-machine release.

`production_machine_transfer_allowed = false`

De gebruiker kan deze EXE al installeren en de nieuwe workspace testen, maar T3–T11 en M1–M9 blijven expliciet open totdat hun eigen tests/evidence groen zijn. Native Trimble-cloudgedrag of proprietary controllergedrag wordt niet gekloond/geclaimd zonder rechtmatige specificatie en onafhankelijke owner evidence.

## Volgende bouwgate

T3: camera/view/navigation/clipping state verdiepen, daarna T4 selection/measurement/snapping, T5 views/markups/review en T6 compare/assemblies/clash/sequence. Daarna T7 export en T8/T9 manufacturingplanning.
