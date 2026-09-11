# BOM reviewexports — vervolg W03/W18, 11 september 2026

## Bronbasis

Dit gerichte herstel bouwt op `721b9b705fff5604c05c7237572b06b26e158c8a`,
branch `agent/cws-pdf-ui-v3-complete-20260909`. Tijdens de uitvoering schoof
HEAD door naar `483fe1813967452dc7d83667150960e001adffda`. De veranderingen
zijn daarop opnieuw vergeleken, geïntegreerd en getest. De gelijktijdige
format-aware writer, exacte partselectie, acht productiepackagegroeperingen
en canonieke BREP-/schaalreparatie zijn behouden; niet met de oudere bron
overschreven. De onderstaande eerste fouten zijn op 721b9b70 gereproduceerd;
een deel was ook in de tussentijdse commits hersteld. De bronbytes en oorspronkelijke
Git-tree van het aangeleverde snapshot zijn opnieuw gecontroleerd. Er is geen
andere UI-branch samengevoegd en geen vervangend programma gebouwd.

## Aangetoonde fouten

1. `export.xlsx`, `export.csv`, `export.json` en `export.review` riepen dezelfde
   volledige package-export aan. De specifieke QAction ging verloren.
2. De geretourneerde dictionary werd op keys in plaats van outputpaden doorlopen;
   het resultaatrapport bevatte daardoor namen in plaats van werkelijke paden.
3. De oude review-scope kon via een gedeeld merk of parent assembly verbreden:
   selectie P1 met aantal 2 leverde P1+P2 met aantal 5. Die verbreding is lokaal
   vóór de reparatie opnieuw aangetoond.
4. Een projectwissel of wijziging tijdens een bevestigings-/mapdialoog werd in
   deze reviewexport niet opnieuw tegen de vastgelegde opdracht gecontroleerd.

## Uitgevoerd

- De bestaande BOM QAction-router draagt de exacte reviewactie over. XLSX maakt
  de bestaande workbookweergave, CSV de acht bestaande datasets, JSON de
  ongewijzigde ruwe snapshotstructuur. Alleen de expliciete complete reviewactie
  maakt daarnaast PDF en het bestaande BOM-package. Manifest en checksums zijn
  bij ieder formaat aanwezig; ze zijn geen extra model-/productie-export.
- De bestaande writers en opmaak blijven behouden. De gelijktijdig toegevoegde
  `_part_snapshot` en `_export_review`-API zijn behouden; de laatste gebruikt
  dezelfde format-aware packagewriter, met aanvullende hash-/stalecontrole. CSV/XLSX behouden hun
  injectiebeveiliging; JSON blijft brongetrouwe data, niet spreadsheetinhoud.
- `strict_entities=True` is een opt-in op de bestaande snapshotketen. De UI
  gebruikt deze exacte scope: geen siblingparts, geen vollediger materiaalstaat
  bij een smaller geselecteerd onderdeel, en geen door groepslidmaatschap
  toegevoegde traceability-IDs. Assemblagemerk blijft context bij het onderdeel.
  De oude ruimere review-API blijft ongewijzigd voor bestaande callers.
- De opt-in generieke strikte scope maakt part- en fasteneraantallen niet
  minimaal één. Nul blijft daar nul en ongeldige aantallen worden geweigerd.
  De recente conservatieve part-only projectie houdt haar eigen bestaande
  massa-/aantalvalidatie. Lege objectselecties en ambigue geneste
  assemblygroepen worden geweigerd, niet naar siblings verbreed.
- Een expliciete matrixactie met lege selectie exporteert nooit alle zichtbare
  regels. De algemene werkbalkactie blijft expliciet de zichtbare scope aanbieden.
- Iedere export schrijft eerst naar staging en publiceert pas na voltooiing,
  hashcontrole en nieuwe broncontrole. Iedere uitvoering krijgt een eigen map;
  eerdere uitvoer en andere formaten worden niet overschreven of vermengd.
- Resultaatregistratie behoudt de exacte actie, werkelijke absolute paden,
  preflightbinding en passed/failed/cancelled. Exports verlenen geen productie-,
  voorraad-, machine- of transportrechten. Een file-export krijgt geen fictieve
  model-undo. De bestaande BOM-resultaatdialoog toont de uitvoering.

## Getest en verplichte Windows-afname

- `tests/bom_review_export_smoke.py`: exacte selectie/aantallen, gescheiden
  formats, injectiebeveiliging, legacycompatibiliteit, ontbrekende scope,
  gewijzigde snapshot, verouderde bron, schrijverfout en uitvoerbotsing.
- `bom_action_evidence.py`: echte shipping QAction-triggers en writers voor alle
  vier reviewacties; bestanden opnieuw lezen en hashen; vijf A-occurrences, geen
  drie B-occurrences; annulering, projectwijziging, lege selectie, echte
  resultaatdialoog en canonieke serialisatie van de audit.
- De bestaande shipping-panel-testhost blijft herkenbaar een componententest,
  geen vervangende hoofdapplicatie of GPU-pariteitsclaim.
- De installerketen voert dezelfde test in de geïnstalleerde EXE uit. Build én
  eindpromotie vereisen vier afzonderlijke reviewacties, concrete asserties,
  exact passende formaten en correcte hashes van alle feitelijke uitvoerfiles.
  Een oud groen rapport of ontbrekende reviewactie blokkeert promotie.
- De finalizer-unitfixtures zijn duidelijk synthetisch; ze zijn geen native
  applicatiebewijs. Twee extra negatieve tests bewijzen afwijzing van een
  ontbrekende reviewactie en een gewijzigd uitvoerbestand.

Lokale gewijzigde bron is voorcontrole, geen releasebewijs. Een nieuwe beta mag
uitsluitend na de bestaande volledige Windows-acceptatie op de finale commit
worden aangeboden; de installer van 721b9b70 wordt niet omgelabeld.

## Niet afgesloten

W03/W18 zijn niet volledig dicht: complete batchteken-/printacties, alle 87
acties en hun volledige lifecycle, 481 bronmodellen, herkenningsdekking,
fysieke apparatuur en bedrijfsafname blijven afzonderlijke werkpakketten.
De acht productiepackagegroeperingen uit de gelijktijdige commits zijn
behouden en in de regressie meegenomen, inclusief hun oorspronkelijke
installed-evidencegate. Dit document claimt ze niet als nieuw eigen werk.
De aanvullende reviewgate moet naast die bestaande grouped-exportgate slagen;
geen van beide vervangt de andere. Dit herstel verleent geen productie- of
machinevrijgave. De definitieve Windows-resultaten worden aan de nieuwe
gezamenlijke broncommit gebonden, niet aan een van de losse voorcontroles.
