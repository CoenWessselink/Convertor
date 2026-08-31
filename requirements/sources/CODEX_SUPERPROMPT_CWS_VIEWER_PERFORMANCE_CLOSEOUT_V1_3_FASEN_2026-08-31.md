# CODEX MASTER-SUPERPROMPT — CWS VIEWER PERFORMANCE CLOSEOUT V1
## Sluit de resterende Viewer-snelheidsgaps volledig
### Exact 3 bouwfasen — meten vóór en na — geen cosmetische PASS

## 0. Doel
Werk verder in de bestaande CWS Convertor repository. Bouw geen tweede Viewer en geen benchmark-demo naast de productapp.

Doel:
> Maak de bestaande CWS Viewer aantoonbaar sneller bij cold load, warm reopen en same-session gebruik; houd orbit/pan/zoom vloeiend terwijl geometry op de achtergrond binnenkomt; meet de echte packaged Windows-runtime; vergelijk waar mogelijk op dezelfde pc/model met Trimble; voer pas daarna rendering-microtuning uit.

Behoud bestaande sterke foundations:
- progressive/proxy-first Viewer;
- één permanente Viewer/context;
- shared geometry/instancing;
- 60 Hz input coalescing;
- upright orbit/pivot/zoom;
- spatial picking;
- whole-object selection;
- crash-isolated IFC workerfoundation;
- ViewerPerformanceEvidence;
- canonical Project/Geometry/Selection truths.

## 1. Verplichte repository-preflight
Auditbaseline:
- repo: `CoenWessselink/Convertor`
- branch: `agent/cws-product-ui-reintegration-v1`
- audit-SHA: `dc4e3e2ec2f91c40aad271d985b3fe59a44c7325`

Deze SHA is alleen baseline. Start met:
```text
git fetch --all --prune
git status
git branch -vv
git log -25 --oneline --decorate
```
Leg vast:
`CURRENT_CANONICAL_BRANCH`, `CURRENT_HEAD_SHA40`, `CURRENT_VERSION`, `WORKTREE_CLEAN`.

Als er nieuwere commits zijn: audit ze eerst en hergebruik correct uitgevoerde performancecode.

Maak:
`validation/viewer_performance_closeout/PREFLIGHT.json`
`validation/viewer_performance_closeout/PREFLIGHT.md`

## 2. Statusmodel
Gebruik uitsluitend:
`PASS | FAIL | BLOCKED | NOT_TESTED | NOT_APPLICABLE`

Houd apart:
`IMPLEMENTED | INTEGRATED | TESTED | PACKAGED_PROVEN | TRIMBLE_PROVEN`

Geen “mostly done”, “looks faster” of “smooth enough”.

## 3. Harde closeout-scope
Sluit exact deze punten:
1. IFC persistent process worker pool.
2. echte dynamische geometry priority scheduler.
3. MeshCache V2.
4. per-frame VTK upload budget + backpressure.
5. MSAA/FXAA tijdens interactie benchmarken en tunen.
6. echte packaged performance instrumentation.
7. cold/warm/same-session benchmark.
8. 10-minuten real Viewer soak.
9. same-machine Trimble comparison.
10. daarna pas finale rendering microtuning.

Aanvulling: maak één centrale `ViewerPerformanceGovernor`.

## 4. Geen duplicate authorities
Behoud:
- ONE ViewerHost
- ONE SelectionAuthority
- ONE Project Model
- ONE Geometry Repository truth
- ONE load priority authority
- ONE Viewer scheduler authority
- ONE ViewerPerformanceGovernor
- ONE MeshCache authority

Geen tweede Viewer, geen alternate performance-app, geen benchmarkroute die andere productcode gebruikt.

## 5. Verplichte metrics
Breid `ViewerPerformanceEvidence` uit waar nodig.

### Startup/load
- shell_visible_ms
- first_tree_ms
- first_pixels_ms
- proxy_scene_ready_ms
- first_usable_ms
- exact_25_ms
- exact_50_ms
- exact_75_ms
- exact_100_ms
- geometry_ready_ms

