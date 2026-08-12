# Masterprompt — AI-ondersteunde PDF-, NC1-, IFC- en STEP-converter met automatische werktekeningen

## 1. Rol en opdracht

Neem het bestaande project **NC1 ↔ STEP ↔ IFC Converter** over en breid het product uit met een volledige, bidirectionele tekeningenmodule. Bouw geen losstaand proefproject en vervang de bestaande werkende conversiekern niet. Integreer de nieuwe functionaliteit in hetzelfde canonieke onderdeelmodel, dezelfde profielendatabase, dezelfde materiaalbibliotheek, dezelfde validatielaag, dezelfde viewer, GUI, CLI en Windows-installer.

De applicatie moet twee hoofdrichtingen ondersteunen:

1. **Technische PDF/tekening → NC1/DSTV, IFC en STEP**
2. **NC1/DSTV, IFC en STEP → technische PDF/werkplaatstekening**

De PDF-functionaliteit moet AI-ondersteund zijn, maar de uiteindelijke geometrie, maatvoering, hoeveelheden en productie-export moeten deterministisch worden berekend en gevalideerd. Een taal- of visionmodel mag nooit rechtstreeks ongecontroleerde NC1-regels of productiegeometrie genereren.

Werk zelfstandig door tot een aantoonbaar werkende release. Maak geen claims zonder tests op echte bestanden.

---

## 2. Projectcontext en referentietekening

Gebruik de meegeleverde tekening `Pos LO4 - LOSSE PLAAT.pdf` als functionele en visuele referentie voor een losse onderdelentekening.

De voorbeeldtekening bevat onder meer:

- een losse plaat/strip als primair onderdeel;
- een maatgevoerde hoofdprojectie;
- positie-/onderdeelnummer `LO4`;
- profiel `STRIP5*120`;
- materiaal `S235JR`;
- lengte `160`;
- aantal `4`;
- merk `MLO4`;
- totaalaantal `4`;
- één gat met aanduiding `1*Ø14`;
- twee contourradii `R 13,5`;
- maatketens en totale afmetingen;
- schaal `1:2`;
- A4-formaat;
- een titelblok met project, opdrachtgever, onderwerp, datum, tekenaar en tekeninggegevens;
- een stukregel met de kolommen Pos, Profiel, Materiaal, Lengte, Aantal en Merk.

Gebruik niet automatisch de bedrijfsnaam, projectnaam of vormgeving van deze referentie als universele standaard. Maak de titelblok- en huisstijlvelden configureerbaar per bedrijf. Gebruik de referentie vooral om de gewenste informatiedichtheid, leesbaarheid, maatvoering, onderdeeltabel en bladindeling te begrijpen.

---

## 3. Niet-onderhandelbare ontwerpprincipes

### 3.1 Eén canoniek intern onderdeelmodel

Alle importers en exporters moeten via één canoniek intern model lopen:

```
PDF / NC1 / IFC / STEP
        ↓
Canonical Part Model
        ↓
NC1 / IFC / STEP / PDF / Excel

```

Gebruik geen afzonderlijke, onderling afwijkende geometrische waarheid per bestandsformaat.

### 3.2 AI interpreteert; geometriekern rekent

Gebruik AI voor:

- documentclassificatie;
- titelblok- en tabelinterpretatie;
- herkenning van aanzichten;
- semantische koppeling van maatvoering aan geometrie;
- herkenning van profielbenamingen, materiaalteksten en symbolen;
- conflictdetectie en het formuleren van gerichte controlevragen;
- automatische bladindeling en maatplaatsing als voorstel.

Gebruik deterministische software voor:

- exacte geometrie;
- coördinaten;
- profielopbouw;
- gaten, uitsparingen, radii, bogen en afschuiningen;
- volume, oppervlak, massa en hoeveelheden;
- NC1/DSTV-serialisatie;
- IFC- en STEP-geometrie;
- projecties, zichtbare lijnen en verborgen lijnen;
- maatwaarden;
- roundtripvergelijkingen en exportvrijgave.

### 3.3 Geen stilzwijgend gokken

Kritische ontbrekende of tegenstrijdige gegevens mogen niet worden verzonnen. Bij onzekerheid moet de applicatie:

1. het betreffende element markeren;
2. de waarschijnlijke interpretaties tonen;
3. een confidence-score geven;
4. een concrete vraag aan de gebruiker stellen;
5. productie-export blokkeren totdat het probleem is bevestigd.

### 3.4 Veiligheidscontrole behouden

Behoud de bestaande strikte geometrische veiligheidscontrole. Een bestand mag niet als succesvol worden geëxporteerd wanneer profiel, contouren, gaten, hoofdmaten, volume of kritische metadata buiten de ingestelde toleranties afwijken.

