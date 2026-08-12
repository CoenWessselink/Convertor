# Implementatiestatus CWS Convertor 0.7.0-alpha

## Gereed en gevalideerd

| Onderdeel | Status | Bewijs |
|---|---|---|
| CWS-productnaam en versie | Gereed | GUI, CLI, projectmanifest en buildconfiguratie |
| Canonical Project Model 2.1 | Gereed | serialisatie-, relatie-, hash- en migratietests |
| Part 21-grafiekkern | Gereed | parser-, cycle-, limit- en Merkle-hashtests |
| Semantische IFC-import | Gereed binnen beschreven scope | echt Tekla IFC2X3-model |
| Semantische STEP-import | Gereed binnen beschreven scope | drie echte AP242-modellen |
| STEP-route C zonder betrouwbare solid-root | Gereed | synthetische AP242-reviewtest zonder verzonnen geometrie |
| Assemblies, parts, fasteners, welds | Gereed | 6.159 IFC-objecten gematerialiseerd |
| Local/global placements | Gereed | transformvalidatie en bronherkomst |
| Properties en materialen | Gereed | MLO4/LO4, STRIP5*120, S235JR, lengte en massa |
| Stable IDs en hashes | Gereed | herimport en project reopen |
| Transactionele import | Gereed | rollbacktests en bronhashcontrole |
| Coöperatief annuleren | Gereed | parser-/servicecancellation en volledige rollback |
| `.cwscproj` met embedded bronnen | Gereed | ZIP, SQLite, hashes, extractie en CRC |
| CLI-projectimport en lijsten | Gereed | command-contracttests |
| Project/Productie-GUI | Gereed voor fase 2 | echte projectdata, voortgang en productiegate |
| Oude NC1/STEP/IFC-kern | Behouden | 24/24, 19/19 en 8/8 focusroundtrips |
| PDF/AI-kern | Behouden | 24/24, 19/19, 2/2, 1/1 en 11/11 veiligheidstests |

## Echte referentieresultaten

### Tekla IFC2X3

- assemblies: 353;
- parts: 2.429;
- mechanische fasteners: 723;
- lasobjecten: 2.654;
- totaal actieve projectentiteiten uit de IFC: 6.159;
- `IfcRelAggregates`: 356;
- `MLO4`: 4 assembly-instanties;
- gekoppelde `LO4`-parts: 4;
- Ø14-fasteners/gatinformatie: 4;
- verbonden lassen: 2.654;
- herhaalde marks: LA1 71×, A1 37×, MP1 18×, MP2 16×.

De vier LO4-parts behouden profiel `STRIP5*120`, materiaal `S235JR`, lengte 160 mm en massa 0,62 kg. Hun globale placements verschillen, maar geometry- en manufacturing hashes zijn gelijk.

### AP242 STEP

Ieder van de drie aangeleverde STEP-bestanden blijft:

- één product;
- één BREP-solid;
- één projectonderdeel;
- nul fictieve assemblies.

`2x voetplaat hoog.step` wordt niet op basis van de naam gesplitst.

Een AP242-bron zonder aantoonbare BREP-/solid-root volgt route `C_fused_review`. Alleen werkelijk aanwezige productrecords worden als reviewobject gematerialiseerd; CWS Convertor verzint geen solid, occurrence, assembly of opsplitsing.

## Bewust nog geblokkeerd

| Onderdeel | Reden |
|---|---|
| Complete-model NC1-export | externe features en productiezijden nog niet per part gevalideerd |
| BOM-vrijgave | classificatie maakdeel/inkoopdeel/niet-staal volgt in fase 3 |
| Geometrische deduplicatie-interface | hashes aanwezig, gebruikersworkflow volgt |
| Revisievergelijking | nog niet gebouwd |
| Handelslengte- en plaatoptimalisatie | komt na BOM en classificatie |
| Machinejobs | geen gevalideerde capability/postprocessorlaag |
| Windows installer-EXE | buildconfiguratie aanwezig, native build en schone-pc-test ontbreken |

## Validatiesamenvatting

- semantische fase: 82/82 controles;
- NC1 → STEP: 24/24;
- STEP → NC1: 19/19;
- NC1 → IFC → STEP → NC1: 4/4;
- STEP → IFC → NC1 → STEP: 4/4;
- NC1 → Trusted PDF → NC1: 24/24;
- STEP → Trusted PDF → STEP: 19/19;
- Trusted PDF → IFC focus: 2/2;
- synthetische LO4-keten: 1/1;
- AI/integriteit/negatieve tests: 11/11.

De oorspronkelijke binaire LO4-PDF was in deze runtime niet lokaal beschikbaar; die specifieke bron-PDF is daarom nog geen vrijgegeven regressietest.

## Gemeten performance van de referentieset

In de huidige Linuxomgeving duurde de semantische materialisatie van het Tekla IFC-model plus drie STEP-modellen **14,20 seconden**. Het atomisch opslaan, intern verifiëren en opnieuw openen van het `.cwscproj` met vier embedded bronnen duurde samen **13,01 seconden**. De zwaarste STEP-referentie `11881` doorliep de afzonderlijke prestatiepoort in **5,84 seconden** met **840,51 MB piek-RSS**; de vrijgavegrenzen zijn 120 seconden en 1.536 MB RSS. De exacte releasewaarden staan in `large_step_performance.json`. Dit zijn ontwikkelmetingen en nog geen Windows-SLA.
