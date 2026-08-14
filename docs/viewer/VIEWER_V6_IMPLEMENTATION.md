# CWS Viewer V6 — Exact Part Workbench implementatie

## Identiteit

- package: `cws_viewer 0.7.0-dev0`
- Viewer API: `0.4.0`
- viewer workspace: `1.1`
- branch: `feature/cws-viewer-v6-exact-workbench`
- Windows packaged/portable gate: **nog uit te voeren**

## Doel en architectuurgrens

V6 sluit de opening tussen een zichtbaar projectobject en een controleerbaar exact productieonderdeel. De viewer werkt met twee gescheiden representaties:

```text
exact source BREP
        +
canonical manufacturing BREP
        ↓
Exact Part Workbench
        ↓
review + compare + roundtrip evidence
        ↓
format-specifieke gate
```

VTK-tessellatie en OCCT/AIS-presentatie zijn afgeleide weergaven. Zij zijn nooit de productiewaarheid. De viewer kan geen productie vrijgeven en kan geen machinecode genereren.

## Gebouwde onderdelen

### 1. Exact BREP-catalogus

`cws_viewer/exact/catalog.py` levert:

- exact STEP/BREP laden via CadQuery/OCP;
- OCCT-validiteit, volume, oppervlak, massa-eigenschappen en bounding box;
- stabiele IDs voor solids, faces, edges en vertices;
- analytische herkenning van vlak, lijn, cirkel, boog, cilinder en kegel;
- rechterhandige lokale productieassen;
- automatische referentievlakvoorstellen;
- analytische features met provenance en confidence;
- expliciete blokkade voor multi-solid/ambigu bronmateriaal.

### 2. Begrensde canonical builders en editor

Ondersteund en getest:

- rechthoekige plaat;
- ronde doorlopende gaten;
- gesloten samengestelde polylinecontour;
- echte contourbogen/radii;
- analytisch sleufgat;
- rondstaaf/cilinder;
- gecontroleerde wijziging van plaatafmetingen en ronde gaten;
- manufacturing hash, audit en undo/redo.

Dit is geen vrije CAD-modeler. Niet-ondersteunde pockets, copes, chamfers en end cuts blijven geblokkeerd.

### 3. Exact snapping

Stabiele ankers zijn beschikbaar voor:

- endpoint;
- midpoint;
- center;
- perpendicular;
- line intersection;
- nearest exact subshape.

Een anker bewaart object-/subshape-identiteit, geometry hash, wereld- en lokale coördinaat en bewijsniveau.

### 4. Native OCCT/AIS-selectie

`OcctExactPartBackend` ondersteunt:

- source/canonical overlay;
- face-, edge- en vertexselectiemodi;
- mapping van gedetecteerde `TopoDS_Shape` naar stabiele CWS-ID;
- selectiehighlight;
- fit en standaardaanzichten;
- native screenshotcapture.

### 5. Review en persistence

- productieframe bevestigen of gecontroleerd vervangen;
- reference faces per rol bevestigen;
- reviewer en reden verplicht;
- atomische `.cwspartreview.json`;
- interne statehash en externe SHA-256-sidecar;
- unresolved questions blijven zichtbaar;
- wijziging van canonical data wist eerdere compare-/roundtripstatus.

### 6. Exacte source/canonical vergelijking

Vergelijkt minimaal:

- volume;
- oppervlak;
- solid/face/edge/vertex count;
- hoofdmaten;
- source→canonical en canonical→source max. afstand;
- analytische features.

De vergelijking gebruikt echte OCCT-edge samples. Een displaymesh kan het resultaat niet beïnvloeden.

### 7. Formaatroundtrips

Voor de gevalideerde plaatklasse:

```text
canonical → STEP → exact runtime
canonical → NC1 → STEP → exact runtime
canonical → converter-owned IFC → STEP → exact runtime
canonical → Trusted PDF → STEP → exact runtime
```

De vergelijking wordt uitgevoerd in genormaliseerde lokale productiecoördinaten. P1811 en een asymmetrische plaat zijn via alle vier routes gevalideerd.

### 8. Scribing review

`cws_viewer/exact/scribing.py` voegt een veilige eerste scribinglaag toe:

- exacte contactlijnen via OCCT BREP-section;
- stabiele proposal-ID's;
- uitsluitend `scribe`/`mark`, nooit stilzwijgend `cut`;
- 3D-preview;
- proposed/confirmed/rejected status;
- reviewer, reden en audit;
- JSON-export met checksum;
- geen wijziging van target- of partner-BREP;
- geen productievrijgave of machine-output.

Een multi-solid target/partner blijft geblokkeerd en een geometrisch gescheiden partner levert geen gegokte lijnen op.

## Qt-interface

`ExactPartWorkbenchPanel` bevat een echte OCCT-native-windowkoppeling met functionele data voor:

- Geometrie;
- Bewerkingen/features;
- Assen en referentiezijden;
- Algemeen;
- Herkomst en validatie.

De uitgebreide bedrijfstabbladen voor prijzen en bewerkingstijden blijven bij het hoofdproject-/productiemodel en worden niet als lege viewerfuncties nagebouwd.

## Gevalideerde scope

- P1811-plaat met vier Ø18-gaten;
- Ø18→Ø20 wordt geblokkeerd;
- D20 rondstaaf;
- HEA140 exact source-BREP en stabiele subshape-selectie;
- plaat met echte R13,5-bogen;
- plaat met analytisch 18×50-sleufgat;
- gesloten niet-rechthoekige plaatcontour;
- multi-solid bron blijft geblokkeerd;
- exacte scribingcontactlijnen zonder geometriewijziging;
- P1811 en asymmetrische plaat via STEP, NC1, IFC en Trusted PDF.

## Bewuste beperkingen

- algemene isolatie van één exact BREP uit ieder willekeurig extern IFC-projectobject is nog niet voltooid;
- HEA/I/U/L/T/CHS/RHS-catalogusrebuild met alle bronradii is nog niet vrijgegeven;
- pockets, notches, copes, chamfers, laskanten en complexe end cuts zijn niet algemeen ondersteund;
- stabiele subshape naming over willekeurige topologiewijzigingen blijft een V7-onderwerp;
- scribing is reviewdata; DSTV-/machine-adapters volgen pas na hun eigen validatie;
- dynamische Windows/PySide6/PyInstaller-validatie staat nog open;
- de viewer kan geen productievrijgave geven.