### 3.5 Twee typen PDF onderscheiden

Maak een expliciet onderscheid tussen:

- **Trusted Converter PDF**: een PDF die door deze applicatie zelf is gemaakt en exacte machineleesbare modeldata bevat;
- **External Drawing PDF**: een externe vector-PDF, scan of foto zonder gegarandeerde exacte data.

Een Trusted Converter PDF moet vrijwel lossless opnieuw naar NC1, IFC en STEP kunnen worden geconverteerd. Een externe PDF vereist AI-herkenning en gebruikerscontrole.

---

## 4. Ondersteunde conversierichtingen

Ondersteun minimaal:

```
PDF  → NC1/DSTV
PDF  → IFC
PDF  → STEP

NC1/DSTV → PDF
IFC       → PDF
STEP      → PDF

```

Behoud daarnaast de bestaande richtingen:

```
NC1/DSTV ↔ STEP
NC1/DSTV ↔ IFC
IFC ↔ STEP
IFC/STEP → Excel

```

Ondersteun batchverwerking en meerdere onderdelen per IFC of PDF-set.

---

## 5. Canonical Part Model

Ontwerp een versieerbaar intern model met minimaal de volgende gegevens.

### 5.1 Identiteit en herkomst

- schema-versie;
- onderdeel-ID;
- positie;
- merk;
- projectnummer;
- ordernummer;
- assembly-ID;
- bronbestand;
- bronformaat;
- bronhash;
- importdatum;
- importmethode: exact, vector, OCR, AI of handmatig;
- provenance per veld;
- confidence per veld;
- gebruiker die een interpretatie heeft bevestigd.

### 5.2 Productgegevens

- onderdeelnaam;
- aantal;
- materiaalcode;
- materiaalkwaliteit;
- dichtheid;
- coating/oppervlaktebehandeling;
- profielcategorie;
- profielserie;
- profielbenaming;
- profielstandaard;
- lengte;
- plaatdikte;
- hoofdafmetingen;
- massa per stuk;
- totale massa;
- oppervlakte per stuk;
- totaal oppervlak.

### 5.3 Geometrie

- lokale rechterhandige assen;
- exacte BREP-/solidrepresentatie;
- analytische lijnen, cirkels, cilinders, bogen en vlakken;
- buitencontouren;
- binnencontouren;
- profieldoorsnede;
- uiteinden;
- gaten;
- sleufgaten;
- pockets;
- inkepingen;
- kopbewerkingen;
- afschuiningen;
- laskanten;
- markeringen;
- referentiezijden;
- toleranties.

### 5.4 Tekeninggegevens

- beschikbare aanzichten;
- projectierichting;
- view bounding boxes;
- schaal;
- maatobjecten;
- maatketens;
- annotations;
- symbolen;
- opmerkingen;
- titelblokvelden;
- revisies;
- bladformaat;
- bladnummer;
- templates en huisstijl.

### 5.5 Validatiegegevens

- warnings;
- errors;
- unresolved questions;
- geometrische vergelijking;
- featurevergelijking;
- exportstatus;
- vrijgavegebruiker;
- vrijgavedatum.

---

## 6. Trusted Converter PDF: exacte roundtrip mogelijk maken

Wanneer het programma zelf een PDF maakt, voeg dan naast de zichtbare tekening een machineleesbare laag toe.

### 6.1 In te sluiten data

Neem minimaal op:

- het volledige canonieke onderdeelmodel als versieerbare JSON;
- schema-versie;
- bronhash;
- geometriehash;
- profiel-ID;
- materiaal-ID;
- eenheden;
- onderdeel-ID;
- lijst met features;
- alle relevante oorspronkelijke metadata;
- hash van de zichtbare tekening;
- softwareversie.

### 6.2 Technische opslag in PDF

Gebruik bij voorkeur meerdere mechanismen:

- een embedded/associated file, bijvoorbeeld `converter-model.json`;
- XMP-metadata met schema-versie, part-ID en hashes;
- optioneel de originele bron als ingesloten bestand;
- optioneel een QR-code of compacte identifier die naar een lokaal/online jobrecord verwijst;
- vectorgeometrie in de PDF, geen gerasterde hoofdtekening.

### 6.3 Importprioriteit

Bij PDF-import:

1. controleer of embedded converterdata aanwezig is;
2. valideer schema en hashes;
3. bouw het onderdeelmodel exact uit de embedded data;
4. vergelijk de embedded data met de zichtbare tekening;
5. gebruik AI alleen voor ontbrekende of beschadigde delen.

Markeer zo’n import als `trusted_exact` wanneer alle controles slagen.

---

## 7. External Drawing PDF → NC1, IFC en STEP

Bouw een robuuste hybride importpipeline.

### 7.1 Invoertypen

Ondersteun:

