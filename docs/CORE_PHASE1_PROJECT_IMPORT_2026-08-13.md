# Core phase 1: Project Model and source geometry

Date: 2026-08-13
Branch: `feature/core-phase-1-project-import`
Base: phase-0 commit `d6b855a`
Project Model: `2.4`
Semantic importer contract: `2.2`

## Scope decision

The existing Project Model, `.cwscproj` storage, migrations, autosave,
transaction rollback, indexes, jobs and semantic IFC/STEP import already met
the phase-1 foundation. This phase closes the missing link between one
materialised `Part` and its re-verified source geometry. It does not open any
production export gate.

## Implemented contract

- Every newly imported IFC/STEP part stores a versioned `source_locator` tied
  to source ID, source SHA-256, source entity and source-geometry hash.
- A source is hashed again before geometry is read. Changed source bytes are
  rejected.
- A STEP part with exactly one semantic BREP root and exactly one native solid
  resolves to an exact, part-scoped native BREP. Multi-root or multi-solid STEP
  stays `manual_validation_required`; list order and filenames are never used
  to pick a solid.
- An IFC part is selected by entity ID and cross-checked with GlobalId and
  representation ID. Its part-scoped tessellation is explicitly not presented
  as exact production BREP.
- IFC geometry runs in a spawned worker process. This prevents CadQuery/OCP and
  IfcOpenShell native runtimes from causing the observed Windows access
  violation when loaded into one long-lived process.
- Persisted inspections contain only versioned evidence, metrics and topology.
  Runtime BREP objects and mesh vertices are not written into `.cwscproj`.
- `project-inspect-source-geometry` exposes the same transactionally saved
  operation through the CLI.
- Dist, portable and installed runtime smoke tests now import an IFC, isolate a
  selected part in the frozen worker, save the project and verify the package.

## Reference evidence

The three available, nested STEP references named by the acceptance suite were
read without modifying them. Each materialised as one part and resolved as one
exact native solid. Their measured values remain observations only: the
existing expected-result records remain `manual_validation_required`.

The exact Tekla IFC fixture required by the reference acceptance test is not
present under the configured reference roots. That test is skipped only for
that file; STEP reference tests still run.

## Large-model evidence

Local confidential evidence is kept outside Git:

| Model class | Size | Result | Elapsed | Peak RSS |
| --- | ---: | --- | ---: | ---: |
| supplied large STEP | 9.2 MB | semantic import plus exact BREP resolution passed | 14.9 s | 530 MB |
| supplied large IFC | 81.3 MB | 64,015 entities plus one selected part mesh passed | 54.6 s | 2,002 MB |

Both sources remained unchanged and both project production gates remained
closed. The IFC report omits source name, path and hash.

## Local quality gate

- `compileall`: passed;
- `pip check`: passed;
- smoke scripts: 32/32 passed;
- known unittest cases: 111;
- explicit fixture-dependent skips: 7;
- golden expected results promoted to validated: 0.

## Remaining gates

- Exact BREP mapping for multi-solid STEP products is not implemented.
- IFC source isolation is an exact entity selection but only a tessellated
  shape; exact IFC BREP and feature validation remain open.
- No observed dimension, volume, area, material or feature value becomes a
  golden expectation until independently validated.
- Per-format canonical roundtrips and production-feature validation belong to
  phase 2.
- Windows CI must pass before this phase is merged or used as build evidence.
