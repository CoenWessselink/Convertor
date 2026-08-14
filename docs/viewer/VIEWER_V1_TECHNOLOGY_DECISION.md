# CWS Viewer V1 — gemeten technologieproef

**Gegenereerd:** `2026-08-13T14:48:10.132881+00:00`  
**Platform:** `Linux-6.18.35-x86_64-with-glibc2.41`  
**Python:** `3.13.5 (main, Jul 15 2026, 20:25:40) [GCC 14.2.0]`  
**Rapporthash:** `9f8a5caf26c24eb2c06c256ba49bdc347ee8814c642d3271110a8e8e63617273`

## Besluit

- Project-/totaalmodelrenderer: **vtk_mesh**
- Exact Part Workbench-renderer: **occt_ais**
- Status: **conditional-hybrid-selected-windows-gate-pending**

- VTK heeft alle lokale synthetische scènes met één gedeelde mesh en stabiele instance-picking uitgevoerd.
- Bij 10.000 nodes bedroeg VTK lokaal 81.25 ms p95 per orbitframe, 0.172 ms p95 picking en 363.2 MiB gemeten procesdelta.
- OCCT/AIS is gekozen voor exact Part Workbench-niveau omdat het TopoDS/AIS BREP en subshape-selectie ondersteunt.
- OCCT/AIS kon de 10.000 gedeelde BREP-instances lokaal tonen, maar de exacte CAD-stack piekte op 576.1 MiB procesdelta; volledig projectgebruik blijft daarom een fallback.
- De geïnstalleerde VTK-moduleboom is lokaal 637.4 MiB; Windows onedir-delta moet apart worden gemeten.
- De OCP-moduleboom is lokaal 160.0 MiB, maar OCP is al onderdeel van de bestaande CWS/CadQuery-runtime.

## Metingen

| Backend | Nodes | Status | Scene build (ms) | First frame (ms) | Orbit p95 (ms) | Pick p95 (ms) | Pick juist | Clip (ms) | Peak RSS (MiB) | Procesdelta (MiB) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| occt_ais | 100 | passed | 3.42 | 37.72 | 22.45 | 0.018 | 100.0% | 13.25 | 525.8 | 414.9 |
| occt_ais | 1,000 | passed | 25.71 | 11.51 | 28.04 | 0.045 | 100.0% | 13.17 | 539.7 | 428.9 |
| occt_ais | 10,000 | passed | 755.11 | 41.91 | 45.47 | 0.050 | 100.0% | 63.82 | 686.8 | 576.1 |
| vtk_mesh | 100 | passed | 0.30 | 92.64 | 30.92 | 0.016 | 100.0% | 24.93 | 414.8 | 303.9 |
| vtk_mesh | 1,000 | passed | 2.57 | 114.76 | 32.58 | 0.036 | 100.0% | 26.12 | 417.8 | 307.1 |
| vtk_mesh | 10,000 | passed | 1.81 | 159.16 | 81.25 | 0.172 | 100.0% | 69.40 | 473.8 | 363.2 |

## Package-footprint in de lokale omgeving

| Module | Versie | Status | Grootte (MiB) | Rol |
|---|---|---|---:|---|
| `OCP` | `7.9.3.1.1` | measured_installed_tree | 160.0 | shared-existing-runtime |
| `vtkmodules` | `9.6.2` | measured_installed_tree | 637.4 | new-project-renderer-runtime |
| `PySide6` | `n.v.t.` | not_installed | 0.0 | shared-qt-shell-runtime |

## Open harde poorten

- [ ] PySide6 was in de offline Linuxruntime niet geïnstalleerd; de Qt-hostcode is gebouwd maar lokaal niet dynamisch uitgevoerd.
- [ ] PySide6/Qt-host daadwerkelijk uitvoeren in source, packaged en installed Windows-vormen.
- [ ] Afzonderlijke PyInstaller onedir-grootte en native runtimebetrouwbaarheid voor OCCT- en VTK-spikes meten.
- [ ] Dezelfde keuze opnieuw toetsen op de echte Tekla-projectscene en het complexe 11881 STEP-part.
- [ ] GPU/driver fallback op Windows 10/11 valideren.

## Interpretatie

De lokale metingen gebruiken één gedeelde boxgeometrie en stabiele instances. Ze bewijzen renderer-overhead, picking, clipping en capture; ze bewijzen nog niet de volledige Tekla-projectscene, exact source-BREP-isolatie of een Windows-installer. De definitieve V1-poort blijft daarom afhankelijk van de meegeleverde Windows CI-spike.