- vector-PDF uit Tekla, AutoCAD, Advance Steel, Revit of andere CAD-software;
- hybride PDF met vectorlijnen en rasterafbeeldingen;
- gescande technische tekening;
- foto van een tekening als conceptmodus;
- enkelvoudige en meervoudige pagina’s;
- één onderdeel per blad en meerdere onderdelen per blad;
- losse onderdelentekeningen en, later, eenvoudige samenstellingstekeningen.

### 7.2 Eerste classificatie

Bepaal per pagina:

- vector, raster of hybride;
- taal;
- eenheden;
- bladformaat;
- oriëntatie;
- schaal;
- tekeningtype;
- titelbloklocatie;
- stuklijstlocatie;
- aantal vermoedelijke onderdelen;
- aanwezige aanzichten;
- kwaliteitsscore.

### 7.3 Vectorextractie

Bij vector-PDF:

- lees lijnen, polylijnen, bogen, Bézierpaden, cirkels, tekst, lijnstijlen, kleuren en lagen uit;
- behoud exacte PDF-coördinaten;
- onderscheid geometrie, maatlijnen, hulplijnen, hartlijnen, verborgen lijnen, kaders en titelblokken;
- groepeer segmenten tot contouren;
- vereenvoudig collineaire segmenten;
- pas cirkel- en boogfitting toe waar tekenpaden gefragmenteerd zijn.

### 7.4 Raster- en scananalyse

Bij scans:

- deskew;
- perspectiefcorrectie;
- ruisonderdrukking;
- lokale contrastcorrectie;
- lijn- en boogdetectie;
- OCR met behoud van bounding boxes;
- herkenning van diameter-, radius-, hoek-, las- en tolerantie-symbolen;
- confidence per herkend teken.

OCR mag alleen tekst voorstellen. De maatwaarde moet vervolgens geometrisch aan de juiste maatlijn en feature worden gekoppeld.

### 7.5 Titelblok en tabellen

Herken en structureer:

- project;
- werk;
- opdrachtgever;
- onderwerp;
- tekeningnummer;
- positie;
- merk;
- profiel;
- materiaal;
- lengte;
- aantal;
- totaal aantal;
- schaal;
- datum;
- tekenaar;
- revisie;
- status;
- algemene notities;
- lasnotities;
- materiaalnotities.

Ondersteun bedrijfsspecifieke titelblokken via configureerbare templates.

### 7.6 Aanzichtherkenning

Detecteer en classificeer:

- vooraanzicht;
- bovenaanzicht;
- onderaanzicht;
- linker-/rechterzijaanzicht;
- doorsnede;
- detailaanzicht;
- isometrisch aanzicht;
- profieldoorsnede.

Koppel aanzichten aan elkaar op basis van orthografische uitlijning, maatvoering, hartlijnen en herkenbare features.

### 7.7 Dimension graph

Bouw een semantische maatgrafiek:

- maatwaarde;
- eenheid;
- tekstpositie;
- maatlijn;
- hulplijnen;
- begin- en eindanker;
- bijbehorende feature;
- maatsoort: lineair, hoek, radius, diameter, booglengte, hoogte, coördinaat;
- tolerantie;
- bronaanzicht;
- confidence.

Controleer maatketens:

- totaalmaten versus deelmaten;
- dubbele maten;
- tegenstrijdige maten;
- ontbrekende ankermaten;
- schaalmaat versus geschreven maat;
- relatieve versus absolute maatvoering.

Geschreven maatwaarden hebben bij externe PDF’s in beginsel voorrang boven gemeten papierschaal, maar alleen wanneer de maatkoppeling betrouwbaar is.

### 7.8 Featureherkenning

Herken minimaal:

- buitencontour;
- binnencontour;
- ronde gaten;
- sleufgaten;
- rechthoekige uitsparingen;
- radii;
- afgeronde hoeken;
- inkepingen;
- kopuitsparingen;
- afschuiningen;
- verzinkingen;
- tapgaten;
- referentie- en hartlijnen;
- markeringen;
- profielzijde.

Verbind dezelfde feature over meerdere aanzichten.

### 7.9 Profielherkenning

Gebruik de profielendatabase om:

- expliciete profielteksten direct te mappen;
- profielen op gemeten doorsnede te herkennen;
- toleranties toe te passen;
- alternatieve matches te tonen;
- confidence te berekenen.

Voorbeeld:

```
Tekst: HEA140
Geometrische match: HEA140
Confidence: 100%
Status: bevestigd

```

of:

```
Gemeten h: 179,8 mm
Gemeten b: 70,2 mm
Gemeten tw: 6,4 mm
Beste match: UPN180
Confidence: 86%
Actie: gebruiker moet bevestigen

```

### 7.10 Interactieve correctie