### Rendering
- frame_p50_ms
- frame_p95_ms
- frame_p99_ms
- stall_33ms_count
- stall_50ms_count
- stall_100ms_count

### Input
- input_to_render_p50_ms
- input_to_render_p95_ms
- orbit_latency_p95_ms
- pan_latency_p95_ms
- zoom_latency_p95_ms
- fit_latency_p95_ms

### Picking
- pick_p50_ms
- pick_p95_ms
- selection_p95_ms
- whole_object_highlight_p95_ms
- wrong_instance_picks
- hidden_object_false_picks

### Pipeline
- geometry_queue_depth_peak
- upload_queue_depth_peak
- upload_frame_p50_ms
- upload_frame_p95_ms
- cache_memory_hits
- cache_disk_hits
- cache_misses
- cache_corruptions
- worker_count
- worker_utilization
- worker_restart_count
- worker_crash_count

### Resources
- rss_start_mb / rss_peak_mb / rss_end_mb / rss_drift_percent
- vram_start_mb / vram_peak_mb / vram_end_mb
- thread_count_start/end
- process_count_start/end
- actor_count_start/end

Onmeetbaar = null + NOT_TESTED. Niets verzinnen.

## 6. Targets
### Load
- medium first usable preferred ≤ 2 s
- large first usable preferred ≤ 3 s
- large hard target ≤ 5 s
- warm reopen preferred ≤ 1–2 s waar hardware/model/cache dit toelaat

### Rendering
- 60 Hz: frame p50 ≤ 16.7 ms
- frame p95 ≤ 25 ms
- heavy large scene p95 ≤ 33 ms where feasible
- input→render p95 ≤ 35 ms

### Picking
- medium p95 ≤ 80 ms
- large p95 ≤ 150 ms
- wrong_instance_picks = 0

### Freeze/memory
- unintended stalls >100 ms = 0 na first usable bij normale interactie
- 10-min real Viewer RSS drift <10%

### Trimble
Op dezelfde machine/model:
- CWS first usable ≤ Trimble ×1.10
- CWS navigation p95 ≤ Trimble ×1.10
- CWS pick p95 ≤ Trimble ×1.10

Geen echte Trimbledata = NOT_TESTED, nooit PASS.

# FASE 1 — THROUGHPUT + CACHE + PRIORITY + UPLOAD GOVERNOR

## 7. IFC persistent process worker pool
Bouw bovenop de bestaande crash-isolated workerfoundation een bounded persistent pool:
```text
GeometryPriorityScheduler
  ├ IFC worker 1
  ├ IFC worker 2
  ├ IFC worker 3
  └ IFC worker N
        ↓
ready mesh queue
```
Eisen:
- iedere worker eigen IFC/OCP context;
- geen native state sharing;
- persistent reuse;
- crash vervangt alleen de defecte worker;
- cancellation/generation safe;
- timeout;
- clean shutdown;
- frozen Windows worker support;
- geen zombie processes.

Benchmark worker counts 1/2/3/4/6 en meet first usable, exact100, CPU, worker RSS, total RSS, crash/restart. Kies beste default op throughput versus RAM, niet hoogste getal. Voeg benchmarkoverride `CWS_VIEWER_IFC_WORKERS` toe.

## 8. STEP/non-IFC parallelisatie
Audit provider/thread/process safety. Indien OCP/CadQuery niet thread-safe genoeg is, gebruik processen of houd uitsluitend de unsafe route serial. Documenteer in `NON_IFC_PARALLELISM_REPORT.md`. Geen unsafe threading voor mooie cijfers.

## 9. Dynamic GeometryPriorityScheduler
Vervang FIFO + selected-only door één dynamische authority.

Signalen minimaal:
1. selected
2. under cursor / recently picked
3. visible
4. projected screen area / visual dominance
5. camera distance
6. current assembly/context
7. rest

