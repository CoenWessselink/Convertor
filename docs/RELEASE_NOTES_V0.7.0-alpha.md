# Release notes — CWS Convertor 0.7.0-alpha

## Nieuwe functionaliteit

- Semantische complete-modelimport voor IFC en STEP.
- Lazy Part 21-referentiegrafiek met ID-onafhankelijke geometry-subgraafhashes.
- Materialisatie van IFC assemblies, onderdelen, mechanische fasteners en Tekla-lasobjecten.
- Behoud van local/global placements, propertysets, materials, marks, part positions en spatial containment.
- AP242 product-/occurrence-import zonder fictieve splitsing op bestandsnaam.
- Project Model-schema 2.1 met semantische importmetadata.
- Transactionele import en idempotente herimport per bron.
- CLI-opdrachten `project-import`, `project-tree`, `project-list-parts` en `project-list-assemblies`.
- Functionele GUI-actie **Semantisch importeren** met achtergrondvoortgang.
- Knop **Annuleren** met coöperatieve parser/importerstop en transactionele rollback.
- Veilige `C_fused_review`-route wanneer STEP geen aantoonbare solid-root bevat.
- Grote STEP-modellen slaan een tweede zware profielherkenningspass over; die analyse wordt expliciet uitgesteld.
- Afzonderlijke grote-modelprestatiepoort voor de `11881`-referentie.

## Validatie

- 82/82 fasecontroles geslaagd.
- Tekla IFC: 353 assemblies, 2.429 parts, 723 fasteners en 2.654 lassen.
- Drie AP242-bestanden: ieder één product, één solid en één part.
- Bestaande NC1/STEP/IFC/PDF/AI-regressies blijven groen.

## Veiligheidsgrens

De release materialiseert bronsemantiek, maar verklaart externe solids nog niet productiegeschikt. NC1-, optimalisatie- en machine-uitvoer blijven geblokkeerd totdat classificatie en per-part feature/roundtripvalidatie zijn afgerond.

## Niet in deze alpha

- complete classificatie en BOM;
- onderdeeleditor en volledige projectgrid;
- revisievergelijking;
- handelslengteoptimalisatie en nesting;
- machinepostprocessors;
- native, schoon geteste Windows-installer.
