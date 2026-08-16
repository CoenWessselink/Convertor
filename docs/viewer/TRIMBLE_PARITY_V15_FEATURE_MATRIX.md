# CWS Viewer / Convertor V15 — Trimble functional parity matrix

Status: **LOCKED REQUIREMENTS MATRIX**  
Audit date: 2026-08-16  
Scope: visible engineering workflows from Trimble Connect for Windows are used as a behavioural benchmark; CWS keeps its own source, visual identity, contracts and manufacturing rules.

## Source hierarchy

1. Existing CWS V14/V15 code, tests and Windows evidence are the implementation baseline.
2. Supplied `Trimble Connect.zip` is a local behavioural/package reference only.
3. Official Trimble Help for Connect for Windows is used to verify visible product workflows.
4. Supplied ConstruSteel Advanced Scribing / Multi Converter material is used only as functional manufacturing/export reference.
5. Proprietary implementation details, private APIs, credentials, binaries and controller logic are never copied into CWS.

## Status legend

- `BASELINE_VERIFIED` — present in V14 code and previously evidenced.
- `V15_BUILDING` — implementation is now being extended in V15.
- `PARTIAL` — useful implementation exists, but workflow/evidence is incomplete.
- `MISSING` — no adequate CWS implementation yet.
- `EXTERNAL` — deliberately outside a local clone; requires official API/specification or owner evidence.

---

## A. Project shell and navigation

| Trimble-visible workflow | Official behavioural reference | CWS status at T0 | V15 target |
|---|---|---:|---|
| Project content through Explorer side pane | Viewing 2D and 3D Files; Project Details | PARTIAL | Project Explorer dock with canonical tree, filters and context actions |
| Open model/project in 3D Viewer | Viewing 2D and 3D Files | BASELINE_VERIFIED | Preserve direct CWSC/IFC/STEP project hosting |
| Side-panel engineering workspace | Project Details / 3D Viewer Reference Guide | V15_BUILDING | Own CWS dockable Project Explorer + Properties + Review workspace |
| Restore working context | Views / Opening Views in 3D | PARTIAL | Persist dock state, camera/view state, visibility, clipping and review context |
| Full-screen/focus viewer | 3D Viewer application/header behaviour | BASELINE_VERIFIED | Add workspace focus mode without losing state |
| Command-line deep-link style routing | Using the Command Line | PARTIAL | CWS CLI/open arguments for local project/view/review context; no Trimble protocol impersonation |

## B. 3D navigation and camera

| Workflow | CWS status | V15 action |
|---|---:|---|
| Rotate/orbit | BASELINE_VERIFIED | Preserve and re-test |
| Pan | BASELINE_VERIFIED | Preserve and re-test |
| Walk around | BASELINE_VERIFIED | Preserve and re-test |
| Look around | BASELINE_VERIFIED | Preserve and re-test |
| Fit to view | BASELINE_VERIFIED | Preserve and re-test |
| Fit selection | BASELINE_VERIFIED | Preserve and re-test |
| Predefined front/back/left/right/top/bottom/isometric | BASELINE_VERIFIED | Persist in canonical view state |
| Perspective/orthographic | BASELINE_VERIFIED | Persist in view contract |
| Zoom area | PARTIAL/MISSING | Implement deterministic window zoom |
| Camera back/forward history | PARTIAL | Expose and persist history controls |
| Position camera / view from face | PARTIAL | Add face-normal camera placement with exact picked-face evidence |
| Keyboard navigation | PARTIAL | Complete shortcut map and conflicts |

Official reference family: **Navigation and Camera Controls** and **3D Viewer Reference Guide**, Trimble Help, modified 9 Jul 2026.

## C. Selection and visibility

| Workflow | CWS status | V15 action |
|---|---:|---|
| Single object selection | BASELINE_VERIFIED | Preserve |
| Area selection | BASELINE_VERIFIED | Preserve; test crossing/window semantics |
| Multi-selection | BASELINE_VERIFIED | Preserve |
| Assembly selection | PARTIAL | Add highest-valid-assembly selection mode using CWS assembly hierarchy |
| Hide selection | BASELINE_VERIFIED | Preserve |
| Hide others / isolate | BASELINE_VERIFIED | Preserve |
| Show only / show all | BASELINE_VERIFIED | Preserve |
| Ghost context | BASELINE_VERIFIED | Persist in saved views |
| Model/object transparency | PARTIAL | Complete per-model/per-object control and persistence |
| Selection ↔ tree synchronization | BASELINE_VERIFIED | Keep canonical object-id equality gate |

