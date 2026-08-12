# Architectuur CWS Convertor 0.6

## Afbakening

Versie 0.6 bouwt het projectfundament boven op de bestaande conversiekern. De nieuwe laag registreert complete IFC-/STEP-bronnen, bewaart bewijs en nulmetingen, beheert projectidentiteit en sluit productie-export totdat de semantische importer de bron veilig heeft gematerialiseerd.

```text
Bestaande productieformats                         Complete projectmodellen
NC1 / STEP / IFC / PDF                            IFC / STEP
          │                                           │
          ▼                                           ▼
Canonical Part Model 1.1                    deterministische bronanalyse
          │                                 + importstrategie A / B / C
          │                                           │
          └──────────────┐               ┌─────────────┘
                         ▼               ▼
                    Canonical Project Model 2.0
                         │
                         ├─ identiteit, placements en hashes
                         ├─ assemblies / parts / inkoop / fasteners / welds
                         ├─ revisies, audit en validatie
                         └─ productiepoort
```

## Pakketgrenzen

- `cws_convertor.product` — centrale productnaam, versie en bestandsidentiteit.
- `cws_convertor.project.model` — Canonical Project Model 2.0.
- `cws_convertor.project.baseline` — STEP-P21-/IFC-entiteitsanalyse en veilige routestrategie.
- `cws_convertor.project.storage` — atomisch `.cwscproj` ZIP+SQLite-pakket.
- `cws_convertor.project.service` — één transactiegedrag voor GUI en CLI.
- `cws_convertor.project.jobs` — annuleerbare achtergrondtaken.
- `project_tab.py` — functionele desktoplaag boven dezelfde projectservice.
- `cli.py` — batch- en integratiecontract boven dezelfde projectservice.

De bestaande convertermodules blijven compatibiliteitsfacades totdat zij gecontroleerd per module naar de nieuwe pakketstructuur zijn verplaatst. Hierdoor wordt geen werkende v0.5.1-functionaliteit weggegooid.

## Veiligheidslagen van `.cwscproj`

1. Veilige ZIP-paden en limieten voor aantallen, grootte en compressieverhouding.
2. Geen dubbele of niet-gemanifesteerde entries.
3. SHA-256 en bytegrootte per entry.
4. ZIP-CRC.
5. SQLite `PRAGMA integrity_check`.
6. Hash van het canonical JSON-snapshot in SQLite.
7. Projecthash en manufacturing-state-hash in het manifest.
8. Cross-check tussen manifest, bronnen, entity-aantallen en auditlog.
9. Project Model-validatie van alle relaties en numerieke productievelden.
10. Productiepoort die onvolledige semantische imports blokkeert.

## Identiteit

- **Source identity:** bronbestand + SHA-256 + bronentity/GlobalId/product occurrence.
- **Internal identity:** stabiele UUIDv5 waar bronidentiteit beschikbaar is.
- **Geometry hash:** genormaliseerde lokale geometrie, onafhankelijk van globale placement.
- **Manufacturing hash:** geometrie plus materiaal, features, referentiezijden, spiegelstatus en productiebepalende metadata.

Globaal verplaatsen van een onderdeel hoeft daardoor geen nieuw NC-bestand te veroorzaken. Een gat-, materiaal- of spiegelwijziging verandert de manufacturing hash wel.

## Transacties

- Multi-file bronregistratie is in-memory transactioneel.
- Een fout in het laatste bestand rolt eerdere wijzigingen terug.
- Opslaan bouwt eerst een afzonderlijk gevalideerd snapshot.
- Het bestaande pakket wordt pas na volledige packageverificatie atomair vervangen.
- Autosave wijzigt het hoofdproject niet.
- Herstel voegt alleen bronbytes terug die opnieuw op SHA-256 zijn gecontroleerd.

## Fasegrens

De v0.6-bronanalyse telt en classificeert bronentiteiten en kiest de veilige importstrategie. Zij maakt nog geen productie-vrijgegeven `Assembly`- en `Part`-objecten van de complete referentiemodellen. Fase 2 moet eerst relations, placements, properties, materialen en geometrie semantisch importeren en per entity valideren.
