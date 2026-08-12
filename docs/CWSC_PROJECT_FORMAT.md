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

Het manifest bevat onder meer:

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
