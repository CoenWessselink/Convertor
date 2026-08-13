# CWS Convertor reference models

Deze map bevat uitsluitend niet-vertrouwelijke golden reference files.

## Structuur

- `STEP/` voor gevalideerde `.step` en `.stp` modellen;
- `IFC/` voor gevalideerde `.ifc` modellen;
- `DSTV/` voor gevalideerde `.nc` en `.nc1` modellen.

Wijzig of verwijder een bestand in deze map nooit zonder expliciete toestemming
van de eigenaar. Ieder model moet een expected-result in `reference-results/`
hebben. Zet de status pas op `validated` wanneer de verwachte waarden betrouwbaar
zijn vastgesteld. Gebruik anders `manual_validation_required`.

Vertrouwelijke modellen blijven in `reference-models-local/` met dezelfde
substructuur. Die map wordt door Git genegeerd.
