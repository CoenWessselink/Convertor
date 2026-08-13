# STEELCONVERTER — SUPERPROMPT

## Rol en opdracht
Je bent lead software architect, senior CAD/BIM/geometry engineer, UX engineer en QA engineer. Bouw/verbeter **SteelConverter** als een productiegerichte staalbouwapplicatie. Gebruik alle afbeeldingen in `bijlagen/` als functionele en visuele referentie. De afbeeldingen zijn concepten: neem de bedoelde functies en structuur over, maar corrigeer inconsistenties en bouw geen functionaliteit uitsluitend omdat een gegenereerde afbeelding die toevallig toont.

## Hoofddoel
Maak één betrouwbare workflow van bronmodel naar productie:

**IFC / STEP-STP / DSTV-NC1 / overige ondersteunde bronnen → gevalideerd intern SteelModel → accurate 3D Production Viewer & Editor → BOM/materiaal → tekeningen → optimalisatie/nesting → machine-/productie-export.**

De applicatie is nadrukkelijk **geen vrije CAD-modeler**. Bewerken is parametrisch en productiegericht. Alles moet herleidbaar blijven naar de bron en geschikt zijn om later betrouwbaar productiedata te genereren.

## Belangrijkste ontwerpprincipes
1. **Viewer/import-accuracy eerst.** Nieuwe productiefuncties zijn ondergeschikt aan correcte geometrie en data.
2. **Één centrale waarheid: SteelModel.** Importers en exporters communiceren via dit model, niet via losse pairwise converters.
3. **Non-destructief.** Originele bestanden nooit overschrijven; wijzigingen en revisies traceerbaar houden.
4. **Geen gokken voor productie.** Onbekende/onvoldoende zekere data wordt gemarkeerd als Review/Blocked.
5. **Productiegericht bewerken, geen vrij modelleren.**
6. **Modulair.** Viewer, importers, experts, validation, drawings, nesting en exporters zijn losse modules rond SteelModel.
7. **Simpel in de UI.** Hoofdmenu beperkt houden; functies logisch groeperen in duidelijke submenu's.

# 1. INLEZEN
Ondersteun als architectuur minimaal:
- IFC
- STEP / STP
- DSTV / NC / NC1
- DXF/DWG waar technisch/licentiematig haalbaar
- PDF/tekeningen als document/reference; AI-herkenning is apart en moet gevalideerd worden
- Excel/CSV voor aanvullende data
- later uitbreidbare adapters voor andere formaten

Bij iedere import:
- units expliciet detecteren en normaliseren;
- transforms/lokale en globale assen correct verwerken;
- object-ID/source-ID behouden;
- geometrie, properties, materialen, profielen, assemblies en features afzonderlijk registreren;
- importlog met warnings/errors;
- onbekende profielen niet stilzwijgend vervangen.

## Onbekende profielen
Gebruik meerdere niveaus:
- match op naam/catalogus;
- geometrische herkenning op doorsnede (h, b, tw, tf, radii etc.);
- custom/user-defined profile indien geen catalogusmatch;
- confidence/status tonen;
- gebruiker kan profiel koppelen aan bibliotheek;
- originele geometrie altijd behouden totdat een wijziging bewust wordt bevestigd.

# 2. 3D MODEL & BEWERKEN
Dit is de centrale werkruimte en moet als eerste zeer betrouwbaar worden gemaakt.

## Viewer basis
- snel en stabiel laden van kleine én grote modellen;
- perspectief/orthografisch;
- ISO, voor, achter, links, rechts, boven, onder;
- selecteren en multi-select;
- hide/show/isolate;
- object tree / assemblies / parts;
- zoeken;
- filters;
- lagen/visibility;
- kleuren per materiaal/profiel/status/fase;
- properties panel;
- clipping planes en doorsneden;
- explode view waar nuttig;
- fit model / fit selection;
- undo/redo voor gebruikersacties;
- lokale projectopslag en heropenen.

## Measure
Na keuze **Measure** verschijnen compacte, duidelijke kleine knoppen, zodat het model groot zichtbaar blijft. Minimaal:
- point-to-point distance;
- horizontale/verticale afstand;
- chain distance;
- point-to-object;
- hoek 3 punten;
- hoek tussen lijnen;
- hoek tussen vlakken;
- slope/gradient;
- perpendicular check;
- radius;
- diameter;
- arc length;
- chord length;
- center point;
- area face / multiface / by points / projected / surface;
- volume object / selection;
- count / by type / material / phase / bolts;
- total length / area / volume / weight / center of gravity;
- coordinate picker;
- snap endpoint/midpoint/center/perpendicular/intersection/nearest/node;
- units en precision;
- measurement list + export.

