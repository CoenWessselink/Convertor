# U0 Unified Baseline Audit

Status: **FROZEN FOR INTEGRATION**  
Phase: `U0 - Three-Baseline Forensic Freeze`

## 1. Active GitHub integration authority

- Repository: `CoenWessselink/Convertor`
- Source branch: `feature/trimble-parity-v15`
- Frozen source HEAD: `6fd8fac7194196aa2fda7e89559000fb5012c926`
- Commit message: `fix(viewer): scale contact shadow radius to model size`
- Integration branch created from that exact HEAD: `feature/unified-v15-scribing-m18`

### Viewer baseline

- Product line: CWS Viewer V15
- Version: `1.4.0-v15-preview.2`
- Handling contract: `1.2-trimble-feel-v2`
- Viewer remains the visual/navigation/selection/review basis of the unified CWS desktop.
- Canonical Project Model remains the only project/manufacturing truth.

### Convertor baseline

- Application version: `0.9.0-alpha-dev`
- Current Project Model schema: `2.5`
- Current integrated desktop: PySide6/VTK primary; legacy Tk is compatibility fallback only.
- Current source still exposes visible `APP_NAME = SteelConverter`; product-name unification is recorded as later integration work and must not break legacy payload identifiers.

### Current manufacturing overlap already present on GitHub

The active GitHub line already contains manufacturing modules for at least:

- Manufacturing Faces / face-local frames / DSTV mapping contract
- Contact Geometry
- Marking / Scribing
- Identification / hole-reference intent
- Machine Capability
- Nesting Mark Binding
- Independent nesting validation
- Neutral Manufacturing Job / operation DAG
- Viewer manufacturing overlays and manufacturing/export CI gates

Therefore M1-M8 from M18 must be semantically reconciled, **not copied over file-for-file**.

## 2. Scribing M18 frozen authority donor

Input delivery inspected locally:

`CWS_Convertor_Scribing_M18_DELIVERY_0.8.30-beta-dev.zip`

Outer delivery SHA-256:

`886dc6aa0a2586d0196e708bebfe3fb6be293de7adde0087fb4bbfe4d8b66737`

Frozen M18 identity from the delivery:

- Product: `0.8.30-beta-dev`
- Project Model: `2.24`
- Source commit: `b04b1c203583295e8c5ed018d75de68b2319c839`
- Tag: `scribing-m18-deployment-assurance-0.8.30-beta-dev`
- M18 contract: `1.0`
- Recorded positive checks: `486`

Verified physical artifacts inside the delivery:

- Git bundle SHA-256: `f2ab5e29eaee93cb69677ce99b5e76a137adb1a4125e5aea6790af49e70af7c1`
- Source ZIP SHA-256: `6ab1fc4819245763e38c8b5c9fb4a1654648ba168f78f54c540c89b89dd503be`
- Safe project SHA-256: `5d13e86fc6d40996b29af5d4a68fd77c09b66b19c1817d3016d9b35529635afa`
- XLSX SHA-256: `bc15903f2851c8f17f1c154bc83653a226cb4ecfe963cb57dce61c0d6d543347`
- PDF SHA-256: `a148f1a798101525ee551790d765a195d95d205e5b642c52967238a48b2b99bc`

All five hashes match `M18_FINAL_FREEZE.json` / `SHA256SUMS.txt`.

The M18 source commit/tag is **not present in the current GitHub repository history**. M18 is therefore treated as an external frozen authority donor to be ported/reconciled into the current integration line, not as a branch to reset GitHub to.

## 3. Safety boundary frozen

The unified work must preserve:

```text
machine_observed_by_cws = false
deployment_transport_authorized = false
direct_machine_transfer = false
machine_transfer.allowed = false
```

No integration phase may silently weaken these values.

## 4. CI baseline

On the frozen V15 HEAD:

- Standalone CWS Viewer V15 Windows x64 workflow: successful.
- Viewer V15 T8 manufacturing geometry gate: successful.
- Viewer V15 manufacturing/scribing/export gates exist on the active branch.
- Existing `build-windows-integrated-v9.yml` has **0 runs on `feature/trimble-parity-v15`** because its branch triggers still target older integration branches.

This is a known U4 integration task; U0 does not change CI behavior.

## 5. UX authority

Target product flow is frozen as:

```text
Inlezen
→ Viewer (Project)
→ Bewerken
→ Converteren
→ Controleren
→ PDF / Tekening
→ Tekeningen
→ Scribing
→ Hoeveelheden / Excel
→ Exporteren
```

Viewer V15 is the central visual/context workspace. Switching tools must retain the same project/entity IDs, selection and canonical project instance.

## 6. Project schema finding

There is a real integration boundary:

- current GitHub: Project Model `2.5`
- frozen M18: Project Model `2.24`

Because the schema versions are numeric dotted versions, `2.24` is later than `2.5`; neither source may simply overwrite the other.

Planned U1 target: **Project Model 2.25**, subject to the U1 schema-field/migration audit.

Required migration paths:

```text
2.5  -> 2.25
2.24 -> 2.25
```

No geometry/manufacturing hash changes are allowed from schema migration alone.

## 7. U0 gate decision

**PASS for starting U1.**

The three baselines are sufficiently identified to begin contract/schema reconciliation without downgrading or overwriting either development line.

Next phase:

`U1 - Canonical Project Model & contract reconciliation`
