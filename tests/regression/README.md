# Regression Tests

Deze tests controleren SteelConverter tegen golden reference models.

## Commands

```bash
npm run reference:analyze
npm run reference:analyze -- --write
npm run test:regression
```

## Gedrag

- Elk model in `reference-models/` of `reference-models-local/` moet een `.expected.json` bestand hebben.
- `validated` expected-results worden automatisch vergeleken.
- `manual_validation_required` expected-results worden bewust overgeslagen totdat de waarden handmatig betrouwbaar zijn gemaakt.
- Failures melden model, eigenschap, verwachte waarde, gevonden waarde en vermoedelijke oorzaak.

## Lokale Vertrouwelijke Tests

Gebruik voor vertrouwelijke modellen:

```text
reference-models-local/STEP
reference-models-local/IFC
reference-models-local/DSTV
reference-results-local/STEP
reference-results-local/IFC
reference-results-local/DSTV
```

Deze paden staan in `.gitignore`.