Gebruik bij voorkeur:
```text
priority_score =
 selection_weight
+ cursor_weight
+ visibility_weight
+ projected_area_weight
+ camera_distance_weight
+ recent_interaction_weight
+ assembly_context_weight
- already_good_lod_penalty
```
Eisen:
- deterministic;
- reprioritize op betekenisvolle camera/contextchange;
- geen volledige queue rebuild per raw mouse event;
- hysteresis;
- starvation prevention;
- selected preemption;
- queue metrics.

## 10. MeshCache V2
Nieuwe versie: `cws-viewer-mesh-cache-v2`.

Persist minimaal:
- vertices
- triangles/indices
- normals
- feature/sharp edges
- bounds
- LOD0
- LOD1
- LOD2 waar gegenereerd
- metadata

Eisen:
- mmap waar passend;
- minimale decompress/copy overhead;
- immutable/versioned format;
- dtype/endian metadata;
- atomic write;
- corruption recovery;
- source/settings/provider invalidation;
- Windows mmap/file handle cleanup;
- bounded RAM LRU.

V1 mag veilig worden verwijderd/opnieuw opgebouwd in plaats van complexe migratie.

Benchmark:
- cold no-cache
- V1 warm indien reproduceerbaar
- V2 disk warm new process
- V2 same-session RAM hit

V2 warm moet meetbaar sneller zijn.

## 11. Per-frame VTK upload + backpressure
Niet alleen batch size.

```text
worker results
→ bounded ready queue
→ UI frame
→ consume tot time budget
→ render/input
→ next frame
```

Adaptief budget via governor:
- INTERACTIVE: 1–3 ms/frame
- RECOVERY: 3–4 ms/frame
- IDLE_HIGH_QUALITY: 6–8 ms/frame

Benchmark de exacte defaults.

Eisen:
- backpressure;
- stale generation discard;
- cancellation;
- camera/selection/visibility blijven intact;
- incremental mesh refresh;
- geen full scene rebuild;
- queue/upload metrics.

## 12. ViewerPerformanceGovernor
Maak één centrale authority met states:
- INTERACTIVE
- RECOVERY
- IDLE_HIGH_QUALITY
- BACKGROUND_LOADING

Governor bepaalt:
- MSAA
- FXAA
- SSAO
- shadows
- upload budget
- LOD target
- exact-refinement aggressiveness
- measurement preview rate
- non-critical inspector refresh/defer

Input → INTERACTIVE. Na inputstop → RECOVERY. Na ca. 100–200 ms stabiele idle → IDLE_HIGH_QUALITY.

## 13. MSAA/FXAA benchmark
Benchmark:
- 0x MSAA + FXAA
- 2x
- 4x
- 8x

Op medium/large en indien mogelijk geïntegreerde + discrete GPU. Meet p50/p95/p99 en stalls, plus screenshots.

Kies policy uit bewijs. Waarschijnlijke richting maar niet vooraf hardcoderen:
- interactive 0–2x/FXAA
- recovery 2x
- idle HQ 4x

## 14. Fase 1 tests
Verplicht:
- pool startup/shutdown;
- worker crash/restart;
- timeout/cancel;
- stale generation;
- priority reprioritization/starvation;
- Cache V2 R/W/corruption/invalidation;
- Windows mmap release;
- upload backpressure/time budget;
- governor transitions;
- MSAA policy;
- camera/selection persistence during patch.

Deliverables onder `validation/viewer_performance_closeout/phase1/`:
`WORKER_POOL_MATRIX.json`, `PRIORITY_SCHEDULER_MATRIX.json`, `CACHE_V2_REPORT.json/.md`, `UPLOAD_BUDGET_REPORT.json`, `GOVERNOR_REPORT.json`, `MSAA_FXAA_MATRIX.json`, `PHASE_1_CHECKLIST.json/.md`.

Fase 1 PASS alleen wanneer alle bovenstaande onderdelen functioneel + geïntegreerd + regressievrij zijn.

# FASE 2 — PACKAGED METRICS + BENCHMARKS + 10-MIN SOAK

## 15. Packaged instrumentation
Koppel metrics aan dezelfde echte productviewer voor:
- source run
- one-folder EXE
- fresh portable