Official reference family: **3D Viewer Reference Guide** and Trimble selection/visibility documentation.

## D. Project Explorer / model tree / assemblies

| Workflow | CWS status | V15 action |
|---|---:|---|
| Hierarchical model/object tree | BASELINE_VERIFIED | Richer project/model/assembly/part hierarchy |
| Search/filter | PARTIAL | Search display columns + canonical IDs + profile/material/mark/source properties |
| Visibility from tree | BASELINE_VERIFIED | Preserve |
| Select descendants/ancestor | PARTIAL | Add context actions |
| Assembly navigation | PARTIAL | Main/secondary drill-down and assembly selection mode |
| Large-tree performance | PARTIAL | Lazy/virtualized population where model size requires it |
| Context commands | PARTIAL | Fit/isolate/hide/show/copy ID/open Workbench |

## E. Properties and provenance

| Workflow | CWS status | V15 action |
|---|---:|---|
| Selected-object properties | BASELINE_VERIFIED | Preserve |
| Source/provenance columns | BASELINE_VERIFIED | Extend to source model, geometry/manufacturing hash and revision |
| Property search/copy | PARTIAL | Add fast property filter and copy actions |
| Confidence/review state | PARTIAL | Tie to canonical evidence/review records |
| Exact source geometry link | BASELINE_VERIFIED | Preserve Exact Part Workbench integration |

## F. Measurement and snapping

| Workflow | CWS status | V15 action |
|---|---:|---|
| Point-to-point distance | BASELINE_VERIFIED | Re-test on Windows packaged build |
| Horizontal/vertical distance | BASELINE_VERIFIED | Preserve |
| Point coordinates | BASELINE_VERIFIED | Preserve |
| Angle | BASELINE_VERIFIED | Preserve |
| Edge/face/object snapping | PARTIAL | Unified snap policy + visual evidence |
| Persistent measurement labels | PARTIAL | Canonical measurement overlay/store |
| Measurement export | PARTIAL/EXISTING TESTS | Wire report/export through one service |
| Unit/tolerance control | PARTIAL | Versioned measurement settings |

## G. Clipping / sections / display

| Workflow | CWS status | V15 action |
|---|---:|---|
| Section/clipping tools | PARTIAL | Multi-plane canonical clipping state + manipulators |
| Clipping box | PARTIAL | Persistence and exact bounds |
| Shaded / edges / wireframe / hidden-line | BASELINE_VERIFIED | Preserve |
| Grid/stamien visibility | BASELINE_VERIFIED | Preserve; improve level/filter/snapping UX |
| Color schemes | BASELINE_VERIFIED | Persist per saved view |
| Explode | PARTIAL | Hierarchy-aware explode state and reset |

## H. Saved views and presentations

Trimble's documented View captures camera/zoom, color/transparency, visibility, measurements, markups, clip planes, grid visibility, clash visibility, ghost mode and orthogonal/perspective state.

| Workflow | CWS status | V15 action |
|---|---:|---|
| Save named view | PARTIAL | Define `CwsSavedView` canonical contract |
| View thumbnails/browser/strip | PARTIAL | Own CWS Views panel with thumbnails |
| Re-open saved view | PARTIAL | Restore complete state deterministically |
| View groups | MISSING | Add local grouping without Trimble cloud semantics |
| Presentation/view sequencing | PARTIAL | Ordered view playback and step controls |
| Original model/revision binding | PARTIAL | Bind saved view to project revision/source hashes |

Official reference: **Create a View**, **Opening Views in 3D**, **Create a View Group**, Trimble Help, modified 9 Jul 2026.

## I. Markups and review issues / ToDos

| Workflow | CWS status | V15 action |
|---|---:|---|
| Text/line/arrow/shape markup | MISSING/PARTIAL | Canonical `CwsMarkup` + 3D/view overlay |
| Markup saved inside view context | MISSING | Bind to saved view and object refs |
| Issue/ToDo title + description | MISSING | `CwsIssue` local review contract |
| Priority/type/status/due date | MISSING | Add versioned fields |
| Assign user/group | EXTERNAL/PARTIAL | Local assignee text/directory; remote sync only via legitimate API |
| Object/model/assembly/file/view context | MISSING/PARTIAL | Typed context references |
| Attachments/comments | MISSING/PARTIAL | Local package first; cloud integration separately gated |

