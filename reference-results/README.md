# SteelConverter Reference Results

Deze map bevat expected-result bestanden voor de golden reference models.

## Bestandsnaam

Gebruik per model een bestand met de suffix `.expected.json`, bijvoorbeeld:

```text
reference-results/STEP/step-hea200-basic.expected.json
reference-results/IFC/ifc-frame-assembly.expected.json
reference-results/DSTV/dstv-plate-holes.expected.json
```

Voor vertrouwelijke lokale modellen gebruik je dezelfde structuur in `reference-results-local/`. Die map wordt niet naar GitHub gepusht.

## Validatiestatus

- `validated`: waarden zijn betrouwbaar vastgesteld en worden automatisch vergeleken.
- `manual_validation_required`: het model is geanalyseerd, maar de waarden zijn nog niet betrouwbaar genoeg om als regressiebaseline te dienen.

## Vergelijkingstypen

- `comparison.exact`: exacte waarden, zoals formaat, aantallen, profielcodes en operations.
- `comparison.tolerance`: numerieke waarden met tolerantie, zoals lengte, volume, gewicht en oppervlakte.
- `comparison.metadata`: export-afhankelijke of informatieve waarden, zoals bestandsnaam, exporter, datum of niet-stabiele labels.
- `comparison.performance`: grenzen voor parse-tijd, totale analysetijd en geheugengroei.

## Voorbeeld

```json
{
  "schemaVersion": 1,
  "model": {
    "id": "dstv-hea200-basic",
    "path": "reference-models/DSTV/hea200-basic.nc1",
    "format": "DSTV",
    "confidential": false
  },
  "validation": {
    "status": "manual_validation_required",
    "validatedBy": "",
    "validatedAt": "",
    "notes": "Parserobservatie moet nog worden vergeleken met het gevalideerde bronmodel."
  },
  "comparison": {
    "exact": {
      "source.format": "DSTV",
      "model.profile": "HEA200",
      "model.operations": [
        { "type": "holes", "count": 4 },
        { "type": "cuts", "count": 1 }
      ]
    },
    "tolerance": {
      "model.dimensions.length": { "expected": 6000, "tolerance": 0.1, "unit": "mm" }
    },
    "metadata": {
      "source.filename": {
        "comparison": "informational",
        "note": "Bestandsnaam kan per export verschillen."
      }
    },
    "performance": {
      "maxParseMs": 1000,
      "maxTotalMs": 1500,
      "maxHeapDeltaMb": 128
    }
  }
}
```
