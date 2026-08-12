# CWS Convertor 0.7 — levering en volgende bouwfase

## Deze levering

Versie 0.7.0-alpha levert de eerste echte complete-modelmaterialisatie. Het grote Tekla IFC-model en drie AP242 STEP-modellen worden als actieve Project Model-entiteiten opgeslagen. De bestaande onderdeelconversies en PDF/AI-laag blijven behouden.

De release bevat:

- volledige broncode en Git-historie;
- semantische IFC-/STEP-importers;
- Canonical Project Model 2.1;
- referentieproject met vier ingesloten bronbestanden;
- validatierapporten, ruwe JSON/CSV-resultaten en testlogs;
- GUI-screenshot;
- checksums en SBOM;
- Windows-build- en installerconfiguratie.

## Volgende fase: classificatie en BOM

De juiste volgende bouwvolgorde is:

1. een deterministische classificatiematrix voor maakdeel, inkoopdeel, bevestigingsmiddel, las/procesobject, niet-staal, referentie en onbekend;
2. profiel-, plaat- en materiaalnormalisatie met confidence en bronbewijs;
3. grouping op geometry hash en manufacturing hash, inclusief spiegelvarianten;
4. conflictcontrole: hetzelfde merk met verschillende manufacturing hashes;
5. part-BOM, assembly-BOM, fastenerlijst, lassenlijst en inkoop-BOM;
6. volledig herleidbare totalen voor aantal, lengte, massa en oppervlak;
7. Excel/CSV-export met status, bron-ID en blokkadereden;
8. pas daarna de uitgebreide eigenschappen-/onderdeeleditor en 3D-selectiesynchronisatie.

## Harde vrijgavepoort voor de volgende fase

Een BOM-regel mag alleen als productiegeschikt worden gemarkeerd wanneer:

- classificatie niet `unknown` is;
- materiaal en profiel voldoende betrouwbaar zijn;
- ieder source object exact eenmaal wordt geteld;
- assemblyrelaties kloppen;
- dezelfde mark niet meerdere manufacturing hashes verbergt;
- alle aantallen en totalen herleidbaar zijn;
- geen blocking issue openstaat.

AI mag classificatiesuggesties en controlevragen leveren. Definitieve geometrie, aantallen, hashes en vrijgave blijven deterministisch.