Toon links de bron-PDF en rechts de gereconstrueerde 2D/3D-geometrie.

Gebruiker moet kunnen:

- lijnen opnieuw classificeren;
- maatteksten aan andere features koppelen;
- contourpunten verslepen of numeriek aanpassen;
- profiel kiezen;
- materiaal kiezen;
- eenheden en schaal corrigeren;
- aanzichttype corrigeren;
- ontbrekende maten invullen;
- onjuiste AI-herkenning afwijzen;
- wijzigingen als bedrijfstemplate opslaan.

### 7.11 Exportstatussen

Gebruik minimaal:

- **Groen — gevalideerd**: alle kritische gegevens bevestigd;
- **Oranje — handmatige controle vereist**: export als concept mogelijk, productie-export geblokkeerd;
- **Rood — onvoldoende bepaald**: geen NC1/IFC/STEP-productie-export.

---

## 8. PDF → NC1/DSTV

### 8.1 Vereiste gegevens

Voor NC1-export moeten minimaal bekend zijn:

- onderdeel-ID/positie;
- profiel of plaatgeometrie;
- lengte;
- eenheden;
- lokale oriëntatie;
- materiaal of expliciete gebruikerskeuze;
- gesloten buitencontour;
- gaten en uitsparingen;
- referentiezijden;
- aantal;
- kritische toleranties.

### 8.2 Schrijfwijze

Schrijf NC1 vanuit het canonieke model, niet vanuit vrije AI-tekst.

Ondersteun relevante DSTV-blokken en profielzijden. Schrijf compacte contouren:

- collineaire punten samenvoegen;
- echte bogen als bogen opslaan waar het formaat dit ondersteunt;
- cirkels niet als honderden segmenten schrijven;
- dubbele features verwijderen;
- consistente lokale assen gebruiken.

### 8.3 Veiligheidsroundtrip

Voer vóór vrijgave uit:

```
Canonical Model → NC1 → opnieuw inlezen → reconstructie

```

Vergelijk:

- profiel;
- lengte;
- buitencontour;
- binnencontouren;
- gaten;
- gatdiameters;
- gatposities;
- zijden;
- volume;
- oppervlak;
- hoofdmaten;
- materiaal;
- aantal;
- onderdeelnummer.

Blokkeer export bij kritische afwijkingen.

---

## 9. PDF → STEP

Maak een echte CAD-solid/BREP, geen STL of uitsluitend triangulated mesh.

Vereisten:

- analytische vlakken, cirkels, cilinders en bogen behouden;
- profiel uit database exact opbouwen;
- features als echte booleaanse bewerkingen modelleren;
- lokale productiecoördinaten consistent toepassen;
- part name, material, mark en projectmetadata opnemen waar STEP-variant dit ondersteunt;
- exportcontrole uitvoeren door STEP opnieuw in te lezen en geometrisch te vergelijken.

---

## 10. PDF → IFC

Maak semantische IFC-objecten en geen generiek meshobject wanneer een betere mapping mogelijk is.

Gebruik waar passend:

- IfcPlate;
- IfcBeam;
- IfcColumn;
- IfcMember;
- IfcBuildingElementProxy alleen als fallback.

Voeg toe:

- GlobalId;
- Name;
- Tag/mark;
- materiaal;
- profiel/type;
- hoeveelheid;
- project/assemblyrelaties;
- Qto-hoeveelheden;
- propertysets;
- bron-PDF en confidence-informatie;
- exacte converterpayload in een eigen propertyset of associated document;
- schema-versie en hashes.

Gebruik analytische of gesweepte geometrie waar mogelijk. Vermijd onnodige triangulatie.

---

## 11. NC1, IFC en STEP → technische PDF

### 11.1 Doel

Genereer automatisch een leesbare, vectoriële werkplaats-/onderdelentekening met maatvoering, aantallen, materiaaleigenschappen, titelblok en relevante aanzichten.

### 11.2 Geometrieanalyse

Bij import:

- herken onderdeeltype;
- bepaal lokale hoofdassen;
- herken profiel en lengte;
- identificeer gaten, contouren, uitsparingen, radii, afschuiningen en uiteinden;
- lees materiaal, onderdeelnummer, mark, aantal en projectmetadata;
- bereken volume, oppervlak en massa;
- bepaal welke aanzichten nodig zijn.

### 11.3 Aanzichtkeuze

Genereer afhankelijk van onderdeeltype:

#### Plaat

- primair vooraanzicht loodrecht op plaatvlak;
- boven- of zijaanzicht om dikte te tonen wanneer relevant;
- detail- of doorsnedeaanzicht voor verzinking, pocket of laskant;
- isometrisch alleen wanneer dit extra begrip geeft.

#### I-, U-, L-, T- of kokerprofiel

