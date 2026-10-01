# CWS Tekla Bridge v0.1 — Opdrachtprompt met Bouwfasen

## Hoofdopdracht
Werk uitsluitend op `feature/cws-tekla-bridge-v0.1`. Bouw een kleine Windows Bridge volgens de masterprompt en API/autorisatiecontracten. Behoud bewezen GitHub-componenten na authority-check; geen force push; geen oude UI-architectuur kopiëren. UI blijft leidend en klein. Iedere fase eindigt met tests én echt bewijs op dezelfde commit. PREPARED/PARTIAL/headless success is geen functionele PASS.

## Fase 0 — Authority/preflight freeze
Leg actuele bron/HEAD, Tekla-versies, dependencyset en Authority Manifest vast. Contracttests voor schemas, model identity en default-deny authorization.
Gate: geen Tekla write vóór contracttests groen.

## Fase 1 — Bridge skeleton + eenvoudige UI
Windows x64 shell; loopback API/dynamic port/session token; health/capabilities/session/model/selection; Tekla DLL/version compatibility fail-closed.
Gate: echte Windows start, actieve Tekla verbinden, juiste model identity lezen.

## Fase 2 — Read-only model/catalog/geometry
Catalogi, objects/parts/assemblies, geometry summary/metrics/compare, canonical↔Tekla mapping.
Gate: echte modellen read-only analyseren en selection roundtrip.

## Fase 3 — Transactional L2 writes
Transaction+journal; beam/polybeam/plate upsert; allowlisted UDA; bewezen cuts/holes; ShapeItem/BRep alleen waar bewezen; build-plan validate/execute.
Gate: create→save→reopen→readback; tweede identieke run 0 duplicaten/0 unintended changes.

## Fase 4 — One-round
Source freeze, recognition, material/profile/geometry resolution, plan, write, save/reopen, readback, safe self-heal, final audit.
Gate: Het Koraal als eerste harde regressie; canonical coverage, physical counts, material blocks, persistence en idempotentie aantoonbaar.

## Fase 5 — 20-model corpus
Batch analyzer over 20 representatieve modellen/modelparen. Coverage voor profielen, materialen, extrusies, BRep/custom/composites/features. Kies circa 5 harde regressiegates; overige coverage corpus.
Iedere fout: oorzaak → algemene regel → testcase → manifest → code.

## Fase 6 — Revision/delta
UNCHANGED/CHANGED/ADDED/REMOVED/CONFLICTED; alleen delta+dependencies; destructive REMOVE via authorization.
Gate: revisie zonder duplicaten of verlies van manual werk.

## Fase 7 — Connections read/propose
Analyseer Tekla-modellen, TS-map/component attributes en details. Bouw joint fingerprints/families. Eerst inspect/candidates/propose.
Gate: voorstellen reproduceren bewezen voorbeelden en onzekerheid blijft zichtbaar.

## Fase 8 — Connections AUTO
Alleen APPROVED families binnen bewezen applicability. Apply/validate/readback op platen/bouten/lassen/cuts/detail/fingerprint/clash. Manual connections KEEP.
Gate: buiten authority altijd PROPOSE/BLOCKED.

## Fase 9 — Review + human authorization
Persistent review store, proposals, project resolutions, confirmation challenges, impact invalidation. Geen cross-part inference.
Gate: GPT kan L3/L4 niet omzeilen; stale source decisions superseden.

## Fase 10 — Production hardening/release
Numbering/NC/productie alleen na aparte gates. Roundtrip waar relevant. Installer commit-bound. Source/tests/installer/runtime/screenshots dezelfde final commit.
Gate: echte Windows/Tekla/reference-model release evidence.

## Codex-regels
- Kleine commits per fase; geen force push.
- Geen default/fallback die onbekende productiedata invult.
- Geen skipped referentietest als PASS.
- Geen UI-telling naast canonical engine-telling.
- Geen endpoint zonder authorization metadata/tests.
- Geen regressietest verwijderen om groen te krijgen.
- Geen globale authority uit één projectbeslissing.
- Bij onzekerheid fail-closed met REVIEW_REQUIRED/BLOCKED.
- Synchroniseer iedere algemene fix naar regression + Authority Manifest + werkwijze.