## Productiegericht bewerken
Geen vrije solid modeling. Ondersteun gecontroleerd:
- profiel wijzigen;
- materiaal/kwaliteit wijzigen;
- lengte aanpassen;
- positie/rotatie waar relevant;
- spiegelen/kopiëren waar productie-logisch;
- plaat L/B/dikte wijzigen;
- gaten toevoegen/wijzigen/verwijderen;
- sleuven;
- uitsparingen/copes;
- zaagsneden/kophoeken;
- fasen/lasvoorbereidingen indien semantisch ondersteund;
- merk/positie/assemblygegevens aanpassen;
- eigenschappen wijzigen.

Iedere wijziging moet direct zichtbaar zijn in 3D en in het SteelModel worden opgeslagen met audit trail.

## Scribing
Scribing is een expliciete kernfunctie:
- scribes uit IFC/STEP/assembly-geometrie kunnen voorstellen;
- contactlijnen/aansluitingen analyseren;
- scribe preview in 3D;
- toevoegen/verwijderen/controleren;
- onderscheid tussen scribe/mark en snijbewerking;
- confidence/status;
- nooit ontbrekende geometrie gokken;
- exporteerbare scribe-data voor DSTV/machine-adapters.

# 3. IMPORT- EN VIEWERVALIDATIE — HOOGSTE PRIORITEIT
De viewer moet niet alleen mooi zijn maar aantoonbaar correct.

Bouw een geautomatiseerde validation/regression suite met een groeiende **Golden Model Library**.

Per model/object waar mogelijk controleren:
- objectaantallen;
- source-ID ↔ SteelModel-ID ↔ viewer mesh-ID;
- bounding box;
- volume;
- surface area;
- center of gravity/centroid;
- positie/rotatie/transforms;
- units;
- doorsnede/profielmaten;
- gaten/sleuven/cuts/copes;
- properties/materialen;
- assemblies/hierarchy;
- geometrische fingerprints/hashes waar zinvol.

Gebruik toleranties expliciet en centraal configureerbaar. Maak synthetische referentiemodellen met exact bekende geometrie én echte modellen uit verschillende exporters. Test uiteindelijk honderden/duizenden modellen en voeg iedere gevonden bug als permanente regression case toe.

Maak een **Accuracy/Debug Mode** waarin bij selectie zichtbaar is: source ID, internal ID, mesh ID, units, bounding box, volumeverschil, transformstatus, profile recognition, feature recognition en PASS/WARNING/FAIL.

Trimble Connect of andere bekende correcte viewers mogen als externe functionele/visuele benchmark worden gebruikt, maar kopieer geen proprietary code/assets en reverse-engineer geen beveiligde implementatie.

# 4. MATERIAAL / BOM
- materiaaloverzicht;
- stuklijsten/BOM;
- gewichten;
- profielstatistieken;
- plaatstatistieken;
- las-/boutoverzichten waar brondata betrouwbaar is;
- groeperen op materiaal, profiel, dikte, assembly, fase;
- Excel/CSV/PDF export;
- IFC/STEP → Excel met materiaal, afmetingen, profiel, lengte, gewicht, aantallen, positie, assembly en relevante eigenschappen;
- onbekende/onzekere velden duidelijk markeren.

# 5. INKOOP
Houd eerste versie simpel:
- materiaalbehoefte uit BOM/nesting;
- aanvragen/bestellijst;
- leveranciers;
- offertevergelijking;
- leverstatus;
- restmateriaalvoorraad koppelen.

Geen volledig ERP bouwen; zorg vooral voor export/integratiepunten.

# 6. TECHNISCHE AANSTURING / PRODUCTIEDATA
- fabrication readiness check;
- status per part: READY / REVIEW / BLOCKED;
- DSTV/NC1 genereren vanuit gevalideerd SteelModel;
- STEP/IFC export;
- DXF waar passend;
- labels/barcodes/QR;
- machineprofielen;
- machine compatibility check;
- machine-adapters/postprocessors later modulair toevoegen.

