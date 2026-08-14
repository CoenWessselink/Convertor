# SteelConverter - CWS Convertor 0.8.3-beta-dev implementation snapshot

**SteelConverter** is de leidende en zichtbare productnaam. De huidige
compatibele executable-, installer-, project- en registeridentifiers blijven
voor versie 0.8.3-beta-dev bewust `CWS_Convertor`, zodat bestaande projecten,
scripts en upgrades blijven werken.

SteelConverter is een local-first productieomgeving voor veilige conversie en
productievoorbereiding van:

- NC1/DSTV, STEP en IFC;
- Trusted Converter PDF en gecontroleerde externe tekeningen;
- hoeveelheden en Excel;
- complete IFC-/STEP-projectmodellen in één draagbaar `.cwscproj`-project.

Versie **0.8.3-beta-dev** bouwt verder op de bewezen conversiekern en de
semantische IFC-/STEP-projectimport. De actuele projectstructuur gebruikt
**Project Model 2.5**.

De huidige ontwikkeling gebruikt **Project Model 2.5** en Part Workbench 1.1.
Daarin is de Part Workbench aanwezig met een onveranderlijke
brongeometrieverwijzing, bewerkbare analytische revisies, rechterhandige
productie-assen, referentiezijden, contouren en bewerkingen, provenance,
blokkerende validatie, undo/redo en automatische artefactinvalidatie. De
interactieve analytische 3D/2D-editor is nu in de bestaande projecttab
geintegreerd. Platen met analytische lijnen en bogen, custom doorsneden,
massief rond en exacte catalogusprofielen met ondersteunde doorgaande gaten
kunnen deterministisch als canonical solid worden opgebouwd. Betrouwbare per-part bronmetingen worden op
volume, oppervlakte, bbox, solidcount en geldigheid vergeleken en gehasht in het
project vastgelegd. Een productieonderdeel kan pas worden vrijgegeven nadat de
NC1-, STEP-, IFC- en Trusted-PDF-roundtrips samen zijn geslaagd.

De actuele productkoers en bouwvolgorde staan in:

- `docs/STEELCONVERTER_PRODUCT_FOUNDATION.md`;
- `docs/STEELCONVERTER_SUPERPROMPT.md`;
- `docs/MASTERPROMPT_TRACEABILITY.md`.

De bestaande Project Model- en Canonical Part-kern wordt daarin
compatibiliteitsbehoudend onderdeel van een projectbreed `SteelModel`. De eerste
nieuwe productpoort is een aantoonbaar betrouwbare viewer/importketen.

## Veiligheidsarchitectuur

```text
PDF / NC1 / STEP / IFC
          ↓
Canonical Part Model
          ↓
NC1 / STEP / IFC / PDF / Excel

Compleet IFC / STEP
          ↓
Geverifieerde Part 21-brongrafiek
          ↓
Canonical Project Model 2.5
          ↓
Assemblies / parts / fasteners / welds
          ↓
Classificatie + featurevalidatie + roundtrip
          ↓
BOM / productie-export / optimalisatie / machines
```

AI mag documentsemantiek, classificatievoorstellen, confidence en controlevragen leveren. AI schrijft geen ongecontroleerde geometrie, NC1 of machinecode. Kritische onzekerheid sluit de productiepoort.

## Nieuw in 0.8.3-beta-dev

- atomair productiepakket per onderdeel en merk, uitsluitend na actuele vrijgave;
- verse NC1-, STEP-, IFC- en Trusted-PDF-roundtrips bij iedere productie-export;
- technische parttekeningen, A3-merkoverzichten, labels en voorvertoningen;
- assembly STEP/IFC, NC/PDF-submappen, stuk-, inkoop-, bout-, las- en paklijsten;
- QR-identiteit, SHA-256, ingesloten assemblymanifest en `totaalrapport.json`;
- CLI- en Project/Productie-integratie met selectie en naamgevingssjabloon;
- DXF alleen voor aantoonbaar ondersteunde analytische plaatcontouren.

## Nieuw in 0.8.2-alpha-dev

- analytische bogen met expliciete richting, custom doorsneden en bewerkte
  catalogusprofielen in de deterministic canonical rebuild;
- verplichte NC1-, STEP-, IFC- en Trusted-PDF-export/herimportmatrix;
- exacte payloadvergelijking en tolerantiecontroles voor zichtgeometrie;
- hashgebonden rapporten en artefacten die bij iedere maakwijziging ongeldig worden;
- CLI-commando's `project-rebuild-canonical` en `project-validate-roundtrips`;
- Workbench-knoppen voor rebuild, roundtrips en gecontroleerde productievrijgave;
- expliciete migratie van Project Model 2.x/Workbench 1.0 naar schema 2.5/1.1.

