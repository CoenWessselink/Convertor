# Implementatiestatus CWS Convertor 0.6.0-beta

## Doel van deze bouwfase

Versie 0.6.0-beta levert het technische fundament waarop de complete-modelmodule veilig kan worden gebouwd. De bestaande NC1/STEP/IFC/PDF-conversiekern is behouden. Nieuw zijn productidentiteit, het Canonical Project Model 2.0, het draagbare `.cwscproj`-formaat, deterministische bronintake, gedeelde GUI/CLI-projectservices en harde productiepoorten.

Deze release claimt nadrukkelijk **nog geen voltooide semantische complete-modelimport**. Een IFC- of STEP-bron wordt in deze fase exact geïnventariseerd en opgeslagen, maar assembly-, part-, fastener- en weld-entiteiten worden pas in fase 2 actief gematerialiseerd.

## Afgerond in deze fase

| Onderdeel | Status | Bewijs |
|---|---|---|
| CWS-productidentiteit | Gereed | GUI, CLI, build, installer en bestandstypen gebruiken `CWS Convertor` |
| Canonical Project Model 2.0 | Gereed als foundation | Project-, assembly-, part-, inkoop-, fastener-, weld-, voorraad-, operatie- en machine-entiteiten |
| Stabiele identiteit | Gereed | bron-ID, UUIDv5, geometry hash en manufacturing hash |
| Plaatsingen | Gereed als datalaag | rigide, orthogonale, rechterhandige `Transform3D`-validatie |
| `.cwscproj` ZIP+SQLite-opslag | Gereed | manifest, SQLite-snapshot, optionele bronnen en previews |
| Integriteitscontroles | Gereed | SHA-256, grootte, CRC, ZIP-padcontrole, archive-bomblimieten en SQLite-integriteit |
| Opslagveiligheid | Gereed | atomisch opslaan, backup, read-only-modus en expliciete migratie naar kopie |
| Revisies en audit | Gereed | inhoudshash, manufacturing-state-hash en auditregels |
| Autosave en herstel | Gereed | lichtgewicht autosave zonder telkens grote bronbestanden opnieuw in te pakken |
| Importstrategie A/B/C-nulmeting | Gereed | semantische structuur, losse solids en expliciete fused/ambiguous reviewroute |
| Vier echte referentiemodellen | Gereed als regressiebasis | één Tekla IFC2X3 en drie AP242 STEP-bestanden |
| Project / Productie GUI | Functioneel foundationscherm | projectboom, sorteerbaar bronraster, KPI's, details, validatie en achtergrondimport |
| Project-CLI | Functioneel | maken, toevoegen, inspecteren, verifiëren, exporteren, extraheren, herstellen en migreren |
| Achtergrondjobs | Functioneel | voortgang, annuleren, resultaat en foutstatus |
| Windows buildconfiguratie | Build-ready | Python 3.12, PyInstaller onedir, Inno Setup, installer- en uninstallsmoke |
| Dependency locks en SBOM | Gereed | runtime/build locks en SPDX-SBOM |
| Bestaande v0.5.1-conversiekern | Behouden | bestaande smokes blijven aanwezig en de volledige regressielog is groen |

## Uitgevoerde projecttests

| Testmodule | Resultaat |
|---|---:|
| `project_model_smoke.py` | 10/10 |
| `project_storage_smoke.py` | 8/8 |
| `project_baseline_smoke.py` | 4/4 |
| `project_cli_smoke.py` | 2/2 |
| `project_jobs_smoke.py` | 3/3 |
| `project_service_smoke.py` | 3/3 |
| `project_reference_files_smoke.py` | 3/3 |

De onafhankelijke phase-validation heeft de vier echte bronbestanden opnieuw geanalyseerd en **117 van 117 controles** doorstaan. Daarnaast is een volledige beschikbare regressierun uitgevoerd voor de bestaande geometrie-, conversie-, PDF-, AI-, review- en projectsmokes; die eindigde met `ALL TESTS PASSED`.

## Referentienulmeting

### Tekla IFC2X3

- 353 assemblies;
- 1.293 platen;
- 707 balk-/liggerobjecten;
- 369 kolomobjecten;
- 723 mechanische bevestigingsmiddelen;
- 2.654 overige fastener-/lasobjecten;
- 38 funderingsobjecten;
- 19 building-element proxies;
- 3 slabs;
- 356 aggregate-relaties;
- 6.159 producten en 744 geometrische solids in de nulmeting.

De bewijszoeker vindt tevens `MLO4`, `LO4`, `STRIP5*120`, `S235JR`, lengte 160 mm, circa 0,6 kg, diameter 14 mm en de herhaalde marks `LA1`, `A1`, `MP1` en `MP2`.

### AP242 STEP

Elk van de drie aangeleverde STEP-bestanden bevat één productrecord, één BREP-solid en geen assembly usage-relatie. Daarom blijft elk bestand in deze fase één bronproduct. De bestandsnaam `2x voetplaat hoog` leidt niet automatisch tot twee onderdelen.

## Productiepoort

De volgende regels zijn hard ingebouwd:

1. een baseline-analyse is geen semantische import;
2. een bron krijgt `semantic_import_pending` totdat de actieve projectentiteiten zijn opgebouwd en gevalideerd;
3. blokkerende `ValidationIssue`-objecten sluiten productie-export;
4. manufacturing hashes moeten bestaan en actueel zijn voordat productieartefacten kunnen worden vrijgegeven;
5. een mislukte batchregistratie mag het bestaande project niet wijzigen;
6. een onbekende of nieuwere projectschemaversie wordt niet stil herschreven.

## Bewust nog geblokkeerd

- IFC-relaties, placements, properties, materialen, bouten en lassen zijn nog niet als actieve ProjectModel-entiteiten gematerialiseerd.
- STEP-product occurrences en topologische solids zijn nog niet als actieve onderdelen geclassificeerd.
- Maakdeel/inkoopdeel/fastener/weld/niet-staal/onbekend is nog geen projectbrede classifier.
- BOM, part-/assembly-export, deduplicatie en revisievergelijking zijn nog niet productierijp.
- Optimalisatie, nesting, machinejobs en voorraad blijven buiten de vrijgegeven scope.
- Er is in deze Linuxomgeving geen native Windows-installer gebouwd of op een schone Windows-machine getest.

## Volgende fase

De eerstvolgende bouwfase is de semantische projectimport:

1. IFC Strategy A: ruimtelijke boom, assemblies, parts, relaties, placements, properties, materialen, fasteners en welds;
2. STEP Strategy A/B: product occurrences, shapes, losse solids en placements zonder fictieve assemblystructuur;
3. stabiele actieve assembly-/part-identiteit en het vullen van geometry/manufacturing hashes;
4. deterministische classificatie met AI alleen als traceerbaar voorstel;
5. BOM en veilige per-part/per-merk export als volgende vrijgavepoort.