- hoofdaanzicht langs de lengte;
- bovenaanzicht;
- zijaanzicht;
- eind-/doorsnedeaanzicht;
- detailaanzichten voor complexe kopbewerkingen;
- optioneel isometrisch overzicht.

#### Rondstaal of buis

- lengteaanduiding;
- eindaanzicht met diameter en wanddikte;
- doorsnede indien nodig;
- gat- en contourdetails.

Onderdruk redundante aanzichten. Voeg geen bovenaanzicht toe wanneer dit exact dezelfde informatie geeft en de tekening daardoor onnodig druk wordt. Voeg het juist wel toe wanneer dikte, profielzijde of bewerking anders niet eenduidig is.

### 11.4 Projecties

Gebruik echte geometrische projecties:

- zichtbare randen;
- verborgen randen als configureerbare streeplijnen;
- hartlijnen;
- symmetrieassen;
- snijlijnen;
- detailverwijzingen;
- lijngewichten per functie.

De tekening moet vectorieel blijven zodat inzoomen scherp blijft.

### 11.5 Automatische maatvoering

Genereer minimaal:

- totale lengte;
- totale breedte;
- totale hoogte;
- plaatdikte;
- profielbenaming;
- gatdiameters;
- gatposities vanaf stabiele referentieranden of assen;
- steekmaten;
- radii;
- hoeken;
- uitsparingsmaten;
- eindbewerkingsmaten;
- profielzijde indien relevant;
- aantallen identieke features, bijvoorbeeld `4× Ø18`;
- toleranties indien bekend.

Regels:

- geef niet dezelfde maat onnodig meerdere keren;
- dimensioneer vanaf stabiele productiereferenties;
- vermijd gesloten/overbepaalde maatketens tenzij als controlemaat gemarkeerd;
- plaats maten buiten de contour waar mogelijk;
- voorkom overlap van tekst, maatlijnen en geometrie;
- groepeer gatpatronen logisch;
- gebruik detailaanzichten wanneer maatvoering anders onleesbaar wordt;
- toon eenheden en decimale precisie volgens bedrijfsinstellingen;
- markeer afgeleide of niet-bevestigde maten op concepttekeningen.

### 11.6 Stukregel en hoeveelheden

Maak een tabel met minimaal:

- Pos;
- Profiel;
- Materiaal;
- Lengte;
- Aantal;
- Merk.

Optioneel configureerbaar:

- massa per stuk;
- totale massa;
- oppervlakte;
- coating;
- revisie;
- assembly;
- zaaglengte;
- opmerkingen.

Toon daarnaast het totaal aantal keer uit te voeren.

Bij IFC met meerdere onderdelen:

- maak optioneel één PDF per onderdeel;
- maak optioneel een gecombineerde PDF-set;
- maak een inhoudsopgave;
- maak een totale stuklijst en hoeveelhedenstaat;
- groepeer identieke onderdelen op profiel, geometrie en materiaal.

### 11.7 Titelblok

Ondersteun configureerbare velden:

- bedrijfslogo;
- project;
- werk;
- opdrachtgever;
- onderwerp;
- tekeningnummer;
- positie;
- status;
- formaat;
- schaal;
- datum;
- getekend door;
- gecontroleerd door;
- revisie;
- projectie-symbool;
- algemene materiaalnotities;
- algemene lasnotities;
- softwareversie;
- bronbestand.

Maak templates per bedrijf en per bladformaat.

### 11.8 Bladformaat en schaal

Ondersteun minimaal A4, A3, A2 en A1, liggend en staand.

Kies automatisch de grootste praktische schaal waarbij:

- geometrie en maatvoering volledig op het blad passen;
- teksthoogte leesbaar blijft;
- titelblok en tabellen niet worden overlapt;
- details voldoende ruimte krijgen.

Laat de gebruiker schaal en formaat forceren. Toon een waarschuwing wanneer het gekozen formaat onleesbaar wordt.

### 11.9 Automatische layout met AI

AI mag voorstellen:

- welke aanzichten worden opgenomen;
- waar aanzichten worden geplaatst;
- welke details apart worden uitvergroot;
- welke maatketens logisch zijn;
- waar maattekst het best past;
- welk bladformaat passend is.

Daarna moet een deterministische layoutengine:

- overlap controleren;
- minimale afstanden handhaven;
- view- en maatbounding boxes berekenen;
- tekstbotsingen oplossen;
- views op raster uitlijnen;
- titelblokruimte reserveren;
- een reproduceerbare PDF maken.

### 11.10 Tekeningstatus

Ondersteun:

- concept;
- ter controle;
- vrijgegeven;
- vervallen.

Concepttekeningen met onopgeloste gegevens moeten zichtbaar een status/watermerk krijgen en mogen niet stilzwijgend als productie-vrijgegeven worden geëxporteerd.

