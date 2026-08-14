# Windows native runtime — harde releasepoort

De echte gebruikersfout `DLL load failed while importing _casadi` is als
regressie vastgelegd.

Wijzigingen:

- `casadi==3.7.2` is een expliciete runtime dependency;
- `CWS_Convertor.spec` verzamelt `casadi`;
- `pyinstaller_hooks/hook-casadi.py` verzamelt package data, submodules en DLLs;
- `pyinstaller_runtime_hooks/cws_native_dll_path.py` voegt packaged native
  directories toe aan de Windows DLL-searchpath;
- `tests/windows_native_runtime_smoke.py` importeert en gebruikt CasADi,
  CadQuery, OCP, PyMuPDF en Matplotlib;
- CadQuery bouwt een box en boort een werkelijk gat;
- de Windows-workflow test source, `dist`, opnieuw uitgepakte portable ZIP en
  geïnstalleerde GUI/CLI zonder Python op `PATH`;
- de windowed GUI schrijft een JSON-smokerapport en moet echt initialiseren.

Deze code is in Linux brongetest. De fout mag pas als definitief opgelost worden
beschouwd nadat een nieuwe Windows Action alle vier runtimevormen groen heeft.
