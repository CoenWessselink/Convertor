# PDF/UI V3 — hoofdtabbladen en contextbalk, 11 september 2026

## Gecontroleerde uitgangsbron

Branch `agent/cws-pdf-ui-v3-complete-20260909`, commit
`c7724322ed46abafa18d584f378585de76efa85d`, tree
`f05e7850a8e8c9d0ce0469f44cebea4285850a58`.
De werkbron is byte- en modegetrouw uit het bijbehorende GitHub-bronartifact
hersteld. De volledige Git-tree en het commitobject zijn onafhankelijk
gecontroleerd. Er waren lokaal geen bewaarde ongecommitte bronwijzigingen;
losse afbeeldingen uit de eerdere uitvoering zijn geen bronpatch.

De actuele branch is opnieuw uitgelezen vóór de reparatie. Er is geen oudere
UI-branch gemerged. De originele V3-ZIP en alle drie referentiebeelden zijn
opnieuw gelezen; hun rol blijft ontwerpinput, niet runtimebewijs.

## Opnieuw aangetoonde fout

Op 1280 logische pixels met de bestaande zijbalk was het primaire QTabWidget
1091 pixels breed. Het merkblok en de globale snelacties gebruikten samen
812 pixels als corner-widgets. Daardoor had de tabbar slechts 270 pixels:
Project en Viewer pasten, Productie, Controle en Uitvoer niet.
De nieuwe eventgestuurde regressie faalt op de oude bron bij
`Primary navigation fits at 1280 logical pixels`.

Er was ook een afzonderlijke plaatsingsfout: de context-toolbar bleef een
onbeheerd direct child van QMainWindow (100 x 42 pixels op 0,0), waarna
navigatiesynchronisatie hem zichtbaar maakte. Daardoor bedekte schermnummer
01/19 het hoofdmenu. Dat is niet met verbergen van het menu opgelost.

## Productiecorrectie

- De bestaande merk-/historieknoppen en globale selector/snelacties delen een
  eigen compacte rij. Alle vijf primaire tabbladen hebben hun eigen volle rij.
  Knoppen, signalen, tooltips, router en test-identiteiten zijn behouden.
- Een context-toolbar wordt alleen in de expliciete QBoxLayout van de actuele
  leaf-werkruimte geplaatst, nooit in de private layout van een QTabWidget of
  los over QMainWindow. De PDF-werkruimte houdt haar eigen bestaande toolbar.
- Rechtstreekse zijbalk-/tabnavigatie werkt ook het bestaande schermnummer en
  de titel bij, zonder opnieuw te routeren of extra controls aan te maken.
- STEP, IFC, DXF, BOM, nesting, canonieke geometrie, DrawingWorkspacePanel en
  de maatvoerings-/renderauthorities zijn niet vervangen of teruggezet.

## Nieuwe verplichte bewijzen

Dezelfde native Qt-eventtest loopt in de volledige bronapp, one-folder EXE,
verse portable runtime, geïnstalleerde EXE en de onafhankelijke heropeningen.
Bij 1280, 1440 en 1920 **logische** pixels worden tabrectangles, zichtbaarheid,
muisselectie, toetsenbordnavigatie, globale bediening, context-toolbarplaatsing
en behoud van workspace/viewer gecontroleerd. Er wordt per breedte een echte
PNG vastgelegd met test-ID, PID, broncommit en status tot dat meetpunt.

De bron-DPI-suite herhaalt dit bij 100/125/150/175/200%. De distributies herhalen
het bij 100% met dezelfde EXE-hash vóór/na uitpakken en installatie. Dit is geen
claim dat een 1280-logische-pixelvenster op ieder fysiek scherm bij 200% past.

De release-finalizer vereist alle 24 nieuwe benoemde checks in ieder van zijn
acht bron-/runtimegroepen. Een oud groen rapport zonder de navigatiecontrole
kan niet als bewijs worden gebruikt. Bestaande release-/hash-/linter- en
600-seconden-soakvoorwaarden zijn niet versoepeld.

Voor de commit draaiden de nieuwe foutreproductie, gerichte regressies en een
native hoofdvensterproef. Dat zijn werkboomdiagnostics, geen releasebewijs.
De definitieve SHA, aantallen, Windows-run en distributiechecksums worden na
commit opnieuw gegenereerd en staan uitsluitend in de oplevermanifesten.

## Visuele afbakening

De hoofdschil blijft de bestaande CWS-stijl met vijf domeinen en een native
zijbalk. De extra rij kost 38 logische pixels hoogte, maar voorkomt verborgen
primaire navigatie zonder kleinere tekst, horizontale navigatiescroll of
weglaten van acties. De PDF-inspecteur/modelboom blijven inklapbaar. De drie
V3-referenties bepalen de informatiehiërarchie, niet fictieve projectdata of
een vaste groene vrijgavestatus. Machine-/hardwarekwalificatie en ondertekening
blijven buiten deze softwarebeta; historische uitgesloten viewerreferenties
worden expliciet in de testtellingen gerapporteerd.