---

## 12. Review- en vergelijkingsinterface

Voeg een tabblad **PDF / Tekening** toe.

### 12.1 PDF → model

Links:

- bron-PDF;
- pan en scrollzoom;
- pagina’s;
- laagfilters;
- OCR-/vectoroverlay;
- herkende titelblokken, tabellen, maatlijnen en aanzichten.

Rechts:

- 2D-reconstructie;
- 3D-model;
- profielweergave;
- featurelijst;
- confidence en waarschuwingen.

### 12.2 Model → PDF

Links:

- 3D bronmodel;
- selecteerbaar aanzicht;
- featureboom.

Rechts:

- live PDF-bladpreview;
- maatvoering;
- titelblok;
- tabellen;
- bladgrenzen;
- printpreview.

### 12.3 Interacties

Ondersteun:

- scrollzoom;
- pan;
- orbit in 3D;
- fit-to-view;
- maat verplaatsen;
- maattekst verplaatsen;
- maat opnieuw ankeren;
- maat verbergen/tonen;
- aanzicht toevoegen/verwijderen;
- detailaanzicht tekenen;
- schaal wijzigen;
- bladformaat wijzigen;
- titelblokvelden bewerken;
- screenshot/PDF-preview;
- undo/redo;
- reset naar automatische layout.

Elke maat in de PDF-preview moet gekoppeld zijn aan een echt geometrisch element. Bij klikken moet de betreffende feature in de 3D-viewer oplichten.

---

## 13. Confidence, provenance en menselijke controle

Geef ieder herkend gegeven:

- waarde;
- bronpagina;
- bronpositie;
- herkenningsmethode;
- confidence;
- status: automatisch, bevestigd, gecorrigeerd of afgeleid.

Voorbeeld:

```
Profiel: STRIP5*120
Bron: stukregel, pagina 1
Confidence: 99%
Status: automatisch herkend

```

```
Gatpositie X: 20 mm
Bron: maatlijn in hoofdaanzicht
Confidence: 84%
Status: gebruiker moet bevestigen

```

Stel drempels configureerbaar in, bijvoorbeeld:

- ≥ 95%: automatisch geaccepteerd indien geometrisch consistent;
- 80–95%: waarschuwing en review;
- < 80%: verplichte bevestiging;
- ontbrekend of tegenstrijdig: exportblokkade.

Een confidence-score alleen is nooit voldoende. Combineer die altijd met geometrische consistentiecontroles.

---

## 14. Validaties

### 14.1 Documentvalidatie

- schaal gevonden;
- eenheden gevonden;
- titelblok gelezen;
- positie/mark gevonden;
- materiaal gevonden of expliciet ingevoerd;
- aantal gevonden;
- alle kritische aanzichten aanwezig;
- alle maatteksten gekoppeld;
- geen tegenstrijdige maatketens.

### 14.2 Geometrievalidatie

- gesloten contouren;
- geen zelfkruisingen;
- gaten binnen materiaal;
- geen dubbele gaten;
- radii geometrisch mogelijk;
- profielafmetingen matchen database;
- plaatdikte bekend;
- hoofdmaten consistent;
- featurezijden bekend;
- geen niet-manifold solid;
- volume positief;
- massa plausibel.

### 14.3 Tekeningvalidatie

- geen overlappende maatteksten;
- geen afgesneden views;
- schaal leesbaar;
- titelblok volledig;
- stukregel consistent met model;
- aantal en totale hoeveelheid consistent;
- alle productiefeatures minimaal eenmaal eenduidig aangegeven;
- geen dubbele of conflicterende kritische maatvoering;
- PDF vectorieel en doorzoekbaar.

### 14.4 Roundtripvalidatie

Test minimaal:

```
External PDF → Canonical Model → NC1 → Model
External PDF → Canonical Model → STEP → Model
External PDF → Canonical Model → IFC → Model

NC1 → PDF → NC1
STEP → PDF → STEP
IFC → PDF → IFC

```

Voor door het programma gemaakte Trusted Converter PDF’s moet de terugweg primair via embedded exact data verlopen.

Vergelijk semantisch en geometrisch, niet byte-voor-byte:

- onderdeel-ID;
- profiel;
- materiaal;
- aantal;
- lengte;
- dikte;
- hoofdmaten;
- aantal gaten;
- gatdiameters;
- gatposities;
- contouren;
- radii;
- volume;
- oppervlak;
- massa;
- lokale oriëntatie;
- kritische metadata.

---

## 15. Specifieke acceptatietest met de voorbeeldtekening

Gebruik `Pos LO4 - LOSSE PLAAT.pdf` als verplichte regressietest.

De importer moet minimaal herkennen en tonen:

