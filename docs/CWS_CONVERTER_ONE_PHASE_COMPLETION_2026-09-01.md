# CWS Converter — one-phase completion

Date: 2026-09-01
Branch: `agent/cws-product-ui-reintegration-v1`

## Delivered contract

The Converter now has one fail-closed planning and execution authority for all
12 cross-format routes between NC1, STEP, IFC and Trusted PDF. The authority is
`cws_convertor.conversion_service`; the former capability registry is a
compatibility view over that authority and no longer owns policy.

Each target-specific preflight returns exactly one of:

- `SUPPORTED`
- `SUPPORTED_WITH_LIMITS`
- `REVIEW`
- `BLOCKED`

Only the first two are executable. `REVIEW` and `BLOCKED` retain machine-readable
reasons and can no longer be re-enabled by a UI fallback.

## Execution and evidence

Every approved loose-file conversion performs, in order:

1. source inspection and source SHA-256 binding;
2. target-specific planning;
3. physical serialization;
4. physical target re-import;
5. geometric comparison;
6. semantic or identity/scope comparison;
7. atomic evidence-manifest save and reopen verification.

The evidence manifest binds the plan, source hash, output hashes, warnings and
all proof results. Trusted PDF output additionally proves visible vector page
content, the main-view label, part/profile identity and visible feature labels;
an embedded payload alone is not accepted as visible drawing proof.

## Scope handling

- Single-part routes remain part scoped.
- Proven trusted multi-solid STEP to NC1/PDF is split per solid and receives a
  part-split manifest; incomplete splits fail the route.
- Assembly/multi-product routes receive an identity manifest containing part
  IDs, assembly IDs and parent-child relations.
- Unproven history-free multi-solid interpretation remains `REVIEW`.
- History-free STEP/IFC to manufacturing output uses the Manufacturing Geometry
  Interpreter gate; a confirmed Part Workbench uses the stricter target-specific
  canonical rebuild/roundtrip authority.

## Batch and application behavior

The Qt application submits one isolated child process for the whole batch. The
child preflights every item before the first serializer starts, records progress,
continues after individual blocked/failed items and writes a batch manifest.
Cancel terminates the native child and escalates to kill after a bounded wait.

Project selection validates only the chosen target. The existing four-format
release gate remains unchanged for full production release validation.

## Verification gates

- `tests/conversion_one_phase_contract_smoke.py`: dependency-light registry,
  status, scope, UI and worker contract.
- `tests/product_full_acceptance.py`: source-runtime 12-route matrix with all
  proof layers and reopenable evidence.
- `tests/conversion_one_phase_packaged_smoke.py`: all 12 routes through the
  packaged Windows GUI worker with Python and pip removed from child `PATH`.
- `.github/workflows/final-release-proof.yml`: exact `${{ github.sha }}` checkout,
  pinned Windows runtime, packaged matrix report and exact-SHA release artifact.

The packaged matrix is considered proven only when the exact-SHA Windows job is
green. Its durable report is uploaded as
`validation/full_acceptance/CONVERSION_PACKAGED_MATRIX.json`, together with the
copied route artifacts and independently reopened evidence manifests in
`validation/full_acceptance/conversion_packaged_matrix_evidence/`.
