# Changelog

## v0.3.0

- Conversiekeuzemenu uitgebreid met IFC → DSTV, DSTV → IFC, IFC → STEP en STEP → IFC.
- Nieuw tabblad **Hoeveelheden & Excel**.
- Viewer uitgebreid: assen verborgen, scrollzoom, meten, snede, bbox, display modes, screenshot en info-copy.
- Profielendatabase uitgebreid naar 1.718 profielen.
- Zoek-, familie- en typefilters toegevoegd aan de profielendatabase.
- IFC/STEP-bestandsfilters toegevoegd voor conversie en hoeveelheden.
- IFC → DSTV schrijft meerdere NC1-bestanden en een manifest; GUI/CLI loggen alle outputs en niet-converteerbare objecten.
- CLI uitgebreid met alle conversierichtingen en Excel/quantity commands.
- requirements.txt aangevuld met IfcOpenShell en XlsxWriter.
- Windows EXE-buildscript uitgebreid met materialen, profielen, IfcOpenShell en XlsxWriter.
- GitHub Actions Windows-build uitgebreid met regressietests en EXE-artifact.
- Regressietests opnieuw uitgevoerd op aangeleverde NC1/STEP-set.

## v0.2.0

- STEP → NC1 uitgebreid naar standaardprofielen via profielendatabase.
- Visuele vergelijking links/rechts toegevoegd.

## v0.1.0

- Eerste lokale NC1 → STEP en beperkte STEP → NC1 prototypeversie.
