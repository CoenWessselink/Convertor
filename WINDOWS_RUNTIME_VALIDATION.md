# Windows native runtime validation

## Release

- Application: SteelConverter 0.8.3-beta-dev
- Platform: Windows 10/11 x64
- Runtime: bundled CPython 3.12 via PyInstaller onedir
- External requirements: no Python, pip, virtual environment or manual DLL install

## Root cause

PyInstaller placed `_casadi.pyd` in `_internal`, while its direct non-system
dependencies were placed in `_internal/casadi`. The Windows DLL loader did not
search that package directory when CadQuery imported CasADi. As a result,
`_casadi.pyd` could not resolve `libcasadi.dll` and its bundled MinGW runtime
libraries (`libgcc_s_seh-1.dll`, `libstdc++-6.dll` and
`libwinpthread-1.dll`).

The previous CI run only imported the GUI from source and only started the
packaged/installed CLI on project-only commands. Those CLI commands deliberately
do not load the CAD stack, so a green installer build did not exercise the
failing GUI import chain.

## Structural repair

- `casadi==3.7.2` is pinned in the direct runtime lock.
- `CWS_Convertor.spec` explicitly collects CasADi and uses local PyInstaller hooks.
- `hook-casadi.py` collects the complete wheel, including native plugins and metadata.
- `pyi_rth_casadi_dll_path.py` registers the bundled CasADi directory before app imports start.
- `CWS_Convertor.exe --self-test` executes native and functional runtime checks.
- `CWS_Convertor.exe --gui-smoke` creates the main window, processes the event loop and closes it.
- The packaged regression performs an NC1-to-STEP conversion, project create/read cycle and
  SteelModel/viewer-hostcontract export.
- The native runtime self-test releases and verifies a complete canonical production package.
- The native runtime self-test renders a real triangulated mesh through VTK and
  validates the produced PNG.
- Automated installer validation uses per-user mode, verifies all configured
  file associations and the PDF context action, and then verifies uninstall.

## Native checks

| Stack | Functional check |
| --- | --- |
| CasADi | Load `_casadi.pyd`; evaluate `x*x+1` at 3; require result 10 |
| CadQuery/OCP | Build 100 x 50 x 10 mm plate; drill 10 mm hole; validate solid and volume |
| IfcOpenShell | Create, serialize and reopen an in-memory IFC4 project |
| PyMuPDF | Create, serialize, reopen and read an in-memory PDF |
| Matplotlib | Render a line using the non-interactive Agg backend |
| NumPy/SciPy | Create a native array and calculate a determinant |
| Pillow | Create an in-memory RGB image |
| VTK | Local/package gate: render real geometry and validate PNG; headless GitHub gate: load native rendering modules and execute a polydata/mapper pipeline |

`inspect_windows_native_dependencies.py` additionally reads the PE import table
of `_casadi.pyd`, confirms every direct dependency resolves from the package,
and inventories all packaged `.pyd` and `.dll` files.

The CasADi wheel also ships optional adapters for third-party solvers such as
Knitro, SNOPT, WORHP, HSL, MadNLP and MATLAB. Their vendor DLLs are not part of
CasADi and are not loaded or used by CWS Convertor. The required CasADi core,
CadQuery solver import and bundled open-source runtime are covered by the
functional checks above. Enabling any optional vendor solver later requires a
separate dependency and license gate.

## Required release matrix

The Windows workflow fails unless all of these environments pass independently:

| Environment | Native selftest | GUI smoke | CLI | Project | SteelModel | NC1 to STEP | VTK viewer | Python on child PATH |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Source | required | required | required | required | required | existing regressions | required | build Python |
| PyInstaller dist | required | required | required | required | required | required | required | absent |
| Fresh portable extraction | required | required | required | required | required | required | required | absent |
| Installed application | required | required | required | required | required | required | required | absent |

The workflow appends its run ID, commit and completed matrix to the copy shipped
inside the release artifact. JSON reports for every environment are included
beside this document, `SHA256SUMS.txt` and `WINDOWS_RELEASE_MANIFEST.json`.
The exact release-file hashes and byte sizes are also published in the GitHub
Actions job summary so they remain inspectable without downloading the artifact.

GitHub-hosted Windows runners do not expose a stable interactive OpenGL context;
creating VTK's Win32 render window there can terminate the process before Python
can report an exception. CI therefore validates the bundled native VTK modules
and a real triangle polydata/mapper pipeline without constructing a render
window. The local source, dist, portable and installed-package gates remain the
authoritative pixel-render checks and must produce a valid PNG.

## Local Windows evidence

On 2026-08-13 the `0.8.3-beta-dev` source suite completed 35/35 smoke scripts:
129 tests passed with seven explicit fixture-dependent skips. The prior
`0.8.2-alpha-dev` Windows run `31720996524` passed native selftest, GUI smoke,
CLI, project cycle and NC1-to-STEP conversion independently from `dist`, a
fresh portable extraction and a fresh Inno Setup installation. The current
`0.8.3-beta-dev` packaged matrix passed as run `31728698072` on commit
`b96e58c`, including production-package creation in dist, portable and installed
runtime. Artifact `CWS_Convertor_0.8.3-beta-dev_Windows_x64` has digest
`sha256:e6bf32b4c32bd0ebc226d866eb19d7a156d0fb2823351c623821be36254c9638`.

Phase A run `31734275341` passed on commit `2a80f86`, adding the SteelModel 1.0
and viewer-hostcontract export to dist, portable and installed-runtime checks.
Artifact `9195086063` is 727,107,900 bytes with digest
`sha256:16e69f976d3e0ef916b3dca87c2ed85dc7afad4fa2e45d092aa9008bcbe5e9ab`.

On 2026-08-14 the Phase B batch-2 local Windows matrix passed for source,
PyInstaller dist, a fresh portable extraction and a per-user installation.
All packaged environments passed the seven-check native self-test, visible GUI
smoke and functional package smoke without Python on the child `PATH`; the
installed associations and silent uninstall also passed. The portable ZIP is
454,980,853 bytes with SHA-256
`975cd157e8b7fe9e774f2098285ae7d8e70579aa511e757c963d2b88fe972040`.
The installer is 266,452,047 bytes with SHA-256
`c230a70146a271e5d7f230ecd9a1190941383162da8f1089c2b6c155ecf5a2ed`.
GitHub Windows run `31776351027` passed the complete matrix on commit
`3ec68ed`, including the headless native VTK pipeline, per-user installation,
installed runtime, file associations and uninstall. Artifact `9210399390` is
727,369,191 bytes with digest
`sha256:d893a6869a958f413344459e5a437a99803026fc5f8d308754779a142ddc7cd2`.

On 2026-08-14 the Phase B batch-3 local matrix passed 39/39 source smoke
scripts, then independently passed dist, a fresh portable extraction and a
fresh per-user installation without Python on the child `PATH`. Native VTK,
GUI, project/SteelModel, IFC source geometry, production packages, file
associations and silent uninstall passed. The portable ZIP is 454,996,427 bytes
with SHA-256
`fa590c3c141ca0568526558d6191a4f7a55ed3e0c6935312b5111567e4c62483`.
The installer is 266,487,917 bytes with SHA-256
`0655a7816965fc0b891ba645592839fc26a8324ed03715cfc94714e685621b91`.
The packaged subprocess harness now tolerates mixed Windows console encodings
without hiding nonzero exit codes or file-based runtime assertions. GitHub
Windows validation for this batch remains pending until the source commit is
pushed.

No separate Visual C++ or MinGW installation is requested from the user. The
release is accepted only when all required wheel runtimes are present and the
installed functional checks pass on the Windows runner.
