# CWS Viewer V1 — open Windows/Qt/packagepoort

## Harde acceptatie

V1 is pas definitief vrijgegeven nadat de dedicated Windows-workflow aantoonbaar groen is en de volgende bewijzen fysiek bestaan:

1. PySide6 OCCT-widget start vanuit source;
2. PySide6 VTK-widget start vanuit source;
3. beide backends renderen, clippen, picken en schrijven een screenshot;
4. beide afzonderlijke PyInstaller-onedirbuilds starten;
5. beide opnieuw uitgepakte portable ZIP's starten zonder Python op `PATH`;
6. packagegrootte van beide onedirbomen is gemeten;
7. alle probe-JSON's melden `passed`;
8. checksums zijn gepubliceerd;
9. geen Trimble DLL/EXE/resource is meegeleverd;
10. de test faalt bij een ontbrekende native dependency.

## Waarom deze poort openstaat

De huidige bouwruntime is Linux en bevat geen PySide6 of lokale PyInstaller-installatie. OCCT/AIS is wel in een echt native X-window onder Xvfb uitgevoerd en VTK is offscreen uitgevoerd, maar dat vervangt geen Windows/Qt/PyInstaller-test.

## Workflow

Bestand:

`.github/workflows/viewer-v1-technology-spike.yml`

Verwacht artifact:

`CWS_Viewer_V1_Windows_Technology_Spike`

De workflow bouwt bewust twee afzonderlijke distributies om de marginale VTK-packageimpact ten opzichte van de al aanwezige OCP-runtime meetbaar te houden.

## Releasebesluit

Totdat deze poort groen is, luidt de status:

`conditional-hybrid-selected-windows-gate-pending`

Er mag dan wel verder worden gewerkt aan backend-neutrale V2-corecode, maar de technologie mag nog niet als bewezen Windows-release worden gepresenteerd.
