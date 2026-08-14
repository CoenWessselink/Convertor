# CWS Viewer V0 — bron- en integratiebaseline

## Status

V0 levert de **contractuele viewerbasis**, niet de grafische eindviewer.
De bestaande Tkinter/Matplotlib-weergave blijft ongewijzigd beschikbaar.

Gebouwd:

- apart `cws_viewer`-package in dezelfde repository;
- immutable `ProjectScene`, `SceneNode`, `GeometryResource` en styles;
- semver voor Viewer API, sceneschema en viewerstate;
- deterministische JSON en SHA-256-scenehash;
- stable-ID-, parent-, cycle-, transform-, geometryref- en payloadvalidatie;
- read-only adapter van Canonical Project Model naar scenestructuur;
- instancinghandle op placement-onafhankelijke geometry hash;
- hoofdapp/viewerprotocol, commands en events;
- headless contractbackend voor integratie- en persistencetests;
- runtime-/backenddiagnostiek;
- native CadQuery/CasADi-functionele selftest;
- verbodsscan voor Trimble binaries in CWS-bron/release;
- CasADi PyInstaller-hook en Windows DLL-search runtimehook;
- verpakte, portable en geïnstalleerde GUI/native tests in de Windows-workflow.

Niet geclaimd in V0:

- grafische Qt-viewer;
- totaalmodelrendering;
- exact BREP-picking;
- sections, measurements of compare;
- performance-SLA;
- Windows-artifact uit deze Linuxruntime.

## Belangrijke compatibiliteitsnoot

De offline Git-bundle waarop deze werkboom is gebaseerd eindigt op commit
`97d2b08`. De publieke branch `v0.8-codex-handover` bevat inmiddels meer
commits en meldt Project Model 2.4. De lokale bundle gebruikt schema 2.3.
Daarom accepteert de adapter Project Model major 2, maar staat alleen 2.3 in de
lijst met lokaal volledig gevalideerde versies. Vóór merge moet deze viewerbasis
op de actuele Codex-branch worden gerebased en tegen 2.4 worden getest.

## Lokale V0-gate

- `compileall`: geslaagd;
- volledige smoke-baseline: 27/27 scripts geslaagd;
- viewercontract: 8/8;
- ProjectModel-sceneadapter: 2/2;
- runtime/integriteit: 3/3;
- bron-GUI-smoke onder virtueel display: geslaagd;
- CasADi/CadQuery/OCP functionele native selftest: geslaagd;
- twee bestaande P1811-tests zijn expliciet overgeslagen omdat de echte binaire fixture in de offline werkboom ontbreekt.

Zie `VIEWER_V0_BASELINE_REPORT.md` voor hashes en testdetails.