## Nieuw in 0.7.0-alpha

### Semantische IFC2X3/IFC4-import

De dependency-light IFC-importer leest en materialiseert onder meer:

- `IfcProject`, site, building en storey-structuur;
- `IfcElementAssembly` en `IfcRelAggregates`;
- `IfcPlate`, `IfcBeam`, `IfcColumn`, `IfcMember`, `IfcFooting`, `IfcSlab` en proxies;
- `IfcMechanicalFastener` en Tekla-las-/fastenerobjecten;
- local/global placements;
- GlobalId, Name, Tag, ObjectType en bronnummers;
- propertysets, quantitysets en materiaalassociaties;
- assembly marks, part positions, profielen, materialen, lengten en massa’s;
- verbindingen tussen lassen/fasteners en onderdelen;
- stabiele interne IDs en bronherkomst per veld.

De bronhiërarchie wordt behouden. De importer reduceert het model niet eerst tot één mesh en verzint geen nieuwe assemblystructuur.

### Semantische STEP-import

De AP203/AP214/AP242-route leest:

- product- en product-definitionrecords;
- product occurrences en assembly usage relations;
- shape representations en BREP-roots;
- occurrence placements/transformaties;
- productnamen, IDs en referentieaanduidingen;
- placement-onafhankelijke geometriehashes.

Wanneer een bestand één product en één solid bevat, ontstaat exact één projectonderdeel. Een naam als `2x voetplaat hoog` is geen bewijs voor geometrische opsplitsing. Wanneer een STEP-bron geen aantoonbare solid-root bevat, kiest CWS Convertor route `C_fused_review`: alleen werkelijk aanwezige productrecords worden als reviewobject vastgelegd. De importer verzint dan geen solid, occurrence, assembly of opsplitsing.

### Part 21-grafiekkern

IFC en STEP delen één ISO-10303-21-parser met:

- lazy argument parsing;
- veilige referentiegrafieken;
- detectie van dubbele entity-ID’s;
- ID-onafhankelijke Merkle-hashes van geometrische subgrafen;
- begrensde grafiektraversal;
- expliciete cachevrijgave na grote imports.

### Transactionele projectimport

Semantische import is één atomaire projectbewerking:

1. alle bronbytes worden eerst opnieuw op SHA-256 gecontroleerd;
2. een geïsoleerde projectkopie wordt gematerialiseerd;
3. relaties en modelregels worden gevalideerd;
4. alleen een volledig geslaagde import vervangt de actieve projectsnapshot;
5. bij een fout blijft het bestaande project ongewijzigd.

Herimport verwijdert de oude bronentities en bouwt dezelfde stabiele IDs en hashes opnieuw op. De GUI-actie kan coöperatief worden geannuleerd; parser, importer en service controleren een thread-safe stopsein en rollen de volledige batch terug zonder half project of half opgeslagen bestand.

### Project / Productie-interface

Het bestaande tabblad heeft nu een echte actie **Semantisch importeren**. De interface toont:

- assembly-, onderdeel-, bout- en lascounts;
- gegroepeerde assemblymarks;
- importstrategie en schemas;
- bronbewijs en productiegate;
- achtergrondvoortgang tot op interne IFC-/STEP-importstappen;
- een actieve **Annuleren**-knop met volledige rollback;
- details van MLO4/LO4, STEP-producten en blokkades.

De 3D Viewer is nu gekoppeld aan opnieuw geverifieerde STEP-BREP-,
IFC-entiteitsmesh- en actuele canonical-BREP-resources. Onzekere of handmatig te
valideren bronselecties leveren geen geometrie op; meten, doorsneden en vergelijken
blijven afzonderlijk capability-gated.

## Bewezen referentie-import

### Tekla IFC2X3

| Gematerialiseerd object | Aantal |
|---|---:|
| Assemblies | 353 |
| Parts | 2.429 |
| Mechanische bevestigingsmiddelen | 723 |
| Lasobjecten | 2.654 |
| **Totaal** | **6.159** |

Bronklassen blijven aantoonbaar behouden:

| IFC-klasse | Aantal |
|---|---:|
| `IfcElementAssembly` | 353 |
| `IfcPlate` | 1.293 |
| `IfcBeam` | 707 |
| `IfcColumn` | 369 |
| `IfcMechanicalFastener` | 723 |
| `IfcFastener` | 2.654 |
| `IfcFooting` | 38 |
| `IfcBuildingElementProxy` | 19 |
| `IfcSlab` | 3 |

