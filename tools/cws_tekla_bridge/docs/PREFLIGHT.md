# CWS Tekla Bridge v0.1 — source authority preflight

Captured on 2026-10-01 UTC, during the build requested at 23:13 Europe/Amsterdam. This freeze records provenance and evidence limits. It grants no engineering, native-write, or production authority.

## Source and branch freeze

- Remote: `https://github.com/CoenWessselink/Convertor.git`.
- Remote default/main HEAD verified by `git ls-remote`: `36bf3d2144716f3deb7f5d1c67b72fe8c1154810`.
- Required remote branch already existed: `feature/cws-tekla-bridge-v0.1`, HEAD `bfdbc99ec33f80d6ce5a2ee629dd494caf767d74`.
- The existing branch was fetched and checked out locally under its exact name. No remote branch, commit, or tag was changed by preflight. The remote documentation branch contains the larger Convertor source tree; main HEAD is a different application tree. Neither branch name grants component authority.
- No `AGENTS.md` exists in the frozen main or required-branch trees. Source changes belong in isolated `tools/cws_tekla_bridge`; existing conversion/viewer code is preserved.
- The three attached full contract prompts are the implementation requirements. The remote branch has shorter summaries that explicitly defer to the start package. Their differing bytes are recorded rather than treated as interchangeable.
- Exact source SHA-256 values, contract hashes, standard references and baseline test evidence are in `source-authority-freeze.json`.

## Current standard checks

The current `CWS_TEKLA_ACTUELE_STANDAARD.json` was read by its known file ID, version 20; `Startinstructie_CWS_Tekla.txt` was read at version 19. Both current records were modified on 2026-10-01 at 15:44 UTC. The selected standard v1.20, complete fault register (79 groups), one-round supplement and FIX19–FIX23 supplement were read in full. Their text bytes including final newline match the SHA-256 hashes declared by the active standard.

The standard preserves the six P01–P06 placement rules and R01–R79 procedure rules. Its stated status is documentation/process authority, not new native execution proof. It explicitly records:

- `complete_native_release=false`, `production_release=false`.
- Generic placement writer and native measurement collector are unimplemented.
- The historical 244 Python tests ran on Linux; they are not a Windows/Tekla proof for this candidate.
- FIX23 is `DIAGNOSTIC_AND_COVERAGE_CORRECTION_NOT_NATIVE_VERIFIED`; Windows installation, native execution, save/reopen, numbering and independent all-object IFC final check are `NOT_RUN`.
- FIX22 failure at unknown ID779667 remains unresolved, and complete cleanup after its final rollback is not proved.
- Project quantities, hardware dimensions and tolerances from 19432 are not general Bridge defaults.

Other mandatory project addenda, placement toolkit, HF3/V29 native reference models and their executable bytes have not been frozen for this generic Bridge build. Their names/hashes in the active standard do not prove their availability, implementation or current execution. Any dependent native workflow must obtain and verify them before granting corresponding authority.

## Upstream reuse assessment

| Component | Schema / role | Current evidence and permitted reuse |
|---|---|---|
| `cws_convertor/steel_model/contracts.py`, `_canonical.py`, `adapter.py` | SteelModel 1.0; Project Model 2.5 read adapter | Deterministic immutable snapshots, source SHA/occurrence trace, entity IDs, relation and geometry/manufacturing hashes. Seven existing foundation tests pass on the frozen source in Linux. Suitable as a contract/reference boundary; this is no native-write proof. |
| `canonical_model.py` | Canonical production payload 1.1 | Keeps explicit manufacturing features and field evidence. Reference only until consumer schema/evidence parity is tested. |
| `project/canonical_rebuild.py` | Rebuild schema 1.0; builder v2 | Reviewed explicit geometry reconstruction; depends on CadQuery. Historical v08 Windows fixture report concerns builder v1 and a synthetic plate, with production gate still blocked. It does not approve the present builder/native Bridge. |
| `manufacturing_interpreter/*` | Versioned geometry interpretation, topology/rebuild/equivalence | Preserve source-gated recognition and evidence. Corpus report says 45 generated categories, 37 REVIEW, 8 BLOCKED, zero ready cases, recall 0.611111; no native Bridge reference proof. Not promoted to write authority. |
| `material_database.py` | Indicative quantity/Excel material library | `find()` defaults to S355JR and ultimately returns the first material. Never use these fallbacks as Bridge production truth. Retain raw material/provenance and require explicit current source or approved scoped normalization. S275JR remains S275JR. |
| Native Tekla/connection components | None present in frozen upstream source | The only Tekla files found are the three contract summaries. No approved native Bridge writer or connection family can be inherited. |

The existing `validation/manufacturing_interpreter_v3/WINDOWS_PACKAGED_ACCEPTANCE.json` labels itself PASS but refers to `validation/phases/PHASE_3_WINDOWS_RUNTIME_EVIDENCE.json` and `release/phase3/PHASE_3_RELEASE_MANIFEST.json`, both absent in the frozen branch. The label is not accepted as verified packaged/runtime authority.

## Dependency and runtime limits

The upstream runtime lock targets Python 3.12 x64 with CadQuery 2.8.0, IfcOpenShell 0.8.5 and PySide6 6.9.2. The available Linux runtime is Python 3.12.14 with CadQuery 2.7.0, IfcOpenShell 0.9.0 and no PySide6. The seven dependency-light SteelModel tests run here do not validate the complete pinned upstream native geometry or Windows UI stack.

The Bridge build uses its separate small C# contract/core, Windows shell and version-bound Tekla adapter. Developer compile references are not a detected user Tekla version. Production runtime must bind to actual running Tekla/assembly identity, validate paths and versions, and fail closed when capability, reference proof or persistence operations are unavailable.

## Remaining hard gates

1. Real Windows x64 start, actual Tekla version/DLL identity and active model/selection readback.
2. Native detail and full rehearsal, atomic complete baseline/unknown-object registration, rollback and protected manual-object checks.
3. Native create/update, save→reopen→independent readback and second identical run with zero duplicates/unintended changes.
4. Het Koraal hard reference gate and a genuinely supplied 20-model source corpus with source hashes, canonical coverage and physical counts.
5. Approved component/detail attributes and joint fingerprints, feature/hole/bolt/weld/connection and clash evidence.
6. Numbering, all-object IFC final comparison and commit-bound Windows installer/release evidence.

These gates remain open unless new, exact-candidate evidence is recorded. Fixture/headless tests, successful API calls or visually plausible screens cannot close them. The runtime authority manifest must ship without approved native writes or connection families until their own evidence is complete.