Official reference: **Create a ToDo** and Project Details. CWS will reproduce the workflow concept, not the Trimble service implementation.

## J. Model comparison / revisions / clashes

| Workflow | CWS status | V15 action |
|---|---:|---|
| Exact part comparison | BASELINE_VERIFIED | Preserve |
| Project revision compare core | IMPLEMENTED_IN_TESTS | Wire into V15 UI |
| Added/removed/changed/moved classification | IMPLEMENTED_IN_TESTS | Visual difference mode + report |
| Difference isolation/coloring | IMPLEMENTED_IN_TESTS | Expose in compare workspace |
| Clash/model control | BASELINE_VERIFIED/PARTIAL | Re-evidence broad phase + exact BREP gates |
| Compare evidence/hash binding | PARTIAL | Persist report with source revision hashes |

Important audit finding: older handover documents label comparison/review as missing, but repository tests already contain deterministic revision comparison and exact review-store logic. V15 therefore integrates/reuses these modules instead of rebuilding them.

## K. File/open/export behaviour

| Workflow | CWS status | V15 action |
|---|---:|---|
| IFC/STEP intake | BASELINE_VERIFIED | Preserve crash-isolated geometry worker |
| CWSC project open | BASELINE_VERIFIED | Preserve |
| 2D/PDF behaviour | PARTIAL | CWS PDF/drawing workspace; do not fake native Windows app launch semantics where not useful |
| Scope-first export | PARTIAL | Central `ExportScope` + preflight + output matrix |
| IFC/STEP/PDF/XLSX/CSV/JSON/labels/NC1 | MIXED | Only show formats with real tested backend |
| Batch jobs/progress/cancel | PARTIAL | Central deterministic job queue |
| Output checksums/manifest | BASELINE_VERIFIED | Extend to V15 and manufacturing output |

## L. Manufacturing extensions beyond Trimble Viewer parity

These are required by the supplied CWS manufacturing superprompt and are a CWS product differentiator rather than a visual Trimble clone:

- Manufacturing Faces + face-local frames;
- assembly contact geometry;
- scribing/marking/hole references/identification;
- machine marking capability and reachability;
- nesting-aware mark binding;
- neutral operation sequence planner;
- scope-first export;
- gated NC1/DSTV marking adapter;
- independent validators, hashes, provenance and release gates.

These remain mapped to T8/T9 and the original M1–M9 sequence.

## M. Explicit external boundaries

The following are **not** counted as local CWS parity unless a legitimate integration specification/API and independent evidence exist:

- Trimble account/login implementation;
- Trimble cloud synchronization/server storage;
- Trimble private service endpoints;
- Trimble-owned plugins/licensing/telemetry;
- proprietary binary file/controller formats not publicly specified;
- machine-specific controller transfer without owner-approved golden cases;
- copying Trimble branding, source code, binary resources or private implementation logic.

## N. Definition of V15 parity completion

A matrix row is complete only when:

1. the CWS implementation exists;
2. automated tests cover its deterministic contract;
3. Windows source and packaged GUI smoke passes where applicable;
4. save/reopen is lossless for persistent state;
5. unsupported state is explicit, never silently dropped;
6. the release artifact is bound to the exact Git commit and SHA-256 manifest.

The phrase `100%` in this project therefore means **100% of applicable rows in this locked CWS parity matrix are implemented and verified**, not that CWS contains Trimble proprietary code or private cloud behaviour.

## Official behavioural references used

- Trimble Help — 3D Viewer Reference Guide (Connect for Windows), modified 9 Jul 2026.
- Trimble Help — Navigation and Camera Controls (Connect for Windows), modified 9 Jul 2026.
- Trimble Help — Viewing 2D and 3D Files (Connect for Windows), modified 9 Jul 2026.
- Trimble Help — Project Details (Connect for Windows).
- Trimble Help — Create a View / Opening Views in 3D / Create a View Group.
- Trimble Help — Create a ToDo.
- Trimble Help — Using the Command Line.
