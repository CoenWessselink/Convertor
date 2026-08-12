# CWS Convertor 0.7 — architectuur van de semantische projectimport

## Doel

Versie 0.7 voegt een semantische projectlaag toe boven op de bestaande, bewezen onderdeelconversie. IFC en STEP worden niet eerst gereduceerd tot één mesh. De importer bewaart productstructuur, bronidentiteit, placements, properties en relaties en materialiseert deze als actieve entiteiten in Canonical Project Model 2.1.

```text
IFC / STEP bronbytes
        │
        ├─ SHA-256 en veilige nulmeting
        │
        ▼
ISO-10303-21-grafiek
        │
        ├─ semantische bronstructuur
        ├─ geometry-subgraafhashes
        ├─ placements en relaties
        └─ properties/materialen
        ▼
Canonical Project Model 2.1
        │
        ├─ Assembly
        ├─ Part
        ├─ Fastener
        ├─ Weld
        └─ spatial tree + audit + provenance
        ▼
Classificatie / features / BOM / productie
(volgende, afzonderlijk gevalideerde fase)
```

## Gedeelde Part 21-kern

`cws_convertor/importers/p21.py` leest ISO-10303-21-bestanden eenmalig en biedt een veilige referentiegrafiek voor zowel IFC als STEP.

Eigenschappen:

- statement-splitsing buiten quoted strings;
- detectie van dubbele entity-ID's;
- lazy parsing en begrensde caches;
- veilige traversal met node- en dieptelimieten;
- recursieve referentieverzameling;
- ID-onafhankelijke Merkle-hash van geometrische subgrafen;
- expliciete cachevrijgave na grote imports;
- geen uitvoering van inhoud uit het bronbestand.

De Merkle-hash vervangt interne `#123`-verwijzingen door de hash van de verwezen inhoud. Gelijke geometrische grafen kunnen daardoor dezelfde brongeometriehash krijgen, ook wanneer entity-ID's verschillen.

## IFC-route

`cws_convertor/importers/ifc_project.py` ondersteunt de semantische projectlaag voor IFC2X3 en de overeenkomstige IFC4-entiteiten die dezelfde argumentstructuur gebruiken.

### Geïndexeerde informatie

- project, site, building en building storey;
- `IfcElementAssembly` en `IfcRelAggregates`;
- plaat-, balk-, kolom-, member-, footing-, slab- en proxyproducten;
- `IfcMechanicalFastener` en `IfcFastener`;
- `IfcRelContainedInSpatialStructure`;
- `IfcRelConnectsWithRealizingElements`;
- `IfcRelDefinesByProperties`, propertysets en quantities;
- `IfcRelAssociatesMaterial` en materiaalnamen;
- `IfcLocalPlacement`, `IfcAxis2Placement3D`, punten en richtingen;
- product representations en geometrische itemtypen.

### Placements

Local placements worden recursief samengesteld tot een globale, rechtsdraaiende 4×4-transformatie. Schaling, shear, niet-eindige waarden en linksdraaiende bases worden door het Project Model geweigerd. De globale projectpositie wordt niet in de placement-onafhankelijke geometry hash opgenomen.

### Tekla-relaties

Tekla assemblymarks, part positions, profielen, materiaal, lengte, massa, boutgegevens en lasrelaties worden uit bronvelden en propertysets gehaald. Iedere afgeleide waarde bevat bronherkomst en confidence. `IfcFastener` wordt alleen als las gematerialiseerd wanneer de bronsemantiek daarvoor bewijs bevat; een onbekend fastenerobject wordt niet stil als maakdeel behandeld.

## STEP-route

`cws_convertor/importers/step_project.py` materialiseert AP203/AP214/AP242-producten en occurrences.

De importer leest onder meer:

- `PRODUCT` en `PRODUCT_DEFINITION`;
- product-definition relationships en assembly usage occurrences;
- shape-definition representations;
- BREP- en surface-modelroots;
- occurrence placementrelaties;
- productnamen, IDs en beschrijvingen.

De importer kiest drie aantoonbare routes:

- expliciete occurrences en productrelaties → `A_semantic_structure`;
- één of meer topologische solid-roots zonder betrouwbare boom → `B_separate_solids`;
- geen betrouwbare solid-root → `C_fused_review`.

Route C materialiseert alleen werkelijk aanwezige productrecords en maakt geen geometrie of assemblystructuur bij. De importer splitst nooit op basis van een bestandsnaam. Eén product plus één solid resulteert in exact één projectonderdeel. Bij grote STEP-modellen wordt zware, tweede profielherkenning uitgesteld; de Part 21-structuur en geometry-subgraafhash blijven wel volledig beschikbaar.

## Transactionele projectservice

`ProjectSession.semantic_import_sources()`:

1. controleert alle bronbytes opnieuw op SHA-256;
2. maakt een geïsoleerde kopie van het project;
3. verwijdert een eerdere materialisatie van dezelfde bron;
4. importeert alle geselecteerde bronnen;
5. valideert het volledige relatiegraph;
6. vervangt pas daarna het actieve project.

Bij iedere fout blijven het actieve geheugenmodel en het bestaande `.cwscproj` ongewijzigd. Herimport is idempotent: stabiele bronidentiteit levert dezelfde interne IDs en hashes op.

Dezelfde grens ondersteunt coöperatief annuleren. De GUI zet een thread-safe annuleringsevent; parser, importer en service controleren dit op begrensde tussenpunten. Een annulering commit niets en laat het actieve project ongewijzigd. Een latere herstart voert de idempotente bronimport opnieuw uit. Er wordt nog geen half-afgemaakt tussenbestand als persistent "resume" verkocht.

## Projectopslag 2.1

Het `.cwscproj`-pakket bevat een SQLite-snapshot, manifest en optioneel de exacte bronbestanden. Het manifest bewaart:

- semantic/project SHA-256;
- content SHA-256;
- revision-content SHA-256;
- manufacturing-state SHA-256;
- entryhashes, groottes en CRC-controle;
- entitycounts en broncounts.

Schema 2.0 wordt expliciet naar 2.1 gemigreerd. Toekomstige schema's zoals 2.9 en onbekende major-versies worden niet stil als compatibel of schrijfbaar behandeld.

## Productiegate

Semantische import is geen productievrijgave. Externe IFC- en STEP-parts blijven op `review_required`, `nc1_eligible = false` en `export_status = blocked` totdat profiel-, feature-, materiaal- en roundtripvalidatie per onderdeel zijn afgerond.

AI kan later classificatievoorstellen doen, maar verandert geen geometrie en schrijft geen NC1, STEP, IFC of machinecode zonder deterministische validatie.

## Bekende grenzen van 0.7

- geen volledige maakdeel/inkoopdeel-classificatie;
- geen productiefeatureherkenning voor alle externe BREP/CSG-varianten;
- geen vrijgegeven complete-model-BOM;
- geen revisievergelijking en deduplicatie-interface;
- geen optimalisatie- of machinejobuitvoer;
- nog geen native Windows-build in de huidige Linux-validatieomgeving.
