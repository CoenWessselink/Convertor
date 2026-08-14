# CWS Viewer V7 — Compare, revisions en robuuste correspondence

## Doel

V7 bouwt boven op de exacte V6-evidence een reproduceerbare compareworkspace voor:

```text
source ↔ canonical
revision A ↔ revision B
canonical ↔ roundtrip
```

## Werkpakketten

1. robuuste subshape-correspondentie bij topologiewijzigingen;
2. added/removed/moved/changed classificatie;
3. placement-only wijziging apart van manufacturing change;
4. materiaal-, profiel-, feature- en mirror-impact;
5. per-feature deviation overlays en heatmaps;
6. difference isolation in totaalmodel en Part Workbench;
7. machineleesbaar comparemanifest;
8. invalidatie van tekeningen, optimalisaties en jobs bij manufacturing change;
9. scribing proposals opnieuw valideren bij partner- of targetwijziging;
10. revision-safe viewpoints, measurements en reviewstate.

## Harde poort

- placement-only change houdt dezelfde manufacturing identity;
- materiaal/profile/feature/mirror change wordt correct geclassificeerd;
- deleted/added objects zijn herleidbaar naar source IDs;
- source/canonical en roundtripcompare leveren dezelfde deterministische metrics;
- onzekere correspondence blijft review/blocked;
- geen productieartefact wordt hergebruikt na relevante manufacturing change.