- positie `LO4`;
- profiel `STRIP5*120`;
- materiaal `S235JR`;
- lengte `160`;
- aantal `4`;
- merk `MLO4`;
- totaal aantal `4`;
- gatcallout `1*Ø14`;
- twee radii `R 13,5`;
- schaal `1:2`;
- A4;
- onderwerp `LOSSE PLAAT`;
- maatvoering en hoofdcontour uit het getoonde aanzicht.

Controleer expliciet of alle contourmaten voldoende zijn om een gesloten, eenduidige geometrie te maken. Als een dikte, referentiezijde of andere kritische productiedata niet betrouwbaar uit de PDF volgt, moet de software dit vragen en niet zelf verzinnen.

Maak vervolgens:

1. een concept-NC1;
2. een STEP-solid;
3. een semantisch IFC-element;
4. een nieuw gegenereerde PDF-tekening.

Vergelijk de nieuw gegenereerde PDF met de bron op:

- informatie-inhoud;
- maatwaarden;
- gat- en radiusaanduidingen;
- positie-/stukregel;
- schaal en bladindeling;
- leesbaarheid.

De layout hoeft niet pixel-identiek te zijn, maar moet technisch gelijkwaardig en duidelijk zijn.

---

## 16. Bedrijfstemplates en lerend gedrag

Ondersteun per organisatie:

- titelbloktemplates;
- logo;
- standaardnotities;
- maatstijl;
- decimale precisie;
- standaard projectiemethode;
- lijngewichten;
- standaard bladformaten;
- standaard materiaalwaarden;
- profielaliasnamen;
- PDF-importtemplates;
- herkenningsregels voor vaste tekenhoofden.

Sla gebruikerscorrecties als gestructureerde regels op, bijvoorbeeld:

- titelblokveldlocatie;
- tabelkolomnaam;
- profielalias;
- gebruikelijke aanzichtplaats;
- projectspecifieke notatie.

Gebruik correcties niet automatisch als globale waarheid voor andere bedrijven. Houd tenantdata gescheiden.

---

## 17. Lokale AI, cloud-AI en privacy

Ontwerp local-first:

- vectoranalyse lokaal;
- geometriekern lokaal;
- profielendatabase lokaal;
- validatie lokaal;
- NC1/STEP/IFC/PDF-export lokaal.

Ondersteun optioneel cloud-AI voor moeilijke scans en semantische interpretatie, maar alleen na expliciete toestemming.

Vereisten:

- duidelijke melding wanneer bestanden extern worden verwerkt;
- configureerbare dataretentie;
- geen training op klantbestanden zonder toestemming;
- auditlog;
- mogelijkheid om cloud-AI volledig uit te schakelen;
- offline basisfunctionaliteit;
- gevoelige project- en bedrijfsgegevens beschermen.

---

## 18. GUI, CLI en automatisering

### 18.1 GUI

Voeg conversiekeuzes toe:

- PDF → NC1;
- PDF → STEP;
- PDF → IFC;
- NC1 → PDF;
- STEP → PDF;
- IFC → PDF.

Voeg een wizard toe:

```
Bestand kiezen
→ analyse
→ herkende gegevens
→ visuele controle
→ ontbrekende gegevens invullen
→ validatie
→ uitvoer kiezen
→ rapport en bestanden

```

### 18.2 CLI

Ondersteun bijvoorbeeld:

```
converter pdf-to-nc1 input.pdf -o output/
converter pdf-to-step input.pdf -o output/
converter pdf-to-ifc input.pdf -o output/
converter nc1-to-pdf input.nc1 -o output.pdf
converter step-to-pdf input.step -o output.pdf
converter ifc-to-pdf input.ifc -o output/

```

CLI moet JSON-rapportage, exitcodes en batchverwerking ondersteunen.

### 18.3 API/jobmodel

Maak de module geschikt voor later online gebruik:

- job aanmaken;
- bestand uploaden;
- analyse starten;
- vragen/ambiguïteiten ophalen;
- correcties opslaan;
- export starten;
- status volgen;
- rapport downloaden;
- auditlog.

---

## 19. Rapportage

Maak per conversie een rapport met:

- bronbestand;
- uitvoerbestanden;
- gebruikte methode;
- gedetecteerde onderdelen;
- profiel en materiaal;
- aantallen;
- hoeveelheden;
- confidence;
- gebruikerscorrecties;
- warnings en errors;
- roundtripresultaten;
- volume-/oppervlak-/maatverschillen;
- exportstatus;
- softwareversie;
- hashes.

Bij meerdere IFC-onderdelen moet het log per onderdeel laten zien welk NC1-, STEP- en PDF-bestand is gemaakt of waarom een onderdeel is overgeslagen.

---

## 20. Installatie en distributie

De eindgebruiker mag geen Python, pip, virtual environment of terminal nodig hebben.

