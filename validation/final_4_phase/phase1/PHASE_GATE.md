# Fase 1 gate - Foundation, Viewer, Intake and State

Status: **PASS**  
Commit: `24fcd448365c8125cd9635d9db6eea8d68a68586`

## Opgeleverd

- Default Light V5.2 visual authority met optionele Engineering Dark voorkeur.
- Exacte hoofdnavigatie `Project | Viewer | Productie | Controle | Uitvoer`.
- Persistente theme-keuze en stabiele `ui_test_id`/`cws_product_control` identifiers.
- 317 actieve masterrequirements met bron, status, code-, test- en evidencevelden.
- Drie echte screenshots uit de Windows/Qt-bronruntime.
- Een actuele one-folderbuild en packaged-runtime smoke op dezelfde commit.

## Testresultaat

Alle Fase 1 source- en packaged-smokes zijn `PASS`; false-green-teller: `0`.

## Bewijs

- `01_project_start_light.png`
- `02_viewer_loaded_light.png`
- `03_project_overview_light.png`
- `packaged/phase1-24fcd44-packaged-runtime.json`

## Open eindacceptatie-eisen

- `FAIL`: first-ever cold HVPC exact geometry haalt de eerder gevraagde 3-5 seconden nog niet; de bestaande meting is circa 71 seconden. Warm/same-session is circa 0,25 seconde.
- `NOT_TESTED`: een reproduceerbare same-machine Trimble-vergelijking ontbreekt nog.

Deze twee punten zijn bewust niet als groen aangemerkt en blijven blokkerend voor de finale productacceptatie in Fase 4, niet voor de technische Fase 1-integratiegate.
