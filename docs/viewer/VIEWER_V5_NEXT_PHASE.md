# CWS Viewer V5 — sections en volledige Measure-workspace

## Doel

V5 voegt reproduceerbare snede- en meetfuncties toe boven op de stabiele V4-workspace. Alle meetwaarden komen uit analytische/canonieke geometrie waar beschikbaar. Een displaymesh mag alleen als expliciet gemarkeerde fallback worden gebruikt en moet dan een lagere proof status krijgen.

De Measure-interface verschijnt contextueel en compact, conform de aangeleverde SteelConverter-concepten, zodat het model de centrale werkruimte blijft.

## Werkpakketten

### 1. Sectioning

- één section plane;
- meerdere section planes;
- clipping box;
- plane flip/enable/disable;
- drag handles;
- opgeslagen sectionstate in viewpoint/workspace;
- optionele capweergave, duidelijk als displayfunctie;
- canonical geometry blijft ongewijzigd.

### 2. Display explode en viewer history

- display-only explode offsets per assembly/selection;
- reset en reproduceerbare persistence;
- geen wijziging van canonical placements;
- undo/redo voor camera, visibility, style, section, explode en measurementacties;
- begrensde command history met duidelijke event/auditdiagnostiek.

### 3. Stable measurement anchors

Ieder anker bevat minimaal:

- node-ID;
- canonical entity-ID;
- source entity-ID;
- geometry hash;
- feature/subshape-ID waar beschikbaar;
- world- en local point;
- snaptype;
- proof source: analytical BREP, canonical feature, verified mesh of display proxy.

Bij geometry-hashwijziging wordt een measurement opnieuw gevalideerd of expliciet geïnvalideerd.

### 4. Afstanden

- point-to-point;
- horizontale afstand;
- verticale afstand;
- chain distance;
- point-to-object;
- edge length;
- perpendicular distance;
- perpendicular check.

### 5. Hoeken en helling

- hoek met drie punten;
- hoek tussen lijnen;
- hoek tussen vlakken;
- slope/gradient;
- graden, procent en verhouding waar passend.

### 6. Cirkel- en boogmetingen

- radius;
- diameter;
- arc length;
- chord length;
- center point.

Analytische cirkels/bogen krijgen voorrang. Een polygonale fit wordt als afgeleid getoond met tolerantie en confidence.

### 7. Oppervlak en volume

- face area;
- multiface area;
- area by points;
- projected area;
- total surface area;
- object volume;
- selection volume.

### 8. Tellingen en totalen

- count;
- count by type;
- count by material;
- count by phase;
- count bolts;
- total length;
- total area;
- total volume;
- total weight;
- center of gravity.

### 9. Coordinate picker en snaps

- endpoint;
- midpoint;
- center;
- perpendicular;
- intersection;
- nearest;
- node;
- coordinate picker in world en local production coordinates.

### 10. Measurement workspace

- contextuele compacte toolbar;
- live preview;
- measurement list;
- naam/notitie/status;
- units en precision;
- hide/show/delete;
- selection synchronization;
- workspace/viewpoint persistence;
- CSV/JSON/PDF-reportexport;
- audit van handmatige labels, niet van de geometrische waarde.

## Tests en Golden Model Library

Minimaal analytische fixtures voor:

- rechte plaat;
- plaat met rond gat;
- echte cirkel/cilinder;
- echte boog;
- HEA-profiel;
- D20-rondstaf;
- twee schuine vlakken;
- selection totals;
- transformed instances;
- displayproxy negatieve case.

Vergelijk iedere waarde met een bekende analytische uitkomst en vastgelegde tolerantie. Iedere later gevonden bug wordt een permanente golden regression fixture.

## Harde poort

V5 is pas afgerond wanneer:

- section, explode en viewer history exact opslaan/herstellen;
- alle ondersteunde measurements stable anchors hebben;
- geometry-hashwijzigingen invalidatie veroorzaken;
- units/precision reproduceerbaar zijn;
- analytics en displayfallback zichtbaar onderscheiden zijn;
- canonical/projectdata niet door sections of measurements worden gemuteerd;
- Windows packaged/portable viewer dezelfde berekeningen en UI-smokes uitvoert.
