# U1 Project Model 2.25 — status

## Scope

Unify the active GitHub Project Model `2.5` and frozen Scribing M18 Project Model `2.24` without downgrading Viewer V15/Convertor or losing M18 authority evidence.

## Implemented contract

- canonical target schema: `2.25`
- accepted migration authorities: GitHub `2.5`, historical Scribing/Profile Nesting `2.6`–`2.24`, and existing early `2.0`–`2.4` migration path
- future `2.26+`: fail closed
- M18 project stores: losslessly retained through the U1 extension bridge for U2 semantic promotion
- per-part M18 `manufacturing_faces` / `manufacturing_faces_state`: losslessly retained
- part `geometry_hash` and `manufacturing_hash`: unchanged for `2.5` and `2.6`–`2.24` migrations
- Viewer declares `2.24` migration input and canonical `2.25` compatibility
- direct machine transfer remains outside U1 and is not enabled

## Gate

`CWS Unified U1 Project Model 2.25 gate` must pass:

1. U0 baseline regression
2. U1 migration/save-reopen contract
3. current Project Model regression
4. project storage regression

Status: **implementation committed; CI gate pending**.
