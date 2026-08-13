# Golden reference regression

`tests/reference_models_smoke.py` ontdekt modellen en expected-results in zowel
de repository als de optionele lokale vertrouwelijke mappen.

```powershell
.\.venv\Scripts\python.exe tests\reference_models_smoke.py
```

Extra roots kunnen met puntkomma-gescheiden absolute paden worden toegevoegd:

```powershell
$env:CWS_REFERENCE_MODEL_ROOTS = 'D:\benchmarks\models'
$env:CWS_REFERENCE_RESULT_ROOTS = 'D:\benchmarks\results'
```

Golden bestanden worden door de test alleen gelezen. Een
`manual_validation_required` baseline wordt gekoppeld en geteld, maar nooit
inhoudelijk als correcte verwachte uitkomst gebruikt.