Lever:

- één Windows-installer-EXE;
- meegeleverde runtime en dependencies;
- portable fallback ZIP;
- automatische installatie van benodigde lokale modellen/data;
- stille of eenvoudige updateoptie;
- SHA-256-checksums;
- duidelijke versie-informatie.

De gebruiker moet de applicatie met één dubbelklik kunnen installeren en starten.

---

## 21. Teststrategie

### 21.1 Unit tests

Test afzonderlijk:

- vectorpadextractie;
- OCR-parsing;
- symboolherkenning;
- maatgrafiek;
- cirkelfitting;
- contourvereenvoudiging;
- profielmatching;
- viewprojectie;
- maatberekening;
- PDF-layout;
- embedded payload;
- NC1/STEP/IFC-export.

### 21.2 Regressietests

Gebruik:

- bestaande NC1- en STEP-dataset;
- bestaande IFC-roundtripdataset;
- `Pos LO4 - LOSSE PLAAT.pdf`;
- extra vector-PDF’s van platen en profielen;
- gescande varianten;
- tekeningen met ontbrekende gegevens;
- tekeningen met tegenstrijdige maten;
- meerdere onderdelen per IFC.

### 21.3 Negatieve tests

Controleer dat export wordt geblokkeerd bij:

- onbekende schaal én onvoldoende maatvoering;
- ontbrekende plaatdikte;
- ambigu profiel;
- open contour;
- conflicterende maatketen;
- onduidelijke gatdiameter;
- onbekende referentiezijde;
- slechte scan;
- beschadigde embedded payload;
- mismatch tussen embedded data en zichtbare PDF.

---

## 22. Definition of done

De uitbreiding is pas gereed wanneer:

1. externe PDF’s aantoonbaar kunnen worden geïnterpreteerd tot een controleerbaar onderdeelmodel;
2. PDF → NC1, STEP en IFC werkt voor minimaal platen en standaardprofielen binnen de afgesproken scope;
3. NC1, STEP en IFC automatisch een technisch bruikbare vector-PDF kunnen genereren;
4. de PDF minimaal relevante voor-, boven-, zij- en/of doorsnedeaanzichten kiest;
5. maatvoering, aantallen, profiel, materiaal, lengte, merk en titelblok worden gegenereerd;
6. Trusted Converter PDF’s exacte machineleesbare data bevatten voor betrouwbare terugconversie;
7. alle exports door roundtrip- en featurevalidatie gaan;
8. onzekere gegevens zichtbaar zijn en productie-export blokkeren;
9. de voorbeeldtekening als regressietest is opgenomen;
10. GUI, CLI en batchverwerking werken;
11. één Windows-installerbestand beschikbaar is;
12. volledige testresultaten, handleiding, checksums en resterende beperkingen worden geleverd.

---

## 23. Verboden shortcuts

Niet doen:

- een PDF alleen als afbeelding naar een AI-model sturen en vrije NC1-tekst laten genereren;
- ontbrekende maten stilzwijgend afleiden zonder waarschuwing;
- ronde gaten als grove polygonen exporteren wanneer een analytische cirkel bekend is;
- een IFC uitsluitend als triangulated mesh opslaan wanneer semantische/swept geometrie mogelijk is;
- een PDF rasteriseren wanneer vectoroutput mogelijk is;
- een tekening als vrijgegeven markeren terwijl kritische gegevens onzeker zijn;
- veiligheidscontroles uitschakelen om tests te laten slagen;
- alleen een mockup of architectuurdocument leveren zonder werkende code en tests.

---

## 24. Op te leveren resultaat

Lever uiteindelijk:

1. complete geïntegreerde broncode;
2. bijgewerkt canoniek datamodel;
3. PDF-importer met vector-, OCR- en AI-laag;
4. PDF-tekeninggenerator;
5. Trusted Converter PDF met embedded exact model;
6. PDF → NC1/STEP/IFC;
7. NC1/STEP/IFC → PDF;
8. GUI en CLI;
9. bedrijfstemplates;
10. validatie- en roundtriprapporten;
11. testbestanden en verwachte resultaten;
12. één Windows-installer-EXE;
13. portable ZIP;
14. gebruikershandleiding;
15. technische documentatie;
16. SHA-256-checksums;
17. een eerlijk overzicht van wat exact werkt en welke beperkingen nog bestaan.

Begin met het analyseren van de bestaande code en testbestanden. Maak daarna eerst het canonieke onderdeelmodel en de Trusted Converter PDF-structuur, omdat die de basis vormen voor een betrouwbare bidirectionele workflow. Implementeer vervolgens de externe PDF-herkenning, de tekeninggenerator en de gebruikerscontrole. Test iedere stap op echte roundtrips voordat je de volgende fase vrijgeeft.