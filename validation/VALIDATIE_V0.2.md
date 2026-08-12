# Validatie NC1 ↔ STEP Converter v0.2

## Doel

Versie 0.2 voegt STEP → NC1 voor standaardprofielen, een profielendatabase en een visuele links/rechtsvergelijking toe. Deze validatie controleert de nieuwe conversielaag op de aangeleverde bestanden en op aanvullende profielgevallen.

De controles zijn geometrisch en regressiegericht. Zij vervangen geen machinespecifieke productievrijgave.

## Gebruikte set

- 24 aangeleverde DSTV/NC1-bestanden;
- 19 aangeleverde STEP-referentiebestanden;
- 13 platen;
- 5 HEA-profielen;
- 1 massief rondprofiel;
- 4 hoeklijnen en 1 koker zonder onafhankelijke STEP-referentie;
- aanvullende synthetische U- en ronde-buisproef.

## Samenvatting

| Controle | Resultaat |
|---|---:|
| NC1 → STEP | 24 van 24 geslaagd |
| NC1 → STEP met onafhankelijke STEP-referentie | 19 paren |
| Grootste absolute volumeafwijking t.o.v. aangeleverde STEP-referentie | 0,008684% |
| Aangeleverde STEP → NC1 | 19 van 19 geslaagd |
| Daarvan platen | 13 |
| Daarvan profielen | 6 |
| Grootste absolute volumeafwijking na STEP → NC1-heropbouw | 0,000657% |
| Grootste absolute oppervlakafwijking na STEP → NC1-heropbouw | 0,000741% |
| Aanvullende L-/koker-reverse-tests | 5 van 5 geslaagd |
| Synthetische U-/CHS-tests | 2 van 2 geslaagd |
| GUI-starttest | geslaagd |
| Visuele vergelijkingsviewer geladen | geslaagd |

## NC1 → STEP

Alle 24 aangeleverde NC1-bestanden zijn met de v0.2-laag naar STEP geconverteerd. Voor de 19 onderdelen waarvoor een aangeleverd STEP-model beschikbaar was, bedroeg de grootste absolute volumeafwijking **0,0086836%**.

Deze afwijking komt overeen met de bekende kleine verschillen in lokale radius-/contourdetails van enkele HEA-onderdelen. De volledige resultaten staan in:

- `v0.2_nc1_to_step.csv`;
- `v0.2_generated_step/`.

## STEP → NC1 — aangeleverde modellen

Alle 19 aangeleverde STEP-bestanden zijn naar NC1 geconverteerd en vervolgens direct opnieuw als 3D-solid opgebouwd.

| Soort | Aantal | Resultaat |
|---|---:|---|
| Platen | 13 | alle geslaagd |
| HEA140/HEA160 | 5 | alle geslaagd |
| Massief rond D20 | 1 | geslaagd |

De grootste absolute volumeafwijking binnen deze route was **0,0006573%**. De grootste absolute afwijking in berekend oppervlak was **0,0007411%**.

De volledige resultaten staan in:

- `v0.2_step_to_nc1.csv`;
- `v0.2_generated_nc1/`.

## Aanvullende profieltests

Voor de vier hoeklijnen en één koker was geen onafhankelijk STEP-referentiemodel aangeleverd. Daarom is eerst vanuit de oorspronkelijke NC1 een STEP-solid gemaakt. Dat STEP-model is daarna door de nieuwe STEP → NC1-profielherkenning terugvertaald.

| Onderdeel | Herkend profiel | Type | Volumeafwijking |
|---|---|---:|---:|
| Pr1528 | K60/3 | M | circa 0% |
| Pr1657 | L60/6 | L | circa 0% |
| Pr1658 | L60/6 | L | circa 0% |
| Pr1706 | L100/10 | L | circa 0% |
| Pr1707 | L100/10 | L | circa 0% |

Dit toont aan dat de beide conversierichtingen voor deze intern consistente profieldefinities op elkaar aansluiten. Omdat de STEP-bron in deze proef door dezelfde geometriekern is gemaakt, is dit **geen onafhankelijke fabrikant- of CAD-validatie**.

Details staan in:

- `v0.2_additional_profile_reverse.csv`;
- `v0.2_reverse_profile_nc1/`.

## U-profiel en ronde buis

Er waren geen aangeleverde U-profiel- of CHS-referentiebestanden. Daarom zijn twee synthetische modellen opgebouwd uit de profieldefinities in de database:

- `U100x50x8.5x6`;
- `CHS88.9x5`.

Beide modellen zijn automatisch herkend en naar NC1 teruggeschreven. De volumeafwijkingen lagen numeriek rond nul. Ook dit zijn interne consistentietests en geen onafhankelijke normtabellenvalidatie.

Details staan in `v0.2_synthetic_profiles.csv` en `v0.2_synthetic_profiles/`.

## Visuele vergelijking

De nieuwe viewer is geladen met:

- links: het aangeleverde STEP-model `Pr1293_1_KOLOM_HEA160.stp`;
- rechts: de uit dat STEP-model gegenereerde NC1-reconstructie.

Gemeten in de viewer:

- volume: 11.310.818,181 → 11.310.803,969 mm³;
- volumeverschil: −0,000126%;
- oppervlak: 2.651.558,818 → 2.651.557,813 mm²;
- omhullende hoofdmaten: 2918,17 × 160,00 × 152,00 mm aan beide zijden.

De viewer lijnt beide modellen alleen voor de presentatie op hun hoofdrichtingen uit. De bestanden zelf worden niet gewijzigd.

## Veiligheidscontroles

De STEP → NC1-route voert na het schrijven van het NC1-bestand een heropbouw uit. Afhankelijk van het profieltype gelden waarschuwing- en afkeurgrenzen. Bij ingeschakelde strikte controle wordt een NC1-bestand verwijderd wanneer de volumeafwijking de ingestelde harde grens overschrijdt.

Verder worden onder meer deze situaties geweigerd of als niet-ondersteund gemeld:

- meerdere STEP-solids;
- niet-prismatische of niet-herkenbare standaardprofielen;
- profiel niet aanwezig in de database;
- te lage profielconfidence;
- te grote afmetingen- of oppervlakafwijking;
- blinde pockets en andere niet-ondersteunde plaatbewerkingen;
- niet-ondersteunde DSTV-geometrieblokken.

## Conclusie

De v0.2-uitbreiding werkt op de volledige aangeleverde testset en ondersteunt daarnaast de nieuwe profielroute voor I, U/C, L, M/RHS/SHS, RU en RO/CHS via een profielendatabase. De links/rechtsviewer werkt met beide bestandsrichtingen.

Voor productie blijft controle in de bestaande DSTV/NC-viewer, postprocessor en machinesimulatie noodzakelijk.
