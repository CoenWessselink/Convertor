# BOM-tekenbatch en PDF-reviewregressie — 11 september 2026

## Basis en bereik

Gerichte voortzetting van `483fe1813967452dc7d83667150960e001adffda` op
`agent/cws-pdf-ui-v3-complete-20260909`. Vóór de push bleek de branch
doorgeschoven naar `21e1b56fc77591a438e9695c2b1a8d7fe5d42c4f`.
Alle acht tussenliggende commits, waaronder artifact-identiteit, exacte
reviewexports, hun geïnstalleerde bewijsgates en de invoerschaalreparatie,
zijn behouden. De batchwijziging is daarop zonder conflicten toegepast
en opnieuw getest. Geen oudere UI-branch overgenomen, geen vervangende
applicatie of tweede tekenengine gemaakt.

Dit pakket implementeert de bestaande `drawing.batch_pdf`-actie uit W03/W18.
Het sluit niet de volledige matrix van 87 BOM-acties, batchgoedkeuring,
machineafname of alle 35 gapanalysewerkpakketten.

## Herstelde bestaande regressie

Windows-run 34631058867 faalde in `pdf_review_smoke` en
`review_workflow_smoke`: de automatisch gedetecteerde invoerschaal werd
onbedoeld als vaste schaal voor een anders ingedeeld uitvoerblad gebruikt.

De lokale correctie is niet over de gelijktijdige upstream-reparatie gelegd.
De behouden implementatie van `21e1b56f` slaat de invoerschaal op onder
`properties.source_drawing` en begint nieuwe review-uitvoer met Auto.
Expliciete menselijke wijzigingen aan `drawing.scale` blijven strikt;
een niet-passende vaste uitvoerschaal blijft een fout. De bijbehorende
upstream-provenance- en fysieke-schaaltests blijven ongewijzigd behouden.

## Werkelijke tekenbatch

- De bestaande BOM-actie maakt een gecombineerd vector-PDF én afzonderlijke
  object-PDFs met bladwijzers en een controlemanifest.
- Exact geselecteerde canonieke object-IDs blijven behouden, ook wanneer een
  BOM-regel meerdere gelijk gemerkte onderdelen/assembly-occurrences bevat.
- Een geselecteerde assembly blijft een assembly met alle traceerbare
  componenten. Een ontbrekend noodzakelijk component blokkeert de hele batch.
- Ieder object gebruikt zijn eigen opgeslagen DimensionDocument, maatstijl,
  maatrecords, audit en bladinstellingen. Geen hergebruik van de laatst
  geselecteerde maatdocumenten voor andere objecten.
- `EngineeringDrawingGenerator` en `ProductionDrawingEngine` blijven de
  autoriteiten. Alleen de registratie van afgeleide uitvoer/projectstatus kan
  tijdens een readonly batch expliciet worden uitgezet.
- Bronproject, meshes en plaatsingen worden gekopieerd voordat de centrale
  JobManager het werk uitvoert. De worker gebruikt geen live Qt-widget.
- PDF-samenvoeging gebruikt de bestaande pypdf-afhankelijkheid. MuPDF wordt
  niet in deze worker aangeroepen naast de interactieve GUI.
- De GUI publiceert pas na nieuwe controle van bronrevisie, geometrie, scope,
  lintergegevens, bestandshashes en volledigheid. De complete tijdelijke map
  wordt in één hernoemstap gepubliceerd, nooit bestand voor bestand.
- Annuleren, een andere projectcontext, een verouderde job, een gewijzigde
  bron, een fout in de tweede tekening en bestaande bestemmingen worden
  expliciet afgehandeld zonder halve publicatie of overschrijving.
- De mapkeuze is aan het oorspronkelijke project en bronrevisie gebonden.
- Dit is een reviewbatch, geen nieuwe revisie- of machinevrijgave.
  `production_release_granted` blijft false. Bestaande autoriteiten worden
  niet verhoogd.

## Herstelde native renderfeedback

Tijdens de echte CWSMainWindow-proef bleven context-echo's telkens een
kleurverversing plannen. De kleurwijziging publiceerde opnieuw viewerstate,
waardoor die verversing zichzelf opnieuw kon inplannen.

De bestaande BOM-context plant dit nu alleen bij een gewijzigde workspace,
renderer, BOM-snapshothash, kleurmodus of revisiestatus. Selectieoverdracht
blijft ongewijzigd plaatsvinden. De regressietest bewijst dat twintig
selectie-echo's één kleurtaak plannen en dat elk relevant gewijzigd gegeven
wel opnieuw een taak plant.

## Afname en herleidbaarheid

Gerichte regressies omvatten echte vector-PDFs, volledige assemblies,
individuele bladinstellingen, ongeldige/lege scopes, ontbrekende geometrie,
dubbele/onveilige namen, annuleren, gewijzigde bestanden en brongegevens.
De historische twee P1811-skips in `pdf_review_smoke` blijven expliciet skips;
er zijn geen bestaande acceptatievoorwaarden verzwakt.

De werkelijke hoofdvenstertest voert drie scenario's uit:
één geselecteerd onderdeel, beide onderdelen en een geselecteerde assembly.
Alle drie gebruiken de bestaande QAction en JobManager; alleen de
directorykeuze wordt geautomatiseerd. De onafhankelijke PDF-lezer controleert
bladen, bladwijzers en vectorinhoud. Opgeslagen maatdocumenten blijven gelijk.

Deze controles draaien in dezelfde vijf bron-DPI-runs en drie packaged
runtimes als de bestaande V3-bewijzen. De finalizer vereist de nieuwe namen
én herberekent de hashes van de echte batchmanifesten en alle PDF-bestanden.
Een eerder groen rapport zonder de nieuwe batchbijlagen kan niet promoveren.

Lokale gewijzigde-sourceproeven zijn diagnostiek, geen releasebewijs.
Installer/portable en alle definitieve bewijzen moeten uit de nieuwe
ongewijzigde broncommit komen. Alleen een gezamenlijke geslaagde Windows-run
met installatiecontrole mag de beta promoveren.

## Gevonden Windows-regressie in het bestaande componentbewijs

De eerste Windows-run op `464dbad1` voerde 234 scripts uit waarvan één
oude BOM-componentproef na 300 seconden stopte: zij verwachtte nog dat
`drawing.batch_pdf` niet bestond. Nu de functie is aangesloten, opende
die ongewijzigde test een native mapkeuze waarop niemand antwoordde.

De proef stuurt nu expliciet die echte mapkeuze aan. De eenvoudige
componenthost heeft geen viewer-meshes en moet daarom correct weigeren:
geen PDF, geen tijdelijke bestanden en geen achterblijvende job.
De positieve deel-, subset- en assemblybatches blijven in de afzonderlijke
echte CWSMainWindow-proef verplicht. Geen productielogica of timeout is
versoepeld. De finalizer vereist beide nieuwe negatieve controlepunten;
een eenheidstest bewijst dat het weglaten ervan promotie verhindert.
De aangepaste componentproef is lokaal werkelijk uitgevoerd, niet geskipt.
Definitief Windows-/installerbewijs vereist een nieuwe commitgebonden run.
