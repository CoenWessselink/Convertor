# CWS Viewer V10 — volgende fase na de V9 Windows-poort

V10 start pas wanneer V9 in de actuele CWS-hoofdbuild is geïntegreerd en de Windows source-, packaged-, portable- en installed-gates aantoonbaar groen zijn.

## Hoofddoel

**Robuuste bron-BREP-isolatie en manufacturing-featuredekking voor echte externe IFC-/STEP-projectonderdelen.**

## Werkpakketten

1. Per-part IFC-representation/placement isoleren met IfcOpenShell/OCCT.
2. STEP occurrence-to-shape mapping voor echte AP242-assemblies en multi-solid bronnen.
3. Exacte, stabiele source-BREP-binding in `.cwscproj` zonder een tweede geometriewaarheid.
4. Analytische herkenning en canonical rebuild voor:
   - platen;
   - I/H/U/L/T-profielen;
   - RHS/SHS/CHS;
   - rondstaaf;
   - holes en slots;
   - notches/copings;
   - chamfers en supported end cuts.
5. Source↔canonical deviation en featurecorrespondence per echte part.
6. NC1/STEP/IFC/Trusted-PDF-roundtrip per ondersteunde partklasse.
7. Representatieve geometrische validatie van de referentiemodellencatalogus.
8. Format-specifieke productiepoort pas per bewezen klasse openen.

## Niet in V10

- handelslengteoptimalisatie;
- plaatnesting;
- machinepostprocessors;
- OPC UA/MES;
- algemene cloudproductie.

Deze modules blijven geblokkeerd totdat de externe manufacturing geometry aantoonbaar betrouwbaar is.
