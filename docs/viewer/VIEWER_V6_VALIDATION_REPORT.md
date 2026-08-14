# CWS Viewer V6 — validatierapport

## Primaire bewijsbestanden

- `validation/viewer_v6/VIEWER_V6_VALIDATION_RESULTS.json`
- `validation/viewer_v6/VIEWER_V6_ACCEPTANCE_MATRIX.csv`
- `validation/viewer_v6/VIEWER_V6_SUBSHAPE_INVENTORY.csv`
- `validation/viewer_v6/VIEWER_V6_VALIDATION_REPORT.md`
- `validation/viewer_v6/V6_SCRIBING_REVIEW.json`
- `validation/viewer_v6_full_smokes/VIEWER_V6_FULL_SMOKE_SUMMARY.json`

## Kernresultaat

| Controle | Resultaat |
|---|---|
| P1811 exact source/canonical | PASS; max. afwijking circa `7,94e-15 mm` |
| P1811 Ø18→Ø20 | BLOCKED; max. afwijking `1,0 mm` |
| D20 exact canonical rebuild | PASS |
| HEA140 exact source-BREP selectie | PASS binnen source-selection scope |
| True R13,5 arcs | PASS |
| Analytisch through slot | PASS |
| Gesloten polylinecontour | PASS |
| Ambiguous multi-solid | BLOCKED |
| Native OCCT stable face pick | PASS |
| Scribing contactlijnen | 4 exacte voorstellen; 1 bevestigd; target BREP ongewijzigd |
| P1811 STEP/NC1/IFC/Trusted PDF | 4/4 PASS |
| Asymmetrische plaat STEP/NC1/IFC/Trusted PDF | 4/4 PASS |
| Viewer productie-PDF-release | expliciet NIET toegestaan |

Alle twintig V6-acceptatiepoorten zijn geslaagd.

## Volledige regressie

- beschikbare smoke-scripts: **67**;
- geslaagd: **67**;
- mislukt: **0**;
- time-outs: **0**;
- niet uitgevoerd: **0**;
- expliciete individuele skips: **2**.

De twee skips komen uit de bestaande P1811-handoverfixturecontroles in `pdf_review_smoke.py`. Die specifieke historische externe binaire fixture is niet aanwezig en wordt niet stilzwijgend vervangen door de nieuwe V6-testdata.

De historische V2 10k software-renderingtest gaf in één geïsoleerde Linux-batch een p95-outlier van 107,846 ms tegenover de 100 ms-poort. De ongewijzigde test is direct opnieuw uitgevoerd in de normale VTK-offscreenomgeving en geslaagd. Dit is vastgelegd in `VIEWER_V6_PERFORMANCE_RERUN_NOTE.md`; het is geen Windows-GPU-garantie.

## Evidence en toleranties

Geometrie wordt semantisch en geometrisch vergeleken, niet byte-voor-byte. Volume, oppervlak, topologie, hoofdmaten, echte edge-samples en feature sets worden gecontroleerd. Displaytessellatie wordt op een afgeleide kopie uitgevoerd en kan exact BREP-evidence niet wijzigen.

## Platformgrens

Lokale Linux OCCT-tests draaien via Xvfb. PySide6 en IfcOpenShell zijn niet als lokale dynamische desktopstack geïnstalleerd; de converter-owned IFC-route is lokaal wel gevalideerd. De echte source-, packaged- en portable Windows-poort wordt door GitHub Actions afgedwongen en is nog niet uitgevoerd.