Geen developer Python PATH. Eventueel `--viewer-performance-probe`, maar dezelfde Viewer/servicecode.

## 16. Environment manifest
Per run:
- CPU/model/cores
- RAM
- GPU/VRAM/driver
- Windows
- resolution/DPI/refresh
- source SHA/version
- model class/input size/entity/geometry/triangle count
- cache mode
- worker count

## 17. Cold/warm/same-session
COLD:
- new process
- CWS cache absent/cleared
- minimaal 5 runs

WARM:
- new process
- V2 disk cache populated
- minimaal 10 runs

SAME SESSION:
- same process/session
- minimaal 10 runs

Rapporteer min/median/p90/p95/max/stddev voor loadmetrics en resources. Geen “beste run” als enige conclusie.

Modelset minimaal:
- SMALL
- MEDIUM
- LARGE
- INSTANCE_HEAVY

Real large model preferred; ontbreekt deze dan status NOT_TESTED.

## 18. Frame/input benchmark
Na first usable vaste reproduceerbare sequence:
orbit, pan, wheel zoom, fit, front/top/iso, select, multi-select, hide/show, isolate.

Meet frame p50/p95/p99, input p50/p95, stalls, pick p95, selection p95 en wrong-instance picks.

## 19. 10-minuten real Viewer soak
Duur ≥600 s.
Niet headless-only.
Real VTK/OpenGL + representatieve geometry.

Cycli:
orbit/pan/zoom/fit/standard views/part selection/assembly selection/multiselect/hide/show/isolate/ghost/section/measure, en zo mogelijk progressive exact patches.

Meet:
RSS/VRAM/threads/processes/workers/actors/mesh groups/widgets + frame p50/p95/p99 + stall counts.

Hard:
- RSS drift <10%
- worker leak 0
- thread leak 0
- actor leak 0
- unintended >100 ms stalls 0
- crash 0

## 20. Before/after
Maak rapport:
`metric | before | after | delta | % improvement | status`

Minimaal:
first usable, exact100, warm reopen, frame p95, frame p99, input p95, pick p95, RSS, stalls.

Ontbrekende baseline = transparant NOT_TESTED.

Deliverables phase2:
`ENVIRONMENT.json`, `COLD_RUNS.json`, `WARM_RUNS.json`, `SAME_SESSION_RUNS.json`, `LOAD_BENCHMARK_SUMMARY.json/.md`, `FRAME_INPUT_BENCHMARK.json`, `PICKING_BENCHMARK.json`, `REAL_10MIN_SOAK.json/.md`, `BEFORE_AFTER.json/.md`, `PACKAGED_ONE_FOLDER_PROBE.json`, `PACKAGED_PORTABLE_PROBE.json`, `PHASE_2_CHECKLIST.json/.md`.

# FASE 3 — TRIMBLE + MICRO-TUNING + EXACT-SHA FREEZE

## 21. Same-machine Trimble
Twee matrices.

Behavior:
orbit direction, pan, zoom, cursor zoom, pivot, fit, standard views, part/assembly/multi selection, hide/isolate/show, section, measure.

Performance op exact dezelfde machine/model/camera:
- first pixels
- first usable
- warm reopen
- frame p50/p95/p99
- pick p95
- memory

Rapporteer CWS/Trimble ratio. Target ≤1.10. Geen reference = NOT_TESTED, geen parityclaim.

## 22. Microtuning pas nu
Tune pas na benchmarks:
- lighting
- material response
- normals
- feature/silhouette edges
- SSAO idle
- shadows
- idle MSAA/FXAA
- background
- selection fill/outline
- LOD thresholds

Geen first-usable regressie. Geen frame p95 regressie >5% zonder onderbouwde visuele winst. Geen nieuwe >100 ms stalls.

## 23. Exact-SHA packaged acceptance
Fresh exact SHA:
- one-folder
- portable
- installer indien release-scope

Test launch/open/first pixels/first usable/orbit/pan/zoom/pick/selection/progressive exact/cache reopen/save/close/reopen.