Daarnaast worden onder meer bewezen:

- vier `MLO4`-assembly-instanties;
- vier gekoppelde `LO4`-onderdelen;
- profiel `STRIP5*120`;
- materiaal `S235JR`;
- lengte 160 mm;
- massa 0,62 kg per LO4-part;
- vier Ø14-fasteners/gatobjecten;
- 2.654 verbonden lasobjecten;
- herhaalde marks `LA1` 71×, `A1` 37×, `MP1` 18× en `MP2` 16×.

### AP242 STEP

De drie echte referentiebestanden worden ieder geïmporteerd als:

- één product;
- één BREP-solid;
- één actief projectonderdeel;
- nul fictieve assemblies;
- route `B_separate_solids`.


## Gemeten fasevalidatie

De vrijgavevalidatie bevat **82/82 geslaagde controles**. In de huidige Linuxomgeving duurde de semantische materialisatie van het Tekla IFC-model plus drie STEP-modellen 14,20 seconden. Het atomisch opslaan, intern verifiëren en opnieuw openen van het projectpakket met vier ingesloten bronnen duurde 13,01 seconden. De afzonderlijke `11881`-prestatiepoort voltooide in 5,84 seconden bij 840,51 MB piek-RSS, binnen de ingestelde grenzen van 120 seconden en 1.536 MB. Dit zijn ontwikkelmetingen, geen Windows-SLA.

## Productiepoort in deze release

Semantische import betekent nog niet automatisch productiegeschiktheid. Externe IFC-/STEP-parts blijven op `review_required` en `nc1_eligible = false` totdat de volgende fase minimaal heeft afgerond:

- maakdeel/inkoopdeel/niet-staal-classificatie;
- profiel- en featureherkenning;
- lokale productiezijden en referenties;
- materiaalbevestiging;
- Canonical Model → NC1/STEP/IFC → Model-roundtrip;
- conflictcontrole op marks, geometry hash en manufacturing hash.

Complete-model BOM-, optimalisatie- en machine-uitvoer zijn daarom nog bewust geblokkeerd.

## Bestaande conversiekern behouden

De eerdere regressies blijven onderdeel van iedere build:

- NC1 → STEP: 24/24;
- STEP → NC1: 19/19;
- NC1 → IFC → STEP → NC1: 4/4;
- STEP → IFC → NC1 → STEP: 4/4;
- Trusted Converter PDF;
- externe vector-PDF-review;
- deterministische maatgrafiek;
- begrensde AI-laag;
- hoeveelheden en Excel.

## CLI

### Project aanmaken en bronnen registreren

```text
CWS_Convertor_CLI.exe project-new project.cwscproj --name "Mijn project"
CWS_Convertor_CLI.exe project-import-baseline project.cwscproj model.ifc model.step
```

### Semantisch materialiseren

```text
CWS_Convertor_CLI.exe project-import project.cwscproj --json
CWS_Convertor_CLI.exe project-tree project.cwscproj --json
CWS_Convertor_CLI.exe project-list-assemblies project.cwscproj --filter MLO4 --json
CWS_Convertor_CLI.exe project-list-parts project.cwscproj --filter LO4 --json
CWS_Convertor_CLI.exe project-export-parts project.cwscproj --output productie --format nc1,step,ifc,production_pdf,csv --json
CWS_Convertor_CLI.exe project-export-assemblies project.cwscproj --output productie --assembly-mark MLO4 --json
```

`project-import` gebruikt exitcode **2 / review required** wanneer de semantische import slaagt maar de productiegate terecht gesloten blijft. Dit is geen stil gedeeltelijk succes; het JSON-rapport bevat de blokkaderedenen per bron.

### Projectintegriteit

```text
CWS_Convertor_CLI.exe project-info project.cwscproj --json
CWS_Convertor_CLI.exe project-sources project.cwscproj --json
CWS_Convertor_CLI.exe project-verify project.cwscproj --json
CWS_Convertor_CLI.exe project-export-json project.cwscproj -o project-model.json
CWS_Convertor_CLI.exe project-extract-source project.cwscproj <source-id> -o bron.ifc
CWS_Convertor_CLI.exe project-recover project.cwscproj -o hersteld.cwscproj
CWS_Convertor_CLI.exe project-migrate oud.cwscproj -o nieuw.cwscproj
```

## Windows-release

De bijgewerkte buildstraat gebruikt Python 3.12 x64 op de **buildcomputer** en maakt:

