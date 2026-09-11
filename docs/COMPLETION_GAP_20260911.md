# CWS Convertor completion gap — 2026-09-11

Baseline: `6237878b8df0089ce4f1c8c6b7ef8ffe542dbb32`
Completion branch: `agent/cws-completion-gap-20260911`
Focused verified matrix commit: `b9c85fef8effa4bc4dd14c024ec9b6f60facde8b`

This file is intentionally conservative. An action is only called complete when the existing canonical runtime executes it with exact BOM scope and produces a verifiable post-condition. Navigation or a prepared form is not completion.

## Verified W03/W18 matrix

The focused Windows gate classified all 87 official BOM actions and rejected unclassified actions.

- `PASS_SOURCE`: 55
- `PARTIAL`: 29
- `SAFE_REFUSAL`: 2
- `EXTERNAL_ACCEPTANCE_REQUIRED`: 1
- `MISSING`: 0

This is not yet global W03/W18 closure: `PARTIAL` and `SAFE_REFUSAL` remain explicit work.

## First repaired / clarified actions

- `drawing.print`: generates the canonical PDF for the exact selected entity. In interactive Windows it uses the existing native Qt print route. Headless CI deliberately remains `PREPARED` because a physical/native printer dialog cannot be accepted honestly there.
- `optimize.compare`: profile comparison executes the existing Phase 3 scenario compare and propagates its actual status. Plate comparison executes only when a canonical plate compare implementation exists; otherwise it fails closed.
- `optimize.alternatives`: source review proved that the profile Phase 3 command service does not provide an alternatives operation. The action therefore remains a deliberate `SAFE_REFUSAL`; no alternative profile/material is invented.
- `export.occurrences`: remains a `SAFE_REFUSAL` because the current canonical export contract selects entity IDs, not independently addressable occurrence IDs. It never broadens to a different export.

## Main remaining partial groups

- explicit STEP / IFC / DXF / PDF / NC1 / production-package actions preserve exact selection, format and preflight, but the shipping Export Center still expects the user to choose/confirm the output folder and press Generate;
- grouping actions per part / mark / assembly / machine / phase likewise prepare the exact grouped export but do not yet complete the user-confirmed Generate step from the original BOM click;
- `viewer.section` and `viewer.measure` open the correct viewer tooling but still require an interactive plane / point choice;
- `edit.profile`, `edit.material` and `edit.length` route to the canonical edit workflow rather than mutating geometry-sensitive fields blindly from the BOM grid;
- drawing setup / format / scale / views open the exact drawing settings but require explicit user choices;
- production route / operations / NC preview are review/workflow surfaces rather than automatic manufacturing mutations;
- remnants / kerf actions configure the canonical solver and intentionally do not claim that a new optimization has already completed;
- plate plan compare is not yet a universal canonical operation;
- per-machine optimization and drawing batch execution remains fail-closed until a partitioned executor can preserve exact machine scope.

## Acceptance rule

Allowed final states are:

- `PASS_INSTALLED`: installed application executed the exact action and post-condition;
- `PASS_SOURCE`: deterministic source/runtime action executed, when installed hardware is not relevant;
- `PARTIAL`: exact intent/scope is preserved but a further explicit user or runtime step is required;
- `SAFE_REFUSAL`: requested action is unavailable and no broader or different action was executed;
- `EXTERNAL_ACCEPTANCE_REQUIRED`: hardware/supplier/production qualification remains external;
- `MISSING`: intended functionality does not exist.

`PREPARED` is never promoted to a functional PASS.
