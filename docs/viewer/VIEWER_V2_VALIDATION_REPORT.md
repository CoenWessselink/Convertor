# CWS Viewer V2 — validatierapport

**Status:** passed
**Viewer:** 0.3.0-dev0
**Platform:** Linux-6.18.35-x86_64-with-glibc2.41

## Acceptatiepoort

| Controle | Resultaat |
|---|---|
| `renderable_count_10k` | ✅ |
| `deterministic_scene_hash` | ✅ |
| `navigation_executed` | ✅ |
| `picking_p95_under_100_ms` | ✅ |
| `picking_100_percent` | ✅ |
| `hide_show` | ✅ |
| `isolate` | ✅ |
| `ghost_context` | ✅ |
| `stable_ids_after_reload` | ✅ |
| `screenshots_created` | ✅ |
| `screenshots_distinct` | ✅ |
| `screenshots_visual_content` | ✅ |

## Metingen

| Metriek | Waarde |
|---|---:|
| scene_build | 1401.889 ms |
| index_build | 926.367 ms |
| load_and_first_frame | 2752.482 ms |
| orbit_mean | 72.431 ms |
| orbit_p95 | 80.617 ms |
| pick_mean | 60.849 ms |
| pick_p95 | 72.665 ms |
| hide | 1520.674 ms |
| isolate | 34.548 ms |
| reload | 2553.546 ms |

## Scene

- Renderable nodes: **10,000**
- Assemblies: **100**
- Picking: **50/50**
- Scenehash: `c86d0fca379d2ac5c361e9df4def6f4cde1fc0d0faaebe63a93d64ea69c56d9a`
- Stable reload: **True**

## Open grenzen

- V2 rendert synthetische display-boxes; echte projectmeshresources volgen in V3.
- Exact source/canonical BREP en subshapepicking blijven gepland voor V6.
- PySide6 Qt-runtime is alleen via de Windows gate bewijsbaar wanneer lokaal niet geïnstalleerd.

## Volledige regressiebaseline

- **37/37 smoke-scripts geslaagd**.
- **0 mislukte scripts**.
- **2 expliciete skips** in `pdf_review_smoke.py`, beide omdat de echte P1811-handoverfixture niet in deze bronboom aanwezig is.
- De skips zijn niet als geslaagde echte-bestandstests gerekend.
- Alle V0-, V1-, converter-, project-, PDF/AI-, IFC/STEP-, BOM- en V2-smokes zijn onder Xvfb uitgevoerd waar een native window noodzakelijk was.

Zie `validation/viewer_v2/full_smokes/FULL_SMOKE_SUMMARY.json` en `.md` voor de volledige lijst en timings.

## Geheugen en runtimecontext

- RSS vóór de 10k-run: **113.281 MiB**.
- RSS na de 10k-run: **588.242 MiB**.
- Gemeten delta: **474.961 MiB**.
- VTK: **9.6.2**.
- OCP: **7.9.3.1.1**.
- Pillow: **12.3.0**.
- PySide6: **niet lokaal geïnstalleerd**.

Deze waarden zijn lokale Linux-/software-renderermetingen en geen gegarandeerde Windows-SLA.