```text
CWS_Convertor_Setup_0.8.3-beta-dev_x64.exe
CWS_Convertor_Portable_0.8.3-beta-dev_x64.zip
SHA256SUMS.txt
WINDOWS_RUNTIME_VALIDATION.md
```

De eindgebruiker heeft geen Python, pip, venv of terminal nodig. De Windows
workflow en Inno Setup-configuratie zijn bijgewerkt naar 0.8.3-beta-dev. Een
artefact geldt pas als gebouwd nadat native selftests en de echte GUI vanuit
`dist`, een schone portable extractie en de installatiemap zijn geslaagd zonder
Python op de child-`PATH`. Iedere pakketvorm maakt daarnaast een project en
voert een echte NC1-naar-STEP-conversie uit.

Workflow `31685684421` en artefact `9175668822` zijn ingetrokken als
releasebewijs: die controles startten de verpakte GUI/CAD-stack niet en misten
daardoor de CasADi-DLL-fout. Vanaf `0.8.1-alpha-dev` publiceert de build ook
ook de volledige runtimevalidatie. Productie-export blijft afzonderlijk
geblokkeerd zolang part-roundtrips of golden validatie niet aantoonbaar slagen.

## Belangrijkste modules

```text
cws_convertor/importers/p21.py              gedeelde Part 21-grafiekkern
cws_convertor/importers/ifc_project.py      semantische IFC-projectimport
cws_convertor/importers/step_project.py     semantische STEP-projectimport
cws_convertor/importers/semantic.py         gedeeld resultaat-/importcontract
cws_convertor/project/semantic_import.py    broncontrole, purge, indexes en gate
cws_convertor/project/source_geometry.py    geverifieerde part-bronselectie
cws_convertor/project/model.py              Canonical Project Model 2.5
cws_convertor/project/workbench.py          partrevisies, validatie en undo/redo
cws_convertor/project/canonical_rebuild.py  canonical solid en bronmeetvergelijking
cws_convertor/project/roundtrip.py          NC1/STEP/IFC/PDF export-herimportmatrix
cws_convertor/steel_model/contracts.py      SteelModel 1.0 read-only contract
cws_convertor/steel_model/adapter.py        Project Model 2.5 compatibility adapter
cws_convertor/steel_model/tolerances.py     central comparison policy
cws_convertor/steel_model/viewer_boundary.py controlled GPT-viewer handover contract
cws_convertor/viewer/workspace.py          verified viewer state and selection
cws_convertor/viewer/mesh_resources.py     hash-bound real mesh resources
cws_convertor/viewer/vtk_backend.py        off-screen VTK scene, camera and picking
cws_convertor/ui/project_viewer.py         integrated project viewer host UI
cws_convertor/ui/part_workbench.py          geintegreerde analytische Part Workbench
cws_convertor/project/storage.py            .cwscproj ZIP+SQLite-integriteit
cws_convertor/project/service.py            transactionele GUI/CLI-service
project_tab.py                              Project / Productie-interface
cli.py                                      conversie- en project-CLI
```

## Huidige bouwfase

De eerder uitgevoerde kernfasen 0-3 blijven geldig als technisch bewijs. De
voorwaartse roadmap gebruikt nu fasen A-F. Fase A is afgerond met SteelModel
1.0, centrale toleranties, compatibiliteitsidentiteit en het viewer-hostcontract.
Fase B is gestart. Batches 1-2 leveren de SteelModel-gebonden projectboom,
properties, validatie, Accuracy/Debug-status, selectie-synchronisatie,
hash-gebonden STEP/IFC/canonical meshes en een ingebouwde VTK/Tk-renderer.
Camera, picking en zichtbaarheidsfuncties zijn actief; meten, doorsneden en
vergelijken blijven bewust uit totdat hun eigen contracts zijn bewezen.

1. maak `source ID -> SteelModel ID -> viewer mesh ID` stabiel en controleerbaar;
2. bewijs units, transformaties, orientatie en toleranties op synthetische en
   eigenaar-gevalideerde referenties;
3. behoud de nu geteste synchronisatie van viewerselectie, modelboom,
   eigenschappen en validatieproblemen;
4. breid de nu gekoppelde echte projectmeshes uit naar progressief volledig-project
   laden en eigenaar-gevalideerde grote-modelmetingen;
5. behoud alle bestaande conversie-, Workbench-, roundtrip- en Windows-tests;
6. bouw pas daarna de productie-editor, volledige tekeningen, adapters en
   optimalisatie verder uit.
