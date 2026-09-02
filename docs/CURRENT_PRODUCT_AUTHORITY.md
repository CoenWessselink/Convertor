# CWS Convertor current product authority

Status: `current_release_authority`

This file is the current phase authority. Older handover documents retain audit
value but are `historical_frozen_source` and `superseded_for_current_status`.

## Product identity

- Product: CWS Convertor
- Version: 0.10.18-beta-dev
- Project Model: 2.25
- Canonical Part: 1.1
- Viewer package: 1.4.0-v15-preview.2
- Active phase: Phase 4 - dynamic release acceptance

## Canonical architecture

- One `CWSMainWindow` composition root.
- One `UnifiedApplicationContext` with versioned, hashed snapshots.
- One permanent ViewerHost and Viewer V15 core.
- One application selection bus.
- One central bounded `JobManager`.
- One canonical project and part model.
- One Workbench transaction/write path.
- One drawing and trusted-PDF path.
- One export/release safety gate.

## Repository evidence

The canonical source branch is `agent/cws-product-ui-reintegration-v1`.
The exact HEAD, parent, clean-tree result, packaged runtime checksums and all
dynamic requirement rows are generated at release time in
`validation/full_acceptance/RELEASE_BINDING.json` and
`validation/full_acceptance/master_traceability/`. A hard-coded SHA in this
tracked document would immediately become stale when the document changes.

## Safety authority

The following values are immutable software defaults:

```text
machine_observed_by_cws = false
deployment_transport_authorized = false
direct_machine_transfer = false
machine_transfer.allowed = false
```

M18 and machine-specific qualification remain fail-closed when exact external
authority evidence is unavailable.
