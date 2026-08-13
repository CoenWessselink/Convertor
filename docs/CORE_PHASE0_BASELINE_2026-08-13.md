# CWS Convertor core phase 0 baseline

Date: 2026-08-13

Core baseline source: `ba6744a834f79501c4a6a78c65eb8a85c1484d0e`

Working branch: `feature/core-phase-0-baseline`

Product: `CWS Convertor 0.8.1-alpha-dev`

Project Model schema: `2.4`

## Scope and ownership

This is the reproducible baseline for the CWS Convertor main application. It
does not implement or modify the separately owned CWS Viewer. Codex owns the
main application, project model, IFC/STEP import, Part Workbench, canonical
rebuild, production exports, installer and application integration. The viewer
module remains a controlled external handover until its integration phase.

No converter behavior or production output was changed in phase 0.

## Handover integrity

- Handover ZIP: 7,722,412 bytes; SHA-256
  `76063d483fd111b98227f04725b1ed9b7616dcfec492a9207e308449728923e7`.
- Embedded `SHA256SUMS.txt`: 315/315 entries independently verified.
- Supplied master prompt: 95,844 bytes; SHA-256
  `2826b41fbb79eb1027b4ecea7a4839054b39139df5028c827a6703e8cc880e80`.
- Repository prompt: 99,239 bytes; SHA-256
  `0b7142433173c06c4364bcd80b243435fb383bf80a59d61f3dc7670e58a05e87`.
- After line-ending normalization there is one content difference: the
  repository copy identifies the current development snapshot as
  `0.8.1-alpha-dev`; the supplied prompt names `0.8.0-alpha-dev`.

The original `v0.5.1-baseline`, `v0.6.0-beta`, `v0.7.0-alpha` and
`v0.8.0-alpha-dev-codex-handover` tags remain present.

## Environment

- Microsoft Windows 11 Pro, build 26200, x64.
- Intel Core Ultra 9 285K, 24 cores / 24 logical processors.
- 63.34 GiB physical memory.
- CPython 3.12.0 from `.venv/Scripts/python.exe`.
- `pip check`: passed with no broken requirements.
- cadquery 2.8.0; cadquery-ocp 7.9.3.1.1; casadi 3.7.2.
- ifcopenshell 0.8.5; numpy 2.3.5; scipy 1.18.0.
- matplotlib 3.10.8; Pillow 12.3.0; PyMuPDF 1.26.7; pypdf 5.9.0.
- reportlab 4.4.9; XlsxWriter 3.2.9; PyInstaller 6.15.0.

The runtime/build lock files and direct-dependency SPDX SBOM are present and
hashed in the machine-readable report.

## Regression baseline

The unmodified source commit first passed `compileall` and all 30 existing
smoke scripts. After adding the phase-0 baseline contract, all 31 smoke scripts
passed. The suite reports 105 `unittest` cases; custom smoke scripts do not
publish an individual case count and are counted by script.

| Gate | Result |
| --- | ---: |
| Compile all tracked Python | PASS |
| Dependency consistency | PASS |
| Smoke scripts | 31/31 PASS |
| Failed smoke scripts | 0 |
| Known `unittest` cases | 105 |
| Explicitly skipped tests | 9 |

The nine skips are not treated as covered:

- 2 real-file PDF review tests: original `P1811.nc1` fixture not mounted;
- 3 classification reference tests: no validated `.cwscproj` fixture;
- 3 flat reference-file tests: expected `CWS_REFERENCE_ROOT` layout unavailable;
- 1 semantic reference test: the exact required IFC/STEP flat set is incomplete.

The last verified Windows release pipeline for the baseline source is GitHub
Actions run `31699143108`: source, PyInstaller dist, fresh portable extraction,
silent install, runtime without Python on child `PATH`, CLI/GUI conversion smoke
and uninstall all passed. It produced one 640 MB release artifact.

## Reference registry

The repository golden directories are present but contain no public model
binaries. The ignored local registry is supported automatically and currently
contains:

| Format | Models |
| --- | ---: |
| IFC | 5 |
| STEP/STP | 293 |
| DSTV/NC1 | 183 |
| **Total** | **481** |

The corresponding 481 local expected-result files all have status
`manual_validation_required`; zero are marked `validated`. This is deliberate:
existence is not evidence that expected engineering values are correct.

Exact prompt-named files found locally:

- `Samenstel nieuw - 11864_Predeterminado (1).step`;
- `Samenstel nieuw - 11881_Predeterminado (1).step`;
- `Samenstel nieuw - 2x voetplaat hoog.step`;
- `Samenstel nieuw - D1500-0190_Predeterminado (1).step`.

Exact fixtures still missing:

- `TAS_RVB Defensie onderbouw te Leeuwarden- Rev4 [definitief].ifc`;
- `Pos LO4 - LOSSE PLAAT.pdf`;
- `Staalconstructie bordes c04 - Part 18.step`;
- original `P1811.nc1` expected by the legacy PDF review smoke;
- a validated `.cwscproj` classification reference project.

`14542_01.pdf`, `Samenstel nieuw - Part 18.step` and generated
`P1811_3_PLAAT_PL10_130.nc1` are present, but are not silently substituted for
the differently named required fixtures.

## Reproduction

```powershell
.\.venv\Scripts\python.exe validation\run_core_phase0_baseline.py `
  --master-prompt C:\Users\c.wesselink\Downloads\CWS_Convertor_CODEX_MASTERPROMPT_COMPLEET.md `
  --handover-zip C:\Users\c.wesselink\Downloads\CWS_Convertor_CODEX_OVERDRACHT_COMPLEET_v0.8.zip `
  --output validation\results\core-phase0-baseline-windows.json
```

The command uses only standard-library code for evidence collection, writes
JSON atomically and never records confidential local model names or paths.

## Phase 0 decision

The local gate passes with declared fixture gaps. Product naming, compatibility
constants, package boundaries, dependency locks, SBOM, stable error codes,
structured logging/crash reports and Windows packaging already existed in the
baseline. Phase 0 adds reproducible evidence and feature-branch Windows CI.

Phase 1 may start only after this branch also passes the Windows workflow. The
missing validated golden results remain release gates for the phases that use
those models; they are not a reason to fabricate expected values.
