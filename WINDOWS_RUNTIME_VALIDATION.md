# Windows native runtime validation

## Release

- Application: CWS Convertor 0.8.1-alpha-dev
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
- The packaged regression performs an NC1-to-STEP conversion and project create/read cycle.

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

| Environment | Native selftest | GUI smoke | CLI | Project | NC1 to STEP | Python on child PATH |
| --- | --- | --- | --- | --- | --- | --- |
| Source | required | required | required | required | existing regressions | build Python |
| PyInstaller dist | required | required | required | required | required | absent |
| Fresh portable extraction | required | required | required | required | required | absent |
| Installed application | required | required | required | required | required | absent |

The workflow appends its run ID, commit and completed matrix to the copy shipped
inside the release artifact. JSON reports for every environment are included
beside this document, `SHA256SUMS.txt` and `WINDOWS_RELEASE_MANIFEST.json`.
The exact release-file hashes and byte sizes are also published in the GitHub
Actions job summary so they remain inspectable without downloading the artifact.

## Local Windows evidence

On 2026-08-13 the source suite completed 30/30 smoke scripts. The new Windows
build then passed the native selftest, GUI smoke, CLI, project cycle and
NC1-to-STEP conversion independently from `dist`, a fresh portable extraction
and a fresh Inno Setup installation. Python and pip were absent from every
packaged child `PATH`. Silent uninstall removed both executables.

No separate Visual C++ or MinGW installation is requested from the user. The
release is accepted only when all required wheel runtimes are present and the
installed functional checks pass on the Windows runner.
