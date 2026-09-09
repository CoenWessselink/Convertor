# Herstel van brongebonden praktijkherkenning

Deze wijziging bouwt voort op `1d83feaca1bc9b9f21e0e7cdc69db0933b9e6008`.
De bestaande project-, BOM-, materiaal- en machinevrijgavepaden blijven leidend.
De oorspronkelijke klantbijlagen en de private verwachtingen zijn **niet** in
het openbare repository opgenomen. Tests in het repository maken eigen fixtures.

## Herstelregister

| Audit-ID | Gewijzigd gedrag | Negatieve bescherming |
|---|---|---|
| STEP-01 | Volledige occurrence-paden; ieder hergebruikt samenstellingsexemplaar krijgt eigen bladonderdelen en samengestelde wereldplaatsing. | Cycli en onbegrensde expansie worden afgewezen; geen aantallen uit bestandsnamen. |
| STEP-02 | Witruimte wordt verwijderd vóór naamterugval; productnamen en volledige exemplaarpaden blijven bewaard. | Geen lege weergavenaam wanneer een bronproductnaam bestaat. |
| STEP-03 | Geometrisch bewezen maatwerkdoorsneden krijgen een reproduceerbare CUSTOM-naam en doorsnedegegevens. | Dit is geen fictieve catalogusmatch; onbekende materiaalgrade blijft onbekend. |
| STEP-04 | Native componentselectie via de oorspronkelijke Part-21-entiteitslabels, inclusief complex samengestelde records. Referenties blijven apart. | Selectie niet op lijstvolgorde; bronhash, geselecteerde rootgrafiek en onderdeelidentiteit moeten overeenkomen. |
| STEP-05 | Ook zelfstandige rootproducten naast samenstellingen worden meegenomen. | Geen stille uitsluiting van losse top-level volumes. |
| PDF-01 | Gelabelde assemblagestuklijsten worden ruimtelijk gescheiden van tolerantie-/titelblokken. | DIN of PART NUMBER is geen profiel; onvolledige rijen worden niet goedgekeurd. |
| DXF-01 | Model-contouren/boringen onder INSERT-blokken worden gekoppeld aan de expliciete layout-stuklijst, grade, dikte, aantallen en samenstellingsmerken. | Geen standaardgrade, onbekende units, niet-sluitende aantallen, meerdere ambigu gekoppelde delen of stille contourbenadering. |
| IFC-01 | Expliciete Tekla Part mark wordt het positienummer; technische Tag blijft bronidentiteit. | Een technisch ID overschrijft geen expliciet posmerk. |
| IFC-02 | Expliciet metselwerk blijft bronmateriaal en wordt bouwkundige context. | Tegenspraak met een bekende metaalgrade blijft een conflict; geen staalproductievrijgave. |
| NC-01 | Volledige canonieke NC1-payload blijft behouden; oorspronkelijke profielparameters krijgen onafhankelijk lokaal BREP-bewijs. | Bronpayload wordt eerst met de oorspronkelijke NC1-attachment vergeleken; geen gedwongen catalogusmatch. |
| NC-02 | Een ontbrekende lokale bewerking kan niet door een kleine globale volumeverhouding worden verborgen. Bronboringen worden één-op-één op diameter, as, wandzijde en positie gekoppeld. | Een ontbrekende, extra of afwijkende boring blokkeert; een eenvoudiger maar niet-bewezen hypothese wint niet. |
| NC-03 | Vereenvoudigde geometrie van NC1-inkoopartikelen blijft expliciet een proxy. | Geen verzonnen draad/binnengat of CNC-geschiktheid. |
| TEST-01 | Private, hash-gebonden acceptatierunner en publieke synthetische regressies zijn toegevoegd. | Source-runtime-controle is geen afname van een nieuwe geïnstalleerde Windows-EXE met de private bijlagen. |

## Reproduceerbare private controle

`tools/verify_private_recognition_set.py` accepteert een manifest buiten het
repository. Elk bestand bevat `file`, `sha256` en een niet-lege `expected` map.
De verwachtingen moeten onafhankelijk uit de bron of geaccordeerde referentie
komen; nooit uit de te testen uitvoer worden gegenereerd.

```text
python tools/verify_private_recognition_set.py --manifest /private/set.json --root /private/inputs --output /private/proof --native-all
```

De uitvoer bevat alle afwijkingen, ongewijzigde bronhashes, bron/runtime-identiteit,
selectie- en herkenningsresultaten en controle na opslaan/heropenen. Uitvoer blijft
in de opgegeven private map. Een fout of ontbrekende verwachting wordt geen PASS.

## Exacte IFC-topologie

Voor door IFC als solid verklaarde Body-geometrie kunnen losse native BREP-vlakken
zonder toegevoegde geometrie tot één gesloten shell worden samengevoegd. Vrije,
meervoudige of verwijderde randen/vlakken, meerdere shells, gewijzigd oppervlak
of een ongeldig volume worden afgewezen. Een open referentieoppervlak wordt
hiermee niet stilzwijgend tot maakdeel omgezet; de meshfallback blijft apart.

## Afbakening

Een correcte naam, aantal, profiel of contour is geen automatische productievrijgave.
Ontbrekende grades, complexe/buiten de ondersteunde route vallende documenten,
referentieoppervlakken, inkoopproxies en machinekwalificatie blijven afzonderlijk
zichtbaar. Bestaande projecten met oude of gewijzigde bronselectorgrafieken moeten
opnieuw via het revisie-/importpad worden ingelezen; de nieuwe validator accepteert
geen oude grafiekhash op basis van een toevallige geometriepositie.

De GitHub-workflow test de exacte commit op Windows met publieke synthetische
fixtures, strikte acceptatie en het bestaande herkenningscorpus. De private set
wordt afzonderlijk lokaal uitgevoerd. Een nieuwe installer en private Windows-/
GUI-afname zijn niet door alleen deze broncommit bewezen.
