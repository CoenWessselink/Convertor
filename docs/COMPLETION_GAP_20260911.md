# CWS Convertor completion gap — 2026-09-11

Baseline: `6237878b8df0089ce4f1c8c6b7ef8ffe542dbb32`
Completion branch: `agent/cws-completion-gap-20260911`

This file is intentionally conservative. An action is only called complete when the existing canonical runtime executes it with exact BOM scope and produces a verifiable post-condition. Navigation or a prepared form is not completion.

## First repaired W03/W18 actions

- `drawing.print`: now generates the canonical PDF for the exact selected entity before invoking a native print hook when one exists. Without a printer hook it remains `PREPARED`, with the generated PDF retained; it is not falsely reported as printed.
- `optimize.compare`: profile comparison executes the existing Phase 3 compare action. Plate comparison executes only when the plate workspace exposes a canonical compare implementation; otherwise it fails closed.
- `optimize.alternatives`: profile alternatives execute the existing Phase 3 alternatives action. Plate alternatives execute only when a canonical plate alternative implementation exists; otherwise it fails closed.

## Still explicitly open after this patch

- per-machine optimization and drawing batches remain fail-closed until their canonical partitioned executors exist;
- generic actions that only route to a workspace remain `PREPARED`, not `PASS`;
- print requires installed/native acceptance because printer availability is environment dependent;
- every action in the 87-action matrix still needs final installed-app classification and post-condition evidence before W03/W18 can be closed globally.

## Acceptance rule

Allowed final states are:

- `PASS_INSTALLED`: installed application executed the exact action and post-condition;
- `PASS_SOURCE`: deterministic source/runtime action executed, when installed hardware is not relevant;
- `SAFE_REFUSAL`: requested action is unavailable and no broader or different action was executed;
- `EXTERNAL_ACCEPTANCE_REQUIRED`: hardware/supplier/production qualification remains external;
- `MISSING`: intended functionality does not exist.

`PREPARED` is never promoted to a functional PASS.
