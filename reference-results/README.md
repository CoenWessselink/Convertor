# CWS Convertor reference results

Ieder golden reference model krijgt een `.expected.json`-bestand in de
overeenkomstige map. Lokale vertrouwelijke resultaten horen in
`reference-results-local/` en worden niet naar GitHub gepusht.

## Status

- `validated`: betrouwbare waarden; automatisch inhoudelijk vergelijken.
- `manual_validation_required`: alleen catalogus en koppeling controleren;
  verwachte waarden niet als waarheid behandelen.

## Vergelijking

- `comparison.exact`: exacte aantallen, typen, profielen en operations;
- `comparison.tolerance`: numerieke waarden met expliciete tolerantie;
- `comparison.metadata`: informatieve of exportafhankelijke metadata;
- `comparison.performance`: parse-, totaal- en geheugengrenzen.

De regressietest meldt bij een afwijking het model, de eigenschap, de verwachte
waarde, de gevonden waarde en de vermoedelijke oorzaak.
