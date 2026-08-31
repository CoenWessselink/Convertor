# CWS Convertor queue completion matrix

Datum: 2026-08-31

| Opdracht / milestone | Verwacht resultaat | Gevonden implementatie | Relevante tests / evidence | Status |
|---|---|---|---|---|
| Fase 1 - evidence en een werkcontext | Een project-, selectie- en geometriecontext; viewer, workbench, conversie, tekening, export en BOM | De gedeelde U3/U4-context en fase-1 services zijn aanwezig | `validation/phases/PHASE_1_SOURCE_TEST_EVIDENCE.json`; fase-1 unified gates groen | COMPLETE |
| Fase 2 - engineering en manufacturing workflows | Productieworkflows, profile nesting, export scope en save/reopen gedrag | De bestaande fase-2 services en UI-routes zijn behouden en aan V5.1 gekoppeld | `validation/phases/PHASE_2_SOURCE_TEST_EVIDENCE.json`; `PHASE_2_UNIFIED_GATES = 15/15 PASS` | COMPLETE |
| Fase 3 - source acceptance en stabiliteit | Fase-3 gates inclusief soak en viewercorrespondentie | Fase-3 bronpoorten zijn volledig uitgevoerd | `validation/phases/PHASE_3_SOURCE_TEST_EVIDENCE.json`; 600 s soak; `PHASE_3_SOURCE_GATES = PASS` | COMPLETE |
| V5.1 hoofdstructuur | Exact `Project | Viewer | Productie | Controle | Uitvoer` | Hoofdnavigatie en routes zijn aangepast en regressiegetest | `tests/unified_ui_shell_u3_gui_smoke.py`; `tests/ui_v51_binding_contract_smoke.py` | COMPLETE |
| V5.1 schermbinding | 31 schermen: 25 visuele referenties en 6 supportsurfaces | Alle 31 scherm-ID's hebben een route en capture | `validation/ui_v5/runtime_windows/screen_coverage.json` | COMPLETE |
| V5.1 controlbinding | 226 verplichte controls, unieke `test_id`, geen dead/no-op binding | 226/226 vereist, 0 ontbrekend, 0 dubbel, 0 verkeerde labels, 0 action-binding failures | `validation/ui_v5/runtime_windows/missing_extra_control_report.json`; `control_action_results.json` | COMPLETE |
| V5.1 DPI | 100/125/150/200 procent zonder harde capturefouten | Alle DPI-captures uitgevoerd | `validation/ui_v5/runtime_windows/dpi_coverage.json` | COMPLETE |
| V5.1 visuele pixelparity | Menselijk goedgekeurde overeenkomst met alle 25 referentiebeelden | Screenshots en pixel-diff zijn gemaakt; menselijke review is nog niet vastgelegd | `validation/ui_v5/runtime_windows/visual_diff_report.json`; `CWS_UI_V5_1_RUNTIME_OVERVIEW.png` | PARTIAL |
| Viewer V15 navigatie en layout | Alle routes, controls en camera-interactie werkend | Drie acceptatietests groen; 43.4 controllerupdates/s | `tests/viewer_v15_layout_navigation_acceptance.py` | COMPLETE |
| Live Trimble Connect observable parity | Side-by-side bewijs op dezelfde modellen en camera's | Geen nieuwe onafhankelijke live Trimble-review in deze buildrun | Bestaande viewer evidence blijft beschikbaar, maar geen finale externe waarneming | NOT_PROVEN |
| One-folder runtime | Volledige Windows-runtime zonder externe Python | Nieuw gebouwd en packaged smoke groen | `validation/results/ui-v51-packaged/ui-v51-onedir-packaged-runtime.json` | COMPLETE |
| One-file runtime | Zelfstandige `.exe`, self-test en GUI-smoke | Nieuw gebouwd en beide tests groen in opgeschoonde runtimeomgeving | `onefile-selftest.json`; `onefile-gui-smoke.json` | COMPLETE |
| Fresh portable | Nieuwe ZIP uit de bewezen one-folder runtime | Verse extractie en packaged runtime smoke groen | `validation/results/ui-v51-packaged/ui-v51-portable-packaged-runtime.json` | COMPLETE |
| Installer | Stille install, packaged smoke, associaties en uninstall-cleanup | Installatie, runtime, associaties en cleanup groen | `ui-v51-installed-packaged-runtime.json`; `uninstall.log` | COMPLETE |
| Git history / checkpoint commits / release SHA | Reproduceerbare Git-bound release | Niet uitgevoerd; er is geen commit-ID verzonnen | Development snapshot `v51ui31`; source snapshot hashes in release manifest | NOT_PROVEN |
| Externe machine-transferkwalificatie | Geautoriseerde en geobserveerde machine-transfer | Externe machine- en transportkwalificatie ontbreekt | Productiegate blijft gesloten | BLOCKED / NOT_PROVEN |

## Conclusie

De V5.1 functionele binding, bronpoorten en Windows-pakketten zijn compleet en getest. Een globale `100% COMPLETE` claim is niet toegestaan zolang visuele menselijke goedkeuring, live Trimble-parity, Git-bound reproduceerbaarheid en externe machinekwalificatie ontbreken.
