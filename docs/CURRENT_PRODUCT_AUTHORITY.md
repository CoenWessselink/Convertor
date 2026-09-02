# CWS Convertor current product authority

Status: `current_authority_in_progress`

This file is the current phase authority. Older handover documents retain audit
value but are `historical_frozen_source` and `superseded_for_current_status`.

## Product identity

- Product: CWS Convertor
- Version: 0.10.21-beta-dev
- Project Model: 2.25
- Canonical Part: 1.1
- Active phase: Exact-SHA BOM Productiehub release acceptance

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
- One exact-SHA BOM completion gate before Windows packaging.

## Repository evidence

Branch, HEAD, parent and working-tree state are deliberately `NOT_TESTED` in
this initial authority record. They must be captured only by an explicitly
authorized repository operation and must never be inferred from an old prompt.

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
