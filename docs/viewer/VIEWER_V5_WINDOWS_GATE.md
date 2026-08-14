# CWS Viewer V5 Windows gate

Local Linux validation does not prove the Windows desktop package. The workflow
`.github/workflows/viewer-v5-measurements.yml` must pass before any Windows EXE
or portable ZIP is claimed.

Mandatory checks:

1. all source smokes and V5 validation;
2. CasADi symbolic operation;
3. CadQuery box and drilled solid;
4. OCP, IfcOpenShell, PyMuPDF and ReportLab imports;
5. VTK offscreen render;
6. real PySide6 Measure dock start;
7. PyInstaller onedir self-test and GUI smoke;
8. portable ZIP retest with Python removed from PATH.

Current local status: **pending Windows runner**.
