# Core phase 2 - Part Workbench and production roundtrips

Date: 2026-08-13

## Scope

- Project Model 2.5 and Part Workbench 1.1 migration.
- Recognition candidate included in the manufacturing identity.
- Exact analytical rebuild for lines, explicit arcs, custom cross-sections,
  round bar and supported holes in exact catalogue profiles.
- Strict NC1, STEP, native IFC and Trusted PDF export/re-import matrix.
- Service, CLI and Part Workbench UI integration.

## Production contract

A part can be released only when:

1. Workbench validation has no blocking issue.
2. Source comparison uses part-scoped exact production geometry and passes.
3. The stored canonical rebuild is current.
4. NC1, STEP, IFC and Trusted PDF all pass independently.
5. The roundtrip report matches the current manufacturing hash and canonical
   signature.

Each format checks the exact embedded canonical geometry payload. NC1, STEP
and IFC additionally compare visible volume, area, bounding box, solid count
and validity. A failed rerun invalidates previous artifacts. Any manufacturing
edit invalidates rebuild, roundtrip and output artifacts.

## Validation evidence

- Focused Workbench/service/CLI/UI suite: 17/17 passed.
- Complete smoke discovery: 118 tests passed, seven fixture-dependent skips.
- Plate with through-hole: complete four-format matrix passed.
- HEA 240 with a through web hole: complete four-format matrix passed.
- Arc, custom section, round bar, tamper, migration, undo/redo, save/reopen and
  invalidation regressions passed.

Read-only local duration checks:

| Model class | Size | Evidence | Duration |
| --- | ---: | --- | ---: |
| Largest local STEP sample | 9,224,690 bytes | 1 product, 1 native BREP solid, CAD metrics | 9.852 s |
| Largest local IFC sample | 81,276,651 bytes | 64,015 products, 5,076 solids, semantic strategy A | 8.910 s |

No file under `reference-models` or `reference-models-local` was modified.
The 481 local expected-result records remain `manual_validation_required` and
are not claimed as engineering truth.

Windows Actions run `31720996524` passed source, native roundtrip self-test,
GUI smoke, PyInstaller dist, clean portable extraction, silent installer,
installed runtime without external Python, uninstall and artifact publication.
Artifact `9189885073` is named
`CWS_Convertor_0.8.2-alpha-dev_Windows_x64`, is 671,285,731 bytes and has
artifact digest
`sha256:414ed1c73cdf28d559589ff6f152177233ff6d217ae91635d09773ec57bab916`.

## Explicit remaining limits

- Selected external IFC geometry is triangulated and therefore cannot satisfy
  the exact production-BREP gate without manual or future native-BREP proof.
- Ambiguous multi-solid STEP selection remains blocked.
- Slots, pockets, chamfers and complex end operations are stored but not yet
  rebuilt losslessly.
- Custom cross-sections and explicit arc segments cannot yet be serialized to
  visible NC1 without loss and therefore do not pass the all-format gate.
- The application remains a development snapshot until real engineering
  reference results are manually validated and later release phases pass.
