# Read-only Foundation / Project Model handover

The Bridge source reader must preserve the existing engine's identities, material text, revision hashes and explicit geometry evidence. Loading a document is a read/proposal operation. It cannot approve profile, material, geometry, connections or native writes.

The frozen Python implementation is the source for these contracts. `python tests/steel_model_foundation_smoke.py` passed 7 tests on baseline `bfdbc99ec33f80d6ce5a2ee629dd494caf767d74`. An additional nine-check synthetic source probe passed; see `source-fixtures/source-handover-report.json`. These are Linux read-contract checks, not Tekla tests.

## SteelModel 1.0

Create the handover from the existing persisted Project Model through the upstream `build_steel_model_snapshot(project)` or existing CLI `project-export-steel-model`. Read upstream `SteelModelSnapshot.from_json_bytes()` to validate the native format when Python is available. This checks duplicate IDs, source existence/hash consistency, relation targets and the snapshot checksum.

| Native field | Bridge read behavior |
|---|---|
| `schema_version` | Require supported `1.0`. Do not identify this contract from a filename. |
| `project_id`, `project_semantic_sha256`, `snapshot_sha256` | Retain project/revision/snapshot identity separately from original source-file hashes. The snapshot hash covers every content field except itself. |
| `sources[]` | Retain exact source IDs, format, SHA-256, import/analysis status and existing production flags; flags alone never grant new Bridge authority. |
| `entities[].steel_model_id` | Preserve canonical engine identity. Keep all entity roles for traceability; only `entity_type=part` enters a part plan. |
| `entities[].source` | Preserve source-file/entity/global/product/occurrence IDs and the exact source hash. Identical geometry at distinct occurrence IDs remains distinct. |
| `local_transform`, `global_transform` | Preserve all 16 finite matrix values and declared units/coordinate system. No centering, axis rotation, shortening or beam endpoint derivation while loading. |
| `geometry_kind`, `geometry_hash`, `manufacturing_hash` | Preserve identifiers/evidence. These are hashes, not solid/contour/feature payloads. |
| `accuracy_status` | Preserve source status; `exact` is not an approved Bridge authority record. |
| `display_properties.profile`, `.material`, `.material_grade`, `.part_position` | Preserve explicit text. Missing values remain missing. No MaterialDatabase fallback or grade conversion. |
| `relations[]`, `validation[]`, `validation_issue_codes` | Retain for audit/dependency planning; unresolved issues remain visible and cannot be silently resolved. |

**Geometry limit:** SteelModelSnapshot has no BRep, endpoints, contour points, hole definitions, workbench features or canonical payload. A reader must not create a beam from `length_mm` plus a transform, or fabricate a plate from display properties. Kind/geometry remain unresolved for native writes unless a separately versioned, validated geometry handover supplies the explicit payload and its evidence.

Snapshot hashing uses Python's `_canonical.py`: recursively sorted mapping keys, finite floating-point values rounded to 9 decimals, compact UTF-8 JSON, Unicode retained, no NaN. Cross-language verification must match numeric serialization and sorting; parsing success alone is not checksum verification.

## Project Model 2.5 JSON

`ProjectModel.to_dict()` produces keyed dictionaries for `sources` and `parts`, not arrays. The existing `.cwscproj` container is handled by `ProjectStore`; a plain JSON reader must not pretend the zipped/persisted format is plain JSON. Export a validated JSON representation through the existing source engine when needed.

| Native field | Bridge read behavior |
|---|---|
| `parts[internal_id]`, `.internal_id` | Dictionary key and stored ID must agree; retain the native identity. |
| `.source_identity` | Retain format, exact SHA, source/entity/GUID/product/occurrence/mark trace. |
| `.field_provenance`, `.revision`, `.validation_issues` | Keep independent from display confidence or normalized labels. |
| `.material`, `.material_grade`, `.normalized_material` | Preserve distinct values and provenance. A normalized field is not approved authority. The source probe confirms S275JR remains S275JR. |
| `.profile`, `.profile_type`, `.normalized_profile`, `.profile_confidence` | Retain explicit evidence and conflicts. Confidence does not substitute for family/profile validation. |
| `.canonical_part` | Preserve explicit CanonicalPart 1.1 payload, including header, contours, holes and field evidence. Do not assume all payload forms have a proven Tekla representation. |
| `.geometry_descriptor`, `.production_features`, `.workbench` | Preserve full original payload separately from Bridge DTO convenience fields. In particular, do not discard workbench contour/feature definitions. |
| `.local_placement`, `.global_placement`, project `units` / `coordinate_system` | Preserve explicit source placement and units. Native writing requires a validated source→Tekla coordinate contract. |
| `.assembly_ids`, `assemblies`, `fasteners`, `welds` | Preserve relationship evidence; assembly membership is not proof of a weld or connection family. |

The source probe roundtrips ProjectModel JSON through the upstream class and confirms explicit contour/hole payload survival, two distinct occurrences, exact S275JR, nonmutating snapshot creation and tamper/source-hash rejection. The supplied fixture is clearly `TEST_FIXTURE_ONLY`; it is not Het Koraal, a corpus member or a native reference model.

## Fail-closed handover rules

Reject unsupported schema, duplicate/conflicting IDs, wrong source hashes, invalid snapshot checksum, nonfinite/malformed transform and inconsistent identity. Surface missing material, unknown profile/geometry, missing original source and unresolved source issues as review/block reasons. A valid read-only handover may still have zero approved native writes. Keep proposed interpretation separate from the unmodified original payload.