Bind evidence aan branch, commit40, tree SHA, version, worker/cache/scheduler/governor version, Python/Qt/VTK.

Deliverables phase3:
`TRIMBLE_ENVIRONMENT.json`, `TRIMBLE_BEHAVIOR_MATRIX.json`, `TRIMBLE_PERFORMANCE_MATRIX.json`, `TRIMBLE_COMPARISON.md`, `RENDER_MICROTUNING_MATRIX.json`, `RENDER_MICROTUNING.md`, `PACKAGED_FINAL_ACCEPTANCE.json/.md`, `FINAL_VIEWER_PERFORMANCE_ACCEPTANCE.json/.md`.

## 24. Final score
Bereken:
- IMPLEMENTATION_SCORE
- INTEGRATION_TEST_SCORE
- PACKAGED_PROOF_SCORE
- TRIMBLE_PROOF_SCORE

Voor elk van de 10 hoofdpunten: 0–100%, evidence refs, resterende gaps.

Geen 100% zonder bewijs.

## 25. Definition of Done
`VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer:
1. current canonical SHA geaudit;
2. worker pool gebouwd + benchmarked;
3. crash isolation behouden;
4. dynamic priority actief;
5. starvation tests groen;
6. Cache V2 actief;
7. warm reopen meetbaar verbeterd;
8. per-frame uploadbudget/backpressure actief;
9. governor actief;
10. MSAA/FXAA uit benchmark gekozen;
11. packaged instrumentation werkt;
12. cold/warm/same-session complete;
13. frame p50/p95/p99 gemeten;
14. input/pick gemeten;
15. 10-min real soak PASS;
16. RSS drift <10%;
17. geen worker/thread/actor leaks;
18. unintended >100 ms stalls = 0;
19. before/after bewijs aanwezig;
20. microtuning pas na benchmark;
21. exact-SHA one-folder PASS;
22. fresh portable PASS;
23. geometry/selection/camera regressievrij;
24. Trimble PASS waar reference beschikbaar is, anders expliciet NOT_TESTED.

## 26. Prioriteit bij problemen
1 correctness/crash
2 UI freeze/>100ms stalls
3 first usable
4 worker throughput
5 cache reopen
6 frame p95/p99
7 input latency
8 picking
9 memory
10 renderingbeauty

## 27. Commitstrategie
Voorbeeld:
- `perf(viewer): add persistent IFC process worker pool`
- `perf(viewer): add dynamic viewport priority scheduler`
- `perf(cache): add memory-mapped MeshCache V2`
- `perf(viewer): add adaptive per-frame upload backpressure`
- `perf(viewer): add centralized performance governor`
- `perf(render): tune interaction AA from benchmark`
- `test(perf): add packaged cold warm session benchmarks`
- `test(perf): add 10-minute real Viewer soak`
- `test(perf): add same-machine Trimble harness`
- `perf(render): apply measured final microtuning`
- `test(release): bind Viewer performance proof to exact SHA`

## 28. Doorgaan-regel
Bij “Ga verder / Bouw verder / Test verder / Volgende fase”:
1 fetch canonical HEAD
2 lees fasechecklist
3 pak eerste niet-PASS
4 reproduceer
5 fix
6 targeted tests
7 benchmark
8 regressie
9 evidence
10 commit
11 ga door

Geen nieuwe vraag wanneer checklist ondubbelzinnig is.

## 29. START NU
A. preflight
B. actual code audit van de 10 punten
C. before-baseline waar nog mogelijk
D. bouw/finaliseer Fase 1
E. voer Fase 1 gate uit

Niet eerst V5 UI-cosmetica.

Niet stoppen na alleen documentaudit als codebouw veilig kan doorgaan.

## 30. Slot
Het doel is niet meer performanceclasses, maar:
> een aantoonbaar snellere, stabielere en vloeiendere CWS Viewer in de echte Windows-app, met meetbare cold/warm/session winst, geen langdurige UI-stalls, gecontroleerd geheugengedrag en waar mogelijk een onderbouwde same-machine vergelijking met Trimble.
