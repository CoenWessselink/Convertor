# CWS Convertor — Part-First Foundation build 1

## Branch en basis

```text
branch: agent/part-first-foundation-v1
base:   feature/trimble-parity-v15
commit: 6fd8fac7194196aa2fda7e89559000fb5012c926
```

## Vastgelegde productbasis

Deze branch legt de lichte CWS-interface en de Part-First werkwijze vast:

```text
Project → Assembly/Merk → Onderdeel → Handeling
```

Dezelfde `ProjectContext`, `SelectionContext` en `ViewerContext` blijven actief bij wisselen tussen Viewer, Bewerken, Converteren, Controleren, PDF/Tekening, Tekeningen, Scribing, BOM/Hoeveelheden, Rapportage en Exporteren.

De eerste build bevat:

- lichte professionele desktopshell;
- Project Explorer, Viewer, Modelstructuur, Properties en contextworkspace;
- geselecteerd onderdeel met ghosted modelcontext;
- één stabiele part-ID en één selection bus;
- workspace-history en terugschakelen naar Viewer;
- state-acties voor ghost, isolate, show all, section en exportscope;
- unit-/contracttests, UI-smoke en controleafbeelding;
- reproduceerbare Windows GUI-EXE via GitHub Actions.

## Bron uitpakken

De foundationbron staat checksum-geverifieerd in zes kleine bronchunks. Uitpakken naar de repositoryroot:

```bash
python tools/expand_foundation_source.py
```

Verwachte bron-ZIP SHA-256:

```text
068514d04f9b5b6ef5fc5ad28ac68e0e5cef99bbed9050c9cbe37c64adb8e37b
```

## Windows-build

Workflow:

```text
.github/workflows/build-part-first-foundation-v1.yml
```

De workflow voert uit:

```text
checksumcontrole
→ bron uitpakken
→ Python compile
→ 8 unit-/contracttests
→ context-self-test
→ UI-smoke
→ controleafbeelding 1600×900
→ screenshotvalidatie
→ PyInstaller Windows GUI-EXE
→ self-test van de verpakte EXE
→ checksums en artifact-ZIP
```

## Betrouwbaarheidsgrens

Dit is een ontwikkelbaseline waarop de echte Viewer V15 en productiebackends worden aangesloten. In deze build zijn echte IFC/STEP/NC1-import, productie-editing, scribing-engine, converters en machine-uitvoer nog niet als voltooid aangemerkt. Er wordt geen productieclaim gedaan.
