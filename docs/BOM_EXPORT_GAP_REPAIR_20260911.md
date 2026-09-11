# BOM-export vervolg — W03 en W18, 11 september 2026

## Werkbasis

Deze gerichte aanvulling gebruikt de bestaande bron `721b9b70` op
`agent/cws-pdf-ui-v3-complete-20260909`. De voorgaande Windows-run
`34622890577` is opnieuw gecontroleerd en volledig geslaagd. Geen oude
UI-branch is gemerged en geen vervangend programma is gebouwd.

## Werkelijk gewijzigde functies

- De bestaande V15 Export Center-service maakt een exacte, disjuncte partitie
  van de selectie: per onderdeel/object, positie, assembly, assemblymerk,
  fase, batch, machine of gecombineerd. Elk kindpakket wordt geproduceerd
  door de bestaande ProjectProductionExportEngine met haar bestaande
  onderdeel-, materiaal-, review-, roundtrip- en vrijgavecontroles.
- DSTV en PDF/labels zijn aan de bestaande NC1-, production_pdf- en label_pdf-
  uitvoer gekoppeld; er wordt geen nieuwe geometriewriter geïntroduceerd.
- Machinegroepering vraagt een expliciete toewijzing en een actueel,
  manufacturing-hashgebonden capabilityrapport. Een advies is geen
  toewijzing; groeperen verleent geen machine- of transportbevoegdheid.
- Bij ontbrekende/conflicterende groepsinformatie wordt geblokkeerd.
  Onderdelen met meer dan één assembly-eigenaar worden niet gekopieerd
  naar meerdere groepen met telkens het volledige aantal. Occurrence-
  verdeling over meerdere eigenaren blijft een expliciete vervolgopdracht.
- De Qt-werkruimte houdt scope, formaat, groepering en oorspronkelijke
  BOM-opdracht vast. Alleen een geverifieerd geschreven pakket levert een
  geslaagd BOM-resultaat op. Een andere projectcontext ontvangt dat oude
  achtergrondresultaat niet. Gelijktijdig opnieuw starten wordt geweigerd.
- XLSX, CSV en JSON in de BOM maken nu hun afzonderlijke payload in plaats
  van telkens het hele pakket. De bestaande XLSX-opmaak en bescherming
  tegen spreadsheetformules blijven behouden. Reviewexport blijft review:
  manifest, validatierapport en hashes worden als bijlagen meegeleverd.
- Bij een gedeeltelijke selectie van een geaggregeerde BOM-regel worden
  uitsluitend de gekozen canonieke IDs, aantallen en individuele massa's
  opgenomen. Een gehighlighte groep voegt geen niet-geselecteerde delen toe.
  Onbekende individuele massa/aantallen worden niet pro rata gegokt.
- De productie-export voegt een exacte part-BOM toe, geen volledige project-
  BOM bij elke groep. De standaard assembly-packagecontrole van de originele
  engine blijft behouden. Losse onderdeel-/fase-/machinegroepen vragen alleen
  onderdeeluitvoer; ze doen geen onterechte assemblyvrijgaveclaim.

## Publicatie en veiligheid

Alle groepen worden eerst in een private tijdelijke map geschreven, daarna
teruggelezen en tegen manifest, ZIP-inhoud en checksums gecontroleerd. De
complete partitie moet iedere gekozen ID precies eenmaal bevatten.

De bronrevisie omvat ook ruwe velden, werkbankvrijgave, groepsmetadata en
machinebewijs. Gewijzigde bron, beschadigde preflight, geannuleerde opdracht
of fout in een latere groep voorkomt publicatie van de volledige batch.
Een reeds bestaand uitvoerpakket wordt niet overschreven of verwijderd.
Publicatie gebeurt door één rename op hetzelfde bestandssysteem. Annuleren
ná die publicatie trekt een reeds geverifieerd pakket niet achteraf in.
Pakketten blijven aan hun bronrevisie gekoppeld; een export is geen modelmutatie
of undo van een machinebewerking.

Groepsvolgorde en leden zijn stabiel. Pakketnamen zijn veilig, uniek en
herleidbaar; vrije naamtemplates blijven niet geïmplementeerd en worden niet
stilzwijgend genegeerd. Een herhaling hoeft door nieuwe job-/tijdstempels niet
byte-identiek aan een eerdere export te zijn.

## Controleketen

`tests/bom_grouped_export_smoke.py` test de partitie, lege/onbekende scope,
verouderde metadata, herstart, cancellation, beschadigde output, fout in de
tweede groep, behouden bestaande bestanden en afzonderlijke reviewformaten.
De manifest-exporter in deze unitproeven is expliciet synthetisch en geldt
niet als native CAD- of installerbewijs.

`bom_export_evidence.run_bom_export_evidence` bouwt twee expliciet synthetische
platen via de echte Workbench → canonical rebuild → roundtrip → review →
release-keten. De echte BOM- en Export Center-QWidgets/QActions starten de
echte JobManager en exportengine. Alle acht hoofdgroeperingen leveren opnieuw
gecontroleerde STEP/NC1/PDF-pakketten. Een extra niet-vrijgegeven onderdeel
blijft buiten de selectie. Afzonderlijke XLSX/CSV/JSON-acties testen de
geaggregeerde-regelvalkuil en concrete uitvoerbestanden. Dit is een test van
de echte componenten, niet een vervangend programma of een leverancierstest.

Deze proef wordt vanuit de bestaande BOM-acceptatie gestart in de werkelijk
geïnstalleerde EXE, zonder externe Python op PATH. De installer- en finale
promotiegates vereisen hetzelfde source-SHA, EXE-hash, alle acht groeperingen,
alle drie reviewformaten en de hashes van de echte pakketten en screenshots.
Een oud groen BOM-rapport zonder dit aanvullende bewijs faalt de nieuwe gate.

Het echte volledige CWSMainWindow krijgt daarnaast native muis-/toetsproeven
voor de exacte exportselectie en het blokkeren van niet-vrijgegeven invoer.
Deze draaien in de bron op vijf DPI-schalen en in de drie verpakte uitvoeringen
bij 100%. Zij vervangen de al bestaande hoofdvenster- en V3-maatproeven niet.

Lokale diagnostiek vóór commit heeft een gewijzigde werkboom en is geen
releasebewijs. Alleen de verse Windows-uitvoer van de uiteindelijke commit
mag als geleverde installatie-afname worden gepresenteerd.

## Niet met dit pakket gesloten

W03 en W18 zijn verder ingevuld, niet volledig afgesloten. Batchgeneratie
van interactieve tekeningen, batchplotten, alle 87 BOM-acties en alle
revisie/undo-/occurrencecombinaties blijven afzonderlijk te testen/bouwen.
Ook vrije naamtemplates, multi-assembly occurrenceverdeling, de onafhankelijke
leveranciers-/DXF-/complex-profielmatrix, echte certificaten en machine-, GPU-,
printer-, Windows 11- en upgradeafname blijven open volgens het werkregister.
Er wordt geen universele herkenning of volledige productievrijgave verklaard.

## Aanvullende visuele fout, tijdens deze afname hersteld

De verse gegroepeerde PDF bevatte een oude generieke H-profielschets bij een
plaat. De roundtrip geeft nu de echte canonical rebuild-BREP door aan Trusted
PDF. De bestaande gedeelde DrawingProjectionModel/OCCT-HLR verzorgt de
isometrie; er is geen nieuwe geometriewriter. Zonder BREP verschijnt een
expliciete ontbreektmelding, nooit een verzonnen H-profiel. Een mislukte HLR
bij aangeleverde BREP breekt de export af. De zichtbare PDF-roundtrip vereist
het bewijslabel van deze exacte projectie. Plaatrandaanzichten heten geen
flenzen meer. Individueel passende nevenaanzichten worden NTS gemarkeerd.
De schaal van het hoofdaanzicht wordt werkelijk toegepast, niet afgerond
naar een andere opdruk; een niet-passende vaste schaal wordt geweigerd.
Deze correctie verandert geen STEP/IFC/NC1-writer of materiaalautoriteit.
