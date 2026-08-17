# U1 Project Model 2.25 — COMPLETE

## Scope

Unify the active GitHub Project Model `2.5` and frozen Scribing M18 Project Model `2.24` without downgrading Viewer V15/Convertor or losing M18 authority evidence.

## Implemented contract

- canonical unified schema: `2.25`
- migration path: GitHub `2.5 -> 2.25`
- migration path: frozen Scribing M18 `2.24 -> 2.25`
- historical Scribing/Profile Nesting `2.6`–`2.23` accepted through the same controlled bridge
- existing early `2.0`–`2.4` Workbench migration semantics preserved
- future `2.26+`: fail closed
- M18 project stores retained losslessly for U2 semantic promotion
- per-part M18 `manufacturing_faces` / `manufacturing_faces_state` retained losslessly
- part `geometry_hash` and `manufacturing_hash` remain stable for `2.5` and `2.6`–`2.24` migration
- original source-schema provenance remains immutable across save/reopen
- native `2.25` snapshots remain hash-stable and do not acquire synthetic bridge metadata on reopen
- Viewer compatibility contract includes migration input `2.24` and canonical `2.25`
- direct machine transfer remains outside U1 and is not enabled

## Verified gate

Workflow: `CWS Unified U1 Project Model 2.25 gate`

Successful verification on commit `c4972640f4f873a819cf3d36d4f04f872868477a`:

1. compile U1 project modules — PASS
2. preserve frozen U0 baseline — PASS
3. unified `2.5/2.24 -> 2.25` migration and save/reopen contract — 6/6 PASS
4. Project Model regression — 13/13 PASS
5. project storage/save-reopen regression — 10/10 PASS
6. evidence artifact upload — PASS

Total explicit Python test cases in U1/model/storage suites: **29/29 PASS**.

## Safety

```text
machine_observed_by_cws = false
deployment_transport_authorized = false
direct_machine_transfer = false
machine_transfer.allowed = false
```

## Result

**U1 COMPLETE — ready for U2 Manufacturing/Scribing semantic merge.**
