# Hervatting PDF/UI V3 — 11 september 2026

## Werkbasis en afbakening

Repository `CoenWessselink/Convertor`, branch
`agent/cws-pdf-ui-v3-complete-20260909`.
Bij aanvang geverifieerde HEAD: `58f30372a3145dfac45c6bb3cfd5260e78a7b313`.
De drie opgegeven basiscommits `e5c09f42`, `3cccd357` en `8f56b58e` zijn
via volledige Git-ancestry als voorouders bevestigd. Geen oudere UI-branch
is gemerged. De read-only bronsnapshot `7d64f2d4` bewaart de bestaande bron
voor controle; hij is geen installer of software-reparatie.

## Opnieuw aangetoonde fouten in de vorige HEAD

Windows-run `34521027460` bouwde een installer-kandidaat, maar werd niet
gepromoveerd. De native hoofdvenstertest faalde op 175% DPI door recursie
in QVTK tijdens een resize voordat `_Iren` was geïnitialiseerd. De brede
regressie en Phase 3 faalden door zes nog niet aangeroepen publieke V3-methoden
in de runtime-inventaris. De tienminutenduurtest zelf was geslaagd.
Beide fouten zijn lokaal opnieuw aangetoond voordat zij zijn hersteld.
Een oude installer van deze run mag niet als de herstelde build worden geleverd.

## Gerichte wijzigingen

- Het bestaande native VTK-widget en zijn twee overlay-subklassen verwerken
  vroege Qt-resizes zonder een nog niet bestaande interactor te benaderen.
  De bestaande logische-pixel/DPI-correctie en controller blijven behouden.
- Een nieuwe deterministische regressie forceert het vroege resize-event
  tijdens echte native handle-creatie. Dezelfde test controleert na normale
  resize het bestaan van de echte backend/controller en de overlaygeometrie.
- De runtime-inventaris roept zoom/set_zoom, Trusted-export, PDF-openen,
  selectieoverdracht en de initiële PDF-openroute daadwerkelijk aan. Een
  echte lokale PDF en expliciete postcondities voorkomen alleen trace-dekking
  zonder resultaatcontrole. Geen publieke functie is uitgezonderd.
- STEP-, IFC-, DXF-, BOM-, nesting-, herkennings- en installerbroncode blijven
  ongewijzigd. DrawingWorkspacePanel en de bestaande maat-/renderketen zijn
  de autoriteiten, niet een vervangend programma.

## Bewijs en resterende grens

Lokale voorcontroles hebben een gewijzigde werkboom en zijn daarom geen
releasebewijs. Alleen nieuwe Windows-resultaten met de definitieve commit,
clean-sourcecontrole, EXE-hashes en echte geïnstalleerde-app-tests gelden
voor vrijgave. De acceptatie-eisen van de gezamenlijke promotiegate blijven
ongewijzigd; herhaalde oude artifacts tellen niet mee.

De oorspronkelijke V3-ZIP en referentiebeelden konden in deze hervatting niet
opnieuw worden gelezen. De historische specificatiehash wordt niet als een
nieuwe inhouds- of visuele verificatie gepresenteerd. Zie
`PDF_UI_V3_NATIVE_INTEGRATION.md` voor deze provenancebeperking en de reeds
bestaande softwarebeta-/hardware-/machinekwalificatiegrenzen.

## Aanvullend gevonden grens tussen Windows-build en Linux-vrijgave

De verse Windows-run op `bdd0fa3c` slaagde voor de kern en vier
regressiegroepen. Onafhankelijk uitlezen van zijn feitelijke DPI-manifest
liet echter zien dat `report` Windows-backslashes bevatte. De Linux-finalizer
behandelde die als onderdeel van een bestandsnaam. Dit is opnieuw aangetoond
met het echte Windows-artifact en een afzonderlijke manifest-unitfixture.

De rapportproducer schrijft nu platformneutrale POSIX-referenties. De finalizer
kan ook reeds geschreven Windows-referenties veilig lezen, zonder rapporten,
afbeeldingen of hun hashes te wijzigen. Absolute paden, drive-/UNC-paden en
padtraversal worden geweigerd. De extra unitfixture test alle acht runtimegroepen
en afwijzing van gemanipuleerde hashes; zij is nadrukkelijk geen UI-bewijs.
De vrijgavemanifesten vermelden nu ook expliciet dat de originele specificatie
niet opnieuw is gecontroleerd. Alle bestaande bron-/runtime-/hash-/soakgates
blijven vereist. Installer en bewijzen moeten opnieuw op de definitieve
commit worden gegenereerd, niet met de eerdere kandidaat worden gemengd.

## Aanvulling na ontvangst van de oorspronkelijke ZIP

De bovenstaande beperking inzake de ontbrekende ZIP is historisch. De gebruiker
heeft later op 11 september de oorspronkelijke bytes opnieuw aangeleverd. De
archiefhash en alle zes manifestbestanden zijn geverifieerd; de volledige prompt
en drie referentiebeelden zijn gelezen. Zie `PDF_UI_V3_SPEC_REVIEW_20260911.md`
voor invoercontrole, vergelijking en herstel van vrijgavebewijs/canonieke ketens.
Alleen manifesten van de nieuwe definitieve commit gelden voor die herstelbuild.
