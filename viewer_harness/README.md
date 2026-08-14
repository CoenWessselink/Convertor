# CWS Viewer V0 harness

Deze harness test uitsluitend het viewercontract, sceneschema en statebeheer.
Hij is **geen grafische mock-up** en doet geen productieclaims. De grafische
OCCT/AIS- en meshbackendspikes volgen in fase V1 en worden op echte Windows-
metingen gekozen.

```bash
PYTHONPATH=. python viewer_harness/run_headless.py
PYTHONPATH=. python -m cws_viewer --self-test --json
PYTHONPATH=. python -m cws_viewer --diagnostics --deep-native --json
```

## Volledige V0-baseline

```bash
PYTHONPATH=. python viewer_harness/run_v0_baseline.py \
  --output validation/V0_BASELINE.json \
  --reference-root /pad/naar/reference_inputs
```

Rapporten kunnen direct naar een bestand worden geschreven:

```bash
python -m cws_viewer --self-test --deep-native --json --output viewer_selftest.json
python cli.py viewer-diagnostics --deep-native --json --output viewer_diagnostics.json
```
