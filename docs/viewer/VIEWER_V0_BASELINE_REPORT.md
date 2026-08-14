# CWS Viewer V0 — baseline- en validatierapport

**Fase:** V0 — bron-, integratie- en Windows-runtimebaseline  
**Gegenereerd:** 2026-08-13T13:44:45.427046+00:00  
**Lokale branch:** `feature/cws-viewer-core`  
**Offline basiscommit:** `97d2b08c62ec2c7e10476884e4bbabcff22ea61f`  
**Projectmodel in offline basis:** 2.3

## Resultaat

- `compileall`: **geslaagd**;
- smoke-scripts: **27/27 geslaagd**;
- bekende skips: **2**;
- nieuwe viewercontracttests: **8/8**;
- ProjectModel→Scene-adaptertests: **2/2**;
- viewer runtime-/integriteitstests: **3/3**;
- native source-runtimecontrole: **geslaagd** voor CasADi, CadQuery, OCP, PyMuPDF en Matplotlib;
- verboden Trimble-binaries in CWS-bronboom: **0**.

De twee skips zitten in `pdf_review_smoke.py`: de echte binaire P1811-handoverfixture ontbreekt in deze offline bronboom. Er is niets als geslaagd aangemerkt zonder fixture.

## Belangrijke basisbeperking

Deze V0-werkboom is gebouwd op de lokaal beschikbare Codex-bundle (`97d2b08`, Project Model 2.3). De publieke GitHub-branch bevat latere commits en Project Model 2.4. De viewer is daarom als eigen `cws_viewer`-module met stabiele adapter- en API-contracten gebouwd. **Voor merge moet deze commit op de actuele GitHub-branch worden gerebased en moeten alle tests daar opnieuw worden uitgevoerd.**

## Windows-status

De Windows-packagingconfiguratie is aangescherpt met:

- expliciete CasADi-hook en native DLL-searchpad;
- echte native selftest met CasADi/CadQuery/OCP;
- verpakte GUI-smoke;
- opnieuw uitgepakte portable-smoke;
- geïnstalleerde-app-smoke zonder Python op `PATH`;
- workflow failure bij een ontbrekende `_casadi`-dependency.

Een echte Windows installer/portable build is in deze Linuxomgeving niet uitgevoerd. V0 is pas volledig vrijgegeven nadat de aangepaste GitHub Action op Windows groen is.

## Relevante dependencies

| Package | Versie in lokale controleomgeving |
|---|---:|
| `cadquery` | `2.8.0` |
| `casadi` | `3.7.2` |
| `cadquery-ocp` | `7.9.3.1.1` |
| `ifcopenshell` | `not-installed` |
| `PyMuPDF` | `1.26.7` |
| `matplotlib` | `3.10.8` |
| `numpy` | `2.3.5` |
| `vtk` | `9.6.2` |
| `PySide6` | `not-installed` |
| `PyInstaller` | `not-installed` |

## Smoke-overzicht

| Script | Status | Tests | Skips | Log-SHA-256 |
|---|---|---:|---:|---|
| `analytic_fitting_smoke.py` | passed | script | 0 | `560f5a32c7ae…` |
| `dimension_graph_smoke.py` | passed | 5 | 0 | `43c8db023df8…` |
| `ifc_semantic_import_smoke.py` | passed | 1 | 0 | `b4b62b9ea3ef…` |
| `p21_graph_smoke.py` | passed | 4 | 0 | `f371394a5113…` |
| `pdf_ai_smoke.py` | passed | script | 0 | `0c1a37f9bbdb…` |
| `pdf_review_smoke.py` | passed | 16 | 2 | `5bcb2d747bbf…` |
| `production_export_negative_smoke.py` | passed | script | 0 | `e4acede8c3c3…` |
| `production_export_smoke.py` | passed | script | 0 | `69a8a85ecf26…` |
| `project_baseline_smoke.py` | passed | 4 | 0 | `afdddf676402…` |
| `project_bom_smoke.py` | passed | 2 | 0 | `3e514e4cd01f…` |
| `project_classification_reference_smoke.py` | passed | 3 | 0 | `34c8bbc137e1…` |
| `project_classification_smoke.py` | passed | 3 | 0 | `eeb335a28543…` |
| `project_cli_smoke.py` | passed | 2 | 0 | `58dec88afdf2…` |
| `project_jobs_smoke.py` | passed | 3 | 0 | `96b8548490ce…` |
| `project_model_smoke.py` | passed | 13 | 0 | `7d09b80b35e2…` |
| `project_reference_files_smoke.py` | passed | 3 | 0 | `878805fbefe0…` |
| `project_semantic_reference_smoke.py` | passed | 1 | 0 | `a8bb0d03695b…` |
| `project_semantic_service_smoke.py` | passed | 4 | 0 | `24d8a104a405…` |
| `project_service_smoke.py` | passed | 3 | 0 | `2a9e1e57bdb3…` |
| `project_storage_smoke.py` | passed | 10 | 0 | `2d761fc8471f…` |
| `regression_smoke.py` | passed | script | 0 | `f8400c37f012…` |
| `review_workflow_smoke.py` | passed | 5 | 0 | `9bb481e9fabb…` |
| `step_semantic_import_smoke.py` | passed | 4 | 0 | `8ff87ceb9ee5…` |
| `viewer_contract_smoke.py` | passed | 8 | 0 | `b2d3d8c78e01…` |
| `viewer_project_adapter_smoke.py` | passed | 2 | 0 | `49e65016aec9…` |
| `viewer_runtime_smoke.py` | passed | 3 | 0 | `f141ae6a6531…` |
| `windows_native_runtime_smoke.py` | passed | script | 0 | `eb37c8ba5c15…` |

## Machineleesbare resultaten

De volledige JSON-resultaten staan in `V0_BASELINE_FINAL.json` in het validatiepakket. Alle individuele logs zijn op SHA-256 vastgelegd.
