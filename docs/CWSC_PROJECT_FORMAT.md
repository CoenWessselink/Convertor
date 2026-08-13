# `.cwscproj`-projectformaat

## Doel

Een `.cwscproj` is één draagbaar CWS Convertor-projectbestand. Het bevat het canonieke projectsnapshot, integriteitsmetadata en optioneel de originele IFC-/STEP-bronnen en previews. De gebruiker hoeft geen losse mapstructuur te beheren.

## Containerindeling

Een project is een ZIP-container met minimaal:

```text
manifest.json
project.sqlite
```

Optioneel:

```text
sources/<source-id>/<bestandsnaam>
previews/<bestandsnaam>
```

`project.sqlite` bevat het huidige Canonical Project Model-snapshot en projectmetadata. Grote binaire geometriebronnen blijven als afzonderlijke gemanifesteerde entries aanwezig, zodat zij exact kunnen worden geëxtraheerd en geverifieerd.

## Manifest

Vanaf Project Model 2.1 bevat het manifest vier afzonderlijke integriteitshashes:

- `project_sha256` / semantische projectsnapshot;
- `content_sha256` voor inhoud zonder vluchtige revisievelden;
- `revision_content_sha256` voor revisiebepaling;
- `manufacturing_state_sha256` voor productie-invalidering.

Het manifest bevat daarnaast onder meer:

- pakketformaat en opslagversie;
- productschema en applicatieversie;
- project-ID;
- aanmaak-/wijzigingstijd;
- entrypad, soort, bytegrootte en SHA-256;
- bron-ID en oorspronkelijke bestandsnaam waar relevant.

Een entry die niet in het manifest staat, wordt geweigerd. Een gemanifesteerde entry met afwijkende hash of grootte wordt eveneens geweigerd.

## Integriteit en beveiliging

Bij openen worden minimaal uitgevoerd:

- ZIP CRC-test;
- controle op dubbele entries;
- blokkade van absolute paden, `..`, backslashes en padtraversal;
- bestandsgrootte-, totaalvolume- en compressieratio-limieten tegen archive bombs;
- SHA-256 en bytegrootte per entry;
- SQLite `PRAGMA integrity_check`;
- controle van pakket-, opslag- en projectschemaversie.

De extractor schrijft alleen naar een vooraf bepaald doelpad en controleert opnieuw dat de uiteindelijke locatie binnen dat doel blijft.

## Atomisch opslaan

1. bouw database en manifest in een tijdelijke werkmap;
2. maak een tijdelijk ZIP-pakket;
3. heropen en verifieer het tijdelijke pakket;
4. maak optioneel een backup van het bestaande doel;
5. vervang het doel atomair.

Wanneer een stap faalt, blijft het bestaande projectbestand onaangetast. De batchservice gebruikt een transactionele kopie van het live model zodat ook het geheugenmodel wordt teruggedraaid.

## Autosave en herstel

Autosave schrijft bewust een lichtgewicht projectsnapshot zonder de grote ingesloten bronbytes telkens opnieuw te comprimeren. Herstel:

1. valideert de autosave;
2. valideert het hoofdproject;
3. combineert het nieuwste geldige model met de al geverifieerde ingesloten bronnen;
4. schrijft altijd naar een expliciet herstelbestand;
5. verifieert het herstelbestand volledig.

Een autosave wordt alleen als herstelkandidaat aangeboden wanneer hij nieuwer is dan het hoofdproject.

## Revisies en backups

Een inhoudelijke wijziging kan een projectrevisie aanmaken. Bij normaal opslaan kan daarnaast een `.bak`-kopie worden behouden. Backup en revisie hebben verschillende doelen: backup beschermt tegen bestandsverlies; revisie beschrijft de inhoudelijke projectgeschiedenis.

## Migratie en compatibiliteit

- een bekende oudere projectschemaversie kan read-only worden geopend;
- migratie schrijft naar een nieuw doelbestand;
- de bron wordt nooit stil overschreven;
- een onbekende nieuwere major-versie wordt geblokkeerd;
- legacy IFC-/Trusted-PDF-payloadmarkers blijven buiten het projectformaat bewust compatibel.


## Semantische importmetadata in schema 2.1

Per bron worden strategie, importerversie, entitycounts, bronklassecounts, relatiecounts, spatial tree, geometry-samenvatting, bewijs, warnings en productiegate opgeslagen. Iedere gematerialiseerde entity verwijst via `SourceIdentity` terug naar bronbestand, bronhash en IFC/STEP-entity.

Schema 2.0 wordt als compatibele minor-versie gemigreerd. Een onbekende major-versie opent niet stil als schrijfbaar project.

## Part Workbench in schema 2.5

Schema 2.5 gebruikt per onderdeel een optionele `workbench`-sectie. Bestaande
onderdelen zonder deze sectie behouden hun bestaande geometry- en manufacturing
hashes. Een gestarte Workbench bewaart:

- de onveranderlijke bronbestand- en brongeometriehash;
- de actuele analytische partrevisie en append-only revisiesnapshots;
- rechterhandige productie-assen, expliciete maakafmetingen, referentiezijden,
  contouren en features;
- provenance, open vragen en actuele blokkerende validatie-issues;
- een gehasht commandolog met cursor voor undo/redo;
- afgeleide artefacten met de manufacturing hash waarvoor ze zijn gemaakt;
- een optioneel gehasht canonical rebuildrapport met bronmetingen, canonical
  metingen, vergelijkingsbeleid en de bijbehorende manufacturing hash.
- een gehasht NC1/STEP/IFC/Trusted-PDF-roundtriprapport en alleen de artefacten
  die samen tegen dezelfde canonical signature zijn geslaagd.

Een wijziging in productiegeometrie of features berekent de part-hashes opnieuw.
Artefacten met een andere manufacturing hash krijgen status `invalidated`.
Het canonical rebuildrapport volgt dezelfde regel en wordt nooit gebruikt om
ontbrekende bronwaarden alsnog als verwacht resultaat in te vullen.
Globale projectplaatsing is geen onderdeel van de manufacturing identity;
spiegeling blijft dat wel.

Project Model 2.0 tot en met 2.4 wordt expliciet naar 2.5 gemigreerd. Workbench
1.0 wordt naar 1.1 opgewaardeerd zodat ook de herkenningskeuze in de
manufacturing hash valt. Bestaande rebuild-, roundtrip- en productieartefacten
worden daarbij ongeldig; er worden geen productiefeatures of verwachte waarden
verzonnen.

## Broninspectie vanaf importer 2.2

Een `geometry_descriptor` kan een versie-1 `source_locator` en
`source_inspection` bevatten. Deze records zijn klein en deterministisch: de
package bewaart selectors, hashes, meetwaarden, topologie en validatiestatus.
CadQuery/OCP-shapes en IFC-meshvertices zijn uitsluitend runtimegegevens en
worden niet in SQLite of ZIP opgeslagen.