## Machineprofielen
Beschrijf per machine/configuratie:
- fysieke limieten (lengte, profielmaten, gewicht etc.);
- toegestane profieltypes;
- zaaghoeken;
- boren/tappen/sleuven/coping/thermal cutting/scribing/marking;
- bereik per zijde/vlak;
- gereedschappen en diameters;
- ondersteunde bestandsformaten/controllers;
- shop rules naast technische capability;
- software/controller-versie.

Gebruik machineprofielen voor manufacturability en later automatische routing.

# 7. NESTING / OPTIMALISATIE
- profielnesting op handelslengtes;
- zaagverlies/kerf;
- kopverlies;
- reststukkenbibliotheek;
- bestaande reststukken eerst kunnen gebruiken;
- materiaal/kwaliteit/profiel strikt scheiden;
- plaatnesting later/modulair;
- rapportage van rendement, afval en materiaalbehoefte;
- handmatige correctie na automatisch nestvoorstel.

# 8. TEKENINGEN — EIGEN HOOFDMENU
Maak **Tekeningen** een zelfstandig hoofdmenu, niet verstopt onder Technische Aansturing.

## 8.1 Overzichten
- algemeen overzicht;
- constructie-/projectoverzicht;
- materiaaloverzicht;
- montageoverzicht;
- gewichts-/faseoverzicht waar nuttig.

## 8.2 Merktekeningen / samenstellingen
- één assembly/merk per tekening;
- hoofdprofiel standaard horizontaal links→rechts oriënteren voor productie, onafhankelijk van modeloriëntatie;
- automatische hoofd-, boven-, zij- en isometrische views;
- onderdelen/plates/profiles positioneren;
- positienummers;
- lasinformatie waar betrouwbaar;
- bouten/gaten;
- maatvoering;
- stuklijst;
- gewicht/materialen;
- titelblok/revisie.

## 8.3 Onderdeltekeningen
- losse profielen/platen;
- alle relevante productiematen;
- gaten/sleuven/copes/zaagsneden;
- profiel/kwaliteit/dikte/lengte;
- onderdeelnummer/aantal;
- waar nodig meerdere views/doorsneden.

## 8.4 Doorsneden & details
Voor grote/complexe samenstellingen, zoals vakwerkspanten:
- automatisch relevante aansluitingen detecteren;
- per aansluiting detail/doorsnede kunnen genereren;
- correcte maatvoering van platen, boutpatronen, gaten, offsets, profielmaten en relevante lasinformatie;
- detailmarkeringen in hoofdview;
- schaal automatisch passend;
- gebruiker kan detail toevoegen/verwijderen/verplaatsen.

**Belangrijk:** gegenereerde tekeningen mogen nooit verzonnen maatvoering bevatten. Alle maten moeten rechtstreeks uit gevalideerde geometrie/data komen. Bij onvoldoende data: markeer als Review/Blocked.

# 9. COMMUNICATIE / RAPPORTAGE
Houd simpel:
- projectrapport;
- validatierapport;
- productie-/readinessrapport;
- nestingrapport;
- notes/issues;
- wijzigingshistorie/audit trail;
- exports voor ERP/DMS via adapters.

# 10. INSTELLINGEN & DATAMANAGEMENT
- projecten;
- materiaalbibliotheek;
- profielbibliotheek;
- bout/lasbibliotheek waar nodig;
- normen/toleranties;
- machineprofielen;
- gebruikers/rechten indien multi-user;
- backups/versies;
- import/export mappings;
- units/precision;
- lokale opslag als primaire veilige projectoptie; architectuur geschikt houden voor cloud/sync later.

# Gewenste hoofdmenu-structuur
Houd de hoofdnavigatie overzichtelijk. Aanbevolen volgorde:
1. Inlezen / Project
2. 3D Model & Bewerken
3. Materiaal / BOM
4. Inkoop
5. Technische Aansturing
6. Nesting / Machines
7. Tekeningen
8. Rapportage / Communicatie
9. Instellingen

Binnen elk hoofdmenu compacte submenu's/panels. Geen enorme permanente toolbars. Contextuele functies verschijnen pas wanneer relevant, zoals de kleine Measure-knoppen na selectie van Measure.

