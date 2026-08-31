# M0 Architecture Map - Manufacturing Geometry Interpreter

Status: `M0_COMPLETE`

Datum: 2026-08-30

## Canonieke keten

```text
IFC / STEP / NC1 / PDF
        |
        v
Semantic importers + immutable SourceIdentity / SourceFileRecord
        |
        v
ProjectModel 2.5 <-> ProjectSession <-> ProjectStorage
        |
        +--> source geometry locator / exact source-BREP isolation
        |
        +--> Part Workbench reviewed manufacturing interpretation
        |
        +--> canonical_rebuild (OCCT/CadQuery BREP)
        |
        +--> exact comparison + format roundtrips
        |
        +--> manufacturing faces/contact/marks/capability
        |
        +--> fail-closed production release
        |
        +--> SteelModelSnapshot read adapter
                    |
                    v
             Viewer host boundary
```

## Eigenaarschap

| Verantwoordelijkheid | Bestaande eigenaar | M0-besluit |
|---|---|---|
| Persistente productwaarheid | `cws_convertor.project.model.ProjectModel` | Behouden als enige persistente waarheid. |
| Transactie- en sessiegrens | `cws_convertor.project.service.ProjectSession` | Behouden; alle toekomstige interpreter-mutaties lopen via deze grens. |
| SteelModel-contract | `cws_convertor.steel_model.contracts.SteelModelSnapshot` | Alleen immutable read/handover-contract; geen tweede projectmodel. |
| Tolerantiebeleid | `cws_convertor.steel_model.tolerances.TolerancePolicy` | Uitbouwen tot enige beleidsbron; lokale constanten worden later adapters. |
| Bronidentiteit en provenance | `SourceIdentity`, `SourceFileRecord`, field provenance | Behouden en verplicht doorgeven aan elk voorstel, bewijs en rebuildresultaat. |
| Bron-BREP | Source locators plus `cws_viewer.exact.source_isolation` | Algoritmen hergebruiken; in M2 achter een applicatie-eigen service plaatsen. |
| Canonieke BREP | `cws_convertor.project.canonical_rebuild` | Behouden en uitbreiden; geen nieuwe BREP-engine. |
| Exacte vergelijking | `canonical_rebuild.compare_source_metrics` en `cws_viewer.exact.compare` | Consolideren achter een service met `TolerancePolicy`. |
| Profielcatalogus | `profile_database.ProfileDatabase` | Behouden als enige profielbron; geen tweede catalogus. |
| Feature-evidence | `cws_viewer.exact.catalog` plus Part Workbench | Hergebruiken als bewijs/voorstel, niet automatisch als productiefeit. |
| Manufacturing-afleiding | `cws_convertor.manufacturing.*` | Behouden voor faces, contact, marks, capability en neutral jobs. |
| Productievrijgave | `cws_convertor.production_export.readiness/release` | Ongewijzigd fail-closed houden. |
| Viewer | `cws_viewer` via `steel_model.viewer_boundary` | Alleen presentatie/interactie; geen autoritatieve geometriewijziging. |

## Niet toegestaan

- Geen tweede `ProjectModel`, `ProjectSession`, `SteelModel`, profielendatabase of identiteitssysteem.
- Geen aparte geometriewaarheid naast source BREP, reviewed workbench state en canonical BREP.
- Geen productie-vrijgave op basis van displaymesh, heuristische profielmatch of onbewezen featurevoorstel.
- Geen viewerobjecten in persistente projectcontracten.
- Geen stille fallback van exact naar approximatief.

## M0-conclusie

De repository heeft de benodigde fundering, maar nog geen algemene manufacturing geometry interpreter. De uitbreiding moet een orchestrerende applicatieservice worden boven de bestaande eigenaren, niet een nieuwe verticale stack.
