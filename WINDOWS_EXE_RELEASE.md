# SteelConverter 0.8.3-beta-dev - Windows x64 release

## Target artifacts

```text
CWS_Convertor_Setup_0.8.3-beta-dev_x64.exe
CWS_Convertor_Portable_0.8.3-beta-dev_x64.zip
SHA256SUMS.txt
WINDOWS_RUNTIME_VALIDATION.md
```

The end user needs no Python, pip, virtual environment, developer tools or
manual DLL installation.

## Release gates

The Windows build runs all source regressions and then validates four distinct
environments: source, PyInstaller `dist`, a freshly extracted portable ZIP and
the silently installed application. Packaged child processes receive a system
only `PATH` without Python or pip.

Every packaged environment must pass:

1. CasADi native import and symbolic expression;
2. CadQuery/OCP solid, bounding-box and boolean-hole operation;
3. IfcOpenShell in-memory roundtrip;
4. PyMuPDF and Matplotlib rendering checks;
5. actual GUI construction and event-loop processing;
6. CLI version and project create/read;
7. actual NC1-to-STEP conversion.
8. canonical NC1/STEP/IFC/Trusted-PDF release package creation and checksum verification.
9. SteelModel 1.0 and viewer-hostcontract export from an installed project.

The complete technical matrix is documented in `WINDOWS_RUNTIME_VALIDATION.md`.

## Installer behavior

The Inno Setup installer copies the self-contained PyInstaller onedir runtime,
creates optional file associations and installs an uninstaller. It does not
download Python, CasADi, redistributables or DLLs at installation time.

## Superseded build

CI run `31685684421` for version `0.8.0-alpha-dev` is superseded and must not be
distributed. It proved source GUI construction and packaged project-only CLI
commands, but did not start the packaged GUI or load the installed CAD stack.
The reported `_casadi` crash exposed that missing acceptance gate.

Version `0.8.3-beta-dev` is releasable only after its workflow is fully
green. The artifact copy of `WINDOWS_RUNTIME_VALIDATION.md` records the exact
run ID and commit, while `SHA256SUMS.txt` records both deliverable hashes.

Accepted Windows validation: run `31728698072`, commit `b96e58c`, artifact
`CWS_Convertor_0.8.3-beta-dev_Windows_x64`, digest
`sha256:e6bf32b4c32bd0ebc226d866eb19d7a156d0fb2823351c623821be36254c9638`.

Phase A validation supersedes that packaged baseline: run `31734275341`, commit
`2a80f86`, artifact `9195086063` (`CWS_Convertor_0.8.3-beta-dev_Windows_x64`),
727,107,900 bytes, digest
`sha256:16e69f976d3e0ef916b3dca87c2ed85dc7afad4fa2e45d092aa9008bcbe5e9ab`.
