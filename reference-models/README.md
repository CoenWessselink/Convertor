# SteelConverter Reference Models

Deze map bevat golden reference files voor SteelConverter.

## Structuur

- `STEP/` voor gevalideerde `.step` en `.stp` modellen.
- `IFC/` voor gevalideerde `.ifc` modellen.
- `DSTV/` voor gevalideerde `.nc` en `.nc1` modellen.

## Regels

1. Bestanden in `reference-models/` zijn golden reference files.
2. Wijzig of verwijder deze bestanden alleen na expliciete toestemming van de eigenaar.
3. Voeg bij ieder model een expected-result bestand toe in `reference-results/`.
4. Zet een model alleen op `validated` wanneer de verwachte uitkomsten betrouwbaar zijn vastgesteld.
5. Markeer twijfelgevallen als `manual_validation_required`; verzin geen waarden.

## Vertrouwelijke Modellen

Vertrouwelijke modellen blijven lokaal in `reference-models-local/` met dezelfde substructuur:

- `reference-models-local/STEP/`
- `reference-models-local/IFC/`
- `reference-models-local/DSTV/`

Deze lokale map staat in `.gitignore` en wordt niet naar GitHub gepusht. Bijbehorende lokale expected-results horen in `reference-results-local/`.

## Workflow

1. Plaats het model in de juiste map.
2. Run `npm run reference:analyze -- --write`.
3. Controleer het gegenereerde expected-result bestand handmatig.
4. Vul betrouwbare waarden aan en zet `validation.status` pas daarna op `validated`.
5. Run `npm run test:regression`.
