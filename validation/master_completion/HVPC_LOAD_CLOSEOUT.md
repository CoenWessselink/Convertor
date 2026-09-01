# HVPC Viewer Load Closeout V2

Status: **PARTIAL**

## Resultaat

- De volledige HVPC-bron bevat 5.725 fysieke IFC-objecten.
- De production identity route gebruikt 1.496 exacte meshresources en 4.229 veilige instanties.
- De echte scene bevat 5.725 nodes, 5.725 unieke selecteerbare identities en 5.725 unieke IFC-bron-ID's.
- Er zijn geen ontbrekende, dubbele, lege of proxy-objecten.
- De cold exact-load verbeterde van 71,041 s naar 7,939 s (88,82%).
- Een volledige herhaalde tessellatie in dezelfde persistente workers duurt 5,380 s.
- MeshCache V2 warm-load duurt 0,075 s; same-session cache-read circa 0,021 s.

## Gate

`cold <= 5,0 s` is nog **FAIL**. Daarom wordt deze fase niet vals als compleet gemarkeerd. Geometriecompleetheid, unieke selectie-identiteit, persistente IFC-workers, bronmodelhergebruik en warm-load zijn **PASS**.

## Technische wijzigingen

- Een grote IFC-bron wordt over echte procesworkers geshard.
- De automatische HVPC-klasse gebruikt 3 workers en maximaal 16 iterator-threads per shard.
- Geopende IFC-modellen blijven per worker gecachet op `(source_path, source_sha256)`.
- Semantisch identieke meshes worden eenmaal getesselleerd en per fysieke placement geinstantieerd.
- Iedere instantie houdt een unieke `entity_id` en de oorspronkelijke IFC STEP-id als `source_entity_id`.

## Visuele/equivalentiecontrole

Tien semantische groepen hadden meerdere ruwe arrayhashes. Zeven verschillen alleen in arrayvolgorde. Drie verschillen uitsluitend subnanometrisch; gelijke bounds, oppervlak en volume zijn vastgesteld en de maximale Hausdorff-afwijking is `8,3e-10 mm`.
