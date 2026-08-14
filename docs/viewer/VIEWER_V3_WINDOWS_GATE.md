# CWS Viewer V3 — open Windows-poort

V3 is lokaal als backend/projectscene gevalideerd. Voor een distributieclaim moeten op Windows x64 nog aantoonbaar slagen:

1. PySide6/QVTK bronstart;
2. packaged PyInstaller onedir-start;
3. portable ZIP opnieuw uitpakken en zonder Python op PATH starten;
4. CasADi/CadQuery/OCP native selftest;
5. echte Qt/VTK projectviewer-smoke;
6. optionele private Tekla-projecttest wanneer de fixture op de runner beschikbaar is;
7. checksums en package-footprint.

Een ontbrekende private fixture wordt als `not_run_missing_private_reference` gerapporteerd, niet als succes.
