# CWS Convertor 0.8.0-alpha-dev — Codex integration snapshot

**CWS Convertor** is een local-first desktopapplicatie en CLI voor veilige conversie en productievoorbereiding van:

- NC1/DSTV, STEP en IFC;
- Trusted Converter PDF en gecontroleerde externe tekeningen;
- hoeveelheden en Excel;
- complete IFC-/STEP-projectmodellen in één draagbaar `.cwscproj`-project.

Versie **0.8.0-alpha-dev** bouwt verder op de bewezen conversiekern en de
semantische IFC-/STEP-projectimport. De actuele projectstructuur gebruikt
**Project Model 2.4**.

De huidige `v0.8-codex-handover`-ontwikkeling gebruikt **Project Model 2.4**.
Daarin is de eerste Part Workbench-fundering aanwezig: een onveranderlijke
brongeometrieverwijzing, bewerkbare analytische revisies, rechterhandige
productie-assen, referentiezijden, contouren en bewerkingen, provenance,
blokkerende validatie, undo/redo en automatische artefactinvalidatie. De
interactieve analytische 3D/2D-editor is nu in de bestaande projecttab
geintegreerd. Exacte source-BREP/canonical-solidvergelijking en
productie-roundtrips zijn nog niet afgerond.

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
Canonical Project Model 2.4
          ↓
Assemblies / parts / fasteners / welds
          ↓
Classificatie + featurevalidatie + roundtrip
          ↓
BOM / productie-export / optimalisatie / machines
```

AI mag documentsemantiek, classificatievoorstellen, confidence en controlevragen leveren. AI schrijft geen ongecontroleerde geometrie, NC1 of machinecode. Kritische onzekerheid sluit de productiepoort.

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

De uitgebreidere onderdeeleditor, versleepbare eigenschappengrid en 3D-isolatie per part horen bij de volgende classificatie-/BOM-interfacefase.

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
CWS_Convertor_Setup_0.8.0-alpha-dev_x64.exe
CWS_Convertor_Portable_0.8.0-alpha-dev_x64.zip
SHA256SUMS.txt
```

De eindgebruiker heeft geen Python, pip, venv of terminal nodig. De Windows
workflow en Inno Setup-configuratie zijn bijgewerkt naar 0.8.0-alpha-dev. Een
artefact geldt pas als gebouwd nadat de native Windows CI-installatie-, CLI-,
projectopslag- en uninstallsmokes zijn geslaagd.

## Belangrijkste modules

```text
cws_convertor/importers/p21.py              gedeelde Part 21-grafiekkern
cws_convertor/importers/ifc_project.py      semantische IFC-projectimport
cws_convertor/importers/step_project.py     semantische STEP-projectimport
cws_convertor/importers/semantic.py         gedeeld resultaat-/importcontract
cws_convertor/project/semantic_import.py    broncontrole, purge, indexes en gate
cws_convertor/project/model.py              Canonical Project Model 2.4
cws_convertor/project/workbench.py          partrevisies, validatie en undo/redo
cws_convertor/ui/part_workbench.py          geintegreerde analytische Part Workbench
cws_convertor/project/storage.py            .cwscproj ZIP+SQLite-integriteit
cws_convertor/project/service.py            transactionele GUI/CLI-service
project_tab.py                              Project / Productie-interface
cli.py                                      conversie- en project-CLI
```

## Volgende bouwfase

De analytische Part Workbench is nu aangesloten op de echte project-/partselectie.
De UI bevat revisiecommando's, sorteerbare onderdelen, eigenschappen, validatie,
provenance, contouren, gaten en een gecombineerde 3D/2D-preview. De grijze 3D-vorm
is voorlopig uitsluitend de betrouwbare bronomhulling; exacte bron-BREP-isolatie
en canonical-solidvergelijking zijn nog niet gereed.

1. geselecteerde IFC/STEP-brongeometrie exact isoleren;
2. deterministische canonical-solid rebuild en bron/canonical-vergelijking;
3. featureselectie tussen grids, 2D en exacte 3D verder synchroniseren;
4. NC1/STEP/IFC/PDF-roundtripvalidatie per ondersteunde onderdeelklasse;
5. pas daarna per-part/per-merk productie-export vrijgeven.
