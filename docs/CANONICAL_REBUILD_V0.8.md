# Canonical rebuild v0.8

Status: eerste begrensde deterministic solid- en bronmeetvergelijkingslaag.

## Ondersteund

- rechte gesloten plaatbuitencontour;
- rechte gesloten binnencontouren;
- doorgaande ronde gaten door platen;
- massief rond met expliciete lengte en diameter;
- exact en uniek gevonden `I`, `U/C`, `L`, `M` en `RO`-catalogusprofielen
  zonder bewerkingen;
- een geldig canonical solid in lokale productieassen.

## Bewust geblokkeerd

- boogsegmenten zonder expliciete, eenduidige sweep-richting;
- custom profielen zonder expliciete doorsnede;
- profielgaten en overige profielbewerkingen;
- blinde gaten en niet-ronde plaatbewerkingen;
- productie-vrijgave zonder formaat-roundtrips.

Een analytische Workbench-revisie kan dus geldig zijn terwijl de eerste
canonical builder de vorm nog blokkeert. Dit voorkomt dat bestaande
revisiegegevens worden afgekeurd alleen omdat een latere builderklasse nog niet
is geimplementeerd.

## Vergelijkingsbeleid

| Eigenschap | Type | Tolerantie |
|---|---|---:|
| Volume | numeriek | 0,1% relatief |
| Oppervlakte | numeriek | 0,1% relatief |
| Bbox, gesorteerde assen | numeriek | 0,05 mm absoluut |
| Solidcount | exact | geen |
| Geometrisch geldig | exact | geen |

Een vergelijking kan alleen `passed` zijn wanneer de bronmetingen aantoonbaar
bij exact het geselecteerde part horen en alle vijf controles beschikbaar zijn.
Een expliciete `scope = part/entity/exact_part` is geldig. Zonder declaratie mag
scope alleen worden afgeleid als bronpart, descriptor en meetset elk exact een
solid aantonen. Anders volgt `manual_validation_required`.

## Persistentie en invalidatie

Het project bewaart het volledige rapport en een SHA-256 daarvan onder
`part.workbench.canonical_rebuild`. Het rapport bevat de onveranderlijke
brongeometriehash, manufacturing hash, inputhash, builderversie, canonical
signature, bronmetingen, gevonden metingen, delta's, tolerantie, status en waar
nodig een vermoedelijke oorzaak.

Maakafmetingen behoren tot de geometry/manufacturing fingerprint. Een wijziging
in afmetingen, contouren, referentiezijden, productieassen of features maakt een
eerder rebuildrapport automatisch `invalidated`.

## Bewijs

- `tests/canonical_rebuild_smoke.py`: 6/6 geslaagd;
- volledige Windows-ontwikkelsuite: 28/28 smoke-scripts geslaagd;
- machineleesbaar: `validation/results/v08-canonical-rebuild-windows.json`;
- screenshot: `validation/results/v08-canonical-rebuild-ui-windows.png`.

De visuele fixture is synthetisch en niet vertrouwelijk. Ze is geen golden
reference voor de aangeleverde STEP-, IFC- of DSTV-modellen. Die 481 modellen
blijven `manual_validation_required` totdat hun verwachte waarden afzonderlijk
betrouwbaar zijn vastgesteld.
