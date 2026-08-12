# Canonical Project Model 2.1

## Doel en afbakening

Het Canonical Project Model is de centrale waarheid voor complete IFC-/STEP-projecten. Het organiseert bronnen, assemblies, onderdelen, inkoopdelen, bevestigingsmiddelen, lassen, voorraad, operaties en machines. Exacte onderdeelgeometrie blijft gekoppeld aan het bestaande Canonical Part Model; er ontstaat geen tweede afwijkende productiegeometrie.

Het model is versieerbaar en serialiseerbaar. Onbekende velden kunnen bij een compatibele minor-update worden behouden, terwijl een onbekende major-versie niet stil wordt geaccepteerd.

## Hoofdentiteiten

- `ProjectModel`: projectkop, bronnen, alle entiteitscollecties, validatie, revisies en audit;
- `SourceFileRecord`: bronhash, formaat, schema, importstrategie, meetbewijs en opslagstatus;
- `Assembly`: merk, bronidentiteit, placement, hoofd-/secundaire delen, fasteners en welds;
- `Part`: part position, profiel, materiaal, geometry/manufacturing hash en productiestatus;
- `PurchasedItem`: artikel, leverancier, norm, prijs-/levertijdvelden en assemblyrelaties;
- `Fastener`: type, diameter, lengte, kwaliteit, locatie en verbonden onderdelen;
- `Weld`: lasmaat, lengte, proces, zijde, werkplaats/montage en verbonden delen;
- `StockItem` en `Remnant`: materiaal, profiel/plaat, heat, voorraad, reservering en restmaat;
- `ProductionOperation`: bewerking, machineklasse, instellingen, tijd en gereedschap;
- `MachineProfile` en `MachineJob`: capabilities, postprocessor, simulatie, vrijgave en checksum.

## Identiteitslagen

### Bronidentiteit

Bestaat uit bronbestand/hash plus beschikbare IFC GlobalId, STEP product occurrence, Tekla mark of entity-ID. Dit bewaart herleidbaarheid naar de bron.

### Stabiele interne identiteit

Entiteiten krijgen een deterministische UUIDv5 op basis van projectnamespace, entiteitstype en bronidentiteit. Daardoor blijft identiteit stabiel over herimport zolang de bronidentiteit stabiel is.

### Geometry hash

De geometry hash is placement-onafhankelijk. Gelijke geometrie op verschillende posities kan zo worden gegroepeerd zonder globale projectcoördinaten in de hash op te nemen.

### Manufacturing hash

De manufacturing hash omvat ten minste geometrie, materiaal/kwaliteit, spiegelstatus, productiefeatures, referentiezijden, toleranties en productiebepalende afwerking. Een wijziging hiervan invalideert afgeleide productieartefacten.

## Transformaties

`Transform3D` bewaart oorsprong en lokale X/Y/Z-assen. Validatie eist:

- eindige getallen;
- eenheidsassen;
- onderlinge orthogonaliteit;
- determinant positief en vrijwel één;
- geen schaal of shear;
- geen stilzwijgende linksdraaiende spiegelbasis.

Spiegelstatus wordt als expliciete productiedata bijgehouden in plaats van verstopt in een ongeldige transform.

## Relatie-integriteit

- parent-/childrelaties van assemblies moeten wederkerig zijn;
- assemblycycli worden geweigerd;
- part-/assemblyrelaties moeten aan beide zijden kloppen;
- fasteners en welds mogen alleen naar bestaande onderdelen verwijzen;
- reserveringen mogen voorraadhoeveelheden niet overschrijden;
- aantallen, massa's, lengtes en oppervlakken mogen niet negatief of niet-eindig zijn.

## Provenance en menselijke controle

`FieldProvenance` kan per veld vastleggen:

- bronbestand, bronentity en bronpositie;
- methode: exact, parser, regel, AI of handmatig;
- confidence;
- status: automatisch, bevestigd, gecorrigeerd of afgeleid;
- reviewer en tijdstip.

AI-resultaten worden als voorstellen opgeslagen. Zij krijgen geen directe productieautoriteit.

## Validatie en productiepoort

`ValidationIssue` heeft niveau, code, entiteit, bron en blokkadestatus. De productiepoort blijft gesloten wanneer bijvoorbeeld:

- semantische import nog niet compleet is;
- een kritieke relatie ontbreekt;
- een manufacturing hash ontbreekt of verouderd is;
- materiaal, profiel of productiefeature ambigu is;
- een blokkerende waarschuwing niet is opgelost;
- een vereiste roundtripcontrole niet is geslaagd.

## Revisies en audit

Een projectrevisie wordt alleen aangemaakt wanneer de inhoudelijke projecthash wijzigt. Tijdelijke UI-/runtimevelden veroorzaken geen revisie. Een afzonderlijke manufacturing-state-hash maakt het later mogelijk BOM, optimalisaties en machinejobs gericht ongeldig te verklaren.

Iedere muterende serviceactie schrijft een auditregel met actor, actie, doel, tijdstip en relevante gegevens. Auditvelden worden niet gebruikt om inhoudelijke geometriegelijkheid te bepalen.


## Uitbreiding in 2.1

Project Model 2.1 voegt geen tweede geometriekern toe, maar legt semantische IFC/STEP-materialisatie vast: bronklasse, bronentiteit, product occurrence, spatial container, local/global placement, propertysets, materiaalevidence, geometry-subgraafhash, relationele assemblykoppeling en semantische importstatus.

External solids blijven `review_required` totdat zij via het Canonical Part Model en deterministische roundtripvalidatie productiegeschikt zijn verklaard.
