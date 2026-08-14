# SteelConverter / CWS Convertor requirements trace — V9 integratie

| Requirement | V9 status | Bewijs / grens |
|---|---|---|
| Eén Canonical Project/Part Model | Gereed | `IntegratedProjectWorkspace` gebruikt exact één ProjectSession/ProjectModel |
| Totaal IFC-/STEP-project bekijken | Geïntegreerde dataflow gereed; dynamische Windows-GUI open | scene 6.168 nodes / 5.809 renderbaar; V3/V4 rendererbewijs |
| Projectboom | Gereed | geïntegreerde Qt-workspace |
| Professionele eigenschappenlijst | Gereed als V8-model/Qt-contract | 52 velden, sort/filter/group/layout/export |
| Boom/grid/3D synchroon | Gereed als stable-ID contract en lokale tests | application selection bus / viewer bridge |
| Assemblies/parts/fasteners/welds | Gereed | echte referentiecounts en identity audit |
| Hide/show/isolate/ghost | Geïntegreerd | ViewerCore controller |
| Sections/clipping/explode | Geïntegreerd | `IntegratedViewerToolsPanel` en V9 display-tools smoke |
| Measurements en export | Geïntegreerd | stable anchors, JSON/CSV/PDF, checksums |
| Viewpoints / `.cwsview.json` | Gereed | workspace schema 1.1 |
| Exact Part Workbench | Geïntegreerd en evidence-gated | V6 workbench + V9 exact source gate |
| Productieassen/referentiezijden | Persisted/validated | Project Model 2.4 workbench state |
| Canonical rebuild | Gereed voor begrensde bewezen scope | plaat/profile/rondstaaf service |
| Algemene external IFC part-BREP isolation | Open / geblokkeerd | `CWS-V9-EXACT-IFC-BREP-ISOLATION-PENDING` |
| Multi-part STEP exact isolation | Open / geblokkeerd | `CWS-V9-EXACT-STEP-PART-ISOLATION-UNPROVEN` |
| Revisions/compare | Geïntegreerd | V7 engine en grid evidence |
| BOM/selection binding | Gereed | één BOM snapshot en stable-ID index |
| PDF feature highlighting | Gereed als application bridge | stable entity/feature IDs |
| Viewer mag productie vrijgeven | Verboden | readiness blijft format-specifiek |
| Windows installer zonder Python | Workflow gereed, uitvoering open | V9 Windows gate |
| CasADi packaged runtime | Hook/tests gereed, Windowsbewijs open | source/dist/portable/installed selftests |
| Trimble code/binaries hergebruiken | Niet gedaan | static UX/architecture reference only |
| Optimalisatie/nesting/machines | Niet in V9 | pas na external manufacturing geometry gate |