# Conversies
Doel is vrij kunnen bewegen tussen ondersteunde formaten via SteelModel:
- IFC → STEP
- STEP → IFC
- IFC → DSTV/NC1 waar productiedata voldoende is
- STEP → DSTV/NC1 waar geometrie betrouwbaar geïnterpreteerd kan worden
- DSTV → STEP/IFC waar semantiek reconstrueerbaar is
- IFC/STEP → Excel/BOM
- later aanvullende formaten via adapters.

Maak bij iedere conversie een duidelijk validatierapport: wat is 1-op-1 behouden, wat is afgeleid, wat is onbekend, wat is niet exporteerbaar.

# Teststrategie
1. Unit tests voor parsers/geometry utilities.
2. Golden models per formaat.
3. Cross-format equivalent tests: dezelfde bekende part als IFC/STEP/NC1 moet naar equivalent SteelModel leiden binnen tolerantie.
4. Round-trip geometry tests.
5. Visual regression met vaste camera's.
6. Performance/stress tests op grote modellen.
7. Iedere bug wordt regression test.
8. Geen release als een bestaande golden test verslechtert zonder expliciete verklaring.

# Bouwvolgorde
Werk gefaseerd en voorkom feature creep:

**Fase A — Foundation**
- inventariseer bestaande converter/code;
- definieer SteelModel contract;
- scheid importer / internal model / tessellation / renderer;
- zorg dat bestaande werkende conversie niet verloren gaat.

**Fase B — Viewer & Import Accuracy**
- IFC/STEP/DSTV correct naar SteelModel;
- stabiele viewer;
- measures/properties/tree/sections;
- golden validation suite;
- debug/accuracy mode.

**Fase C — Production Editor**
- productiegerichte edits;
- profile/material/plate/hole/cut/cope;
- scribing;
- audit trail.

**Fase D — BOM & Drawings**
- BOM/Excel;
- overzicht-, merk/samenstel- en onderdeeltekeningen;
- details/doorsneden.

**Fase E — Export & Production**
- betrouwbare STEP/IFC/DSTV exports;
- readiness;
- machineprofielen.

**Fase F — Optimization**
- profielnesting/reststukken;
- plaatnesting;
- machine routing/adapters.

# UX-stijl uit bijlagen
Gebruik de bijlagen als inspiratie voor:
- professionele industriële uitstraling;
- lichte viewer of donkere viewer afhankelijk van context, maar consistent design system;
- veel ruimte voor het 3D-model;
- compacte iconen en contextmenu's;
- rechter properties/selection panel;
- object tree links indien nodig;
- duidelijke statuskleuren voor validation;
- technische tekeningen wit/clean met goede hiërarchie;
- geen overvolle schermen.

# Harde acceptatiecriteria voor eerste mijlpaal
De eerste mijlpaal is NIET “veel functies”. Het is:
- dezelfde bronmodellen laden reproduceerbaar;
- geen stil verdwenen onderdelen;
- correcte units/transforms;
- geometrie binnen afgesproken tolerantie;
- source → SteelModel → viewer traceerbaar;
- onbekende data zichtbaar;
- grote modellen stabiel;
- regressietest automatisch uitvoerbaar;
- viewer betrouwbaar genoeg om als basis voor productieanalyse te dienen.

# Werkwijze voor Codex
1. Inspecteer eerst de bestaande repository volledig en rapporteer architectuur, werkende conversies, risico's en herbruikbare onderdelen.
2. Maak daarna een concreet implementatieplan per fase en bestanden/modules.
3. Verwijder of herschrijf geen werkende convertercode zonder testdekking en duidelijke reden.
4. Werk in kleine commits met beschrijvende commit messages.
5. Voeg tests tegelijk met functionaliteit toe.
6. Rapporteer na iedere fase: wat aangepast is, welke tests draaien, resultaten, performance, openstaande risico's.
7. Gebruik geen tijdelijke mocks in productiepad zonder ze expliciet te markeren.
8. Geen claims van “100% correct” zonder meetbare tests; rapporteer exacte pass/fail/tolerantiegegevens.

## Eindbeeld
SteelConverter moet uiteindelijk aanvoelen als één eenvoudige productieomgeving:

**Open model → controleer in betrouwbare 3D → corrigeer productiegegevens → genereer BOM/tekeningen → valideer → optimaliseer/nest → exporteer/produceer.**

De complexiteit zit in de engines; de gebruiker krijgt een rustige, duidelijke workflow.
