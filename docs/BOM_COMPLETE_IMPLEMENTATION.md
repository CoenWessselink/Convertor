# BOM productiehub — complete implementatie 0.10.21

Deze oplevering sluit de zeven expliciete BOM-gaps op één canonieke
`ProjectModel 2.25`- en `BOMSnapshot`-autoriteit. De Windows-releaseworkflow
maakt op de exacte Git-SHA een machineleesbaar acceptance-rapport, acht echte
Qt-afbeeldingen, installer, portable pakket, bron-ZIP, Git-bundle, SBOM en
checksums.

| Eis | Implementatie | Bewijs |
| --- | --- | --- |
| Selectieafhankelijke actiematrix | 84 unieke acties, gegroepeerd per bekijken, bewerken, tekenen, machine/productie, voorraad/optimalisatie en export; enablement per familie, blocker en globale readiness | `BOMActionMatrix`; runtimecapture telt minimaal 75 acties |
| Veldniveau revisie en verwijderd | Canonieke entity-ID-correlatie over gewijzigde groepssleutels; before/after per veld; geometrie-, manufacturing- en featuredelta; historische verwijderde regels en rode 3D-bounds | `BOMHubState.revision_deltas`; revisietab; Viewer tombstones |
| Productiegereedheidskolommen | Elf afzonderlijke statussen: geometrie, materiaal, tekening, machine, nesting, NC, scribing, conflicten, vrijgave, productie en levering | 37-koloms `BomWorkspacePanel`; productiepreset |
| Voorraad/reststuk en inkoop | Deterministische first-fit packing met kerf, fysieke reserveringsrevisie en ledger; canonieke `PurchasedItem`-behoeften, edit en release | `BOMStockAllocator`; `BOMProcurementService`; projectroundtriptests |
| Slimme selectie/lasso/kleur | Persistente EN/OF-query's met tekst-, leegte- en numerieke operatoren; vrije schermpolygonen; selectie op effectieve renderkleur | `BOMScopeEngine.query`; `select_polygon`; `select_same_display_color` |
| Transacties/resultaten/undo | Eén projectbrede rollbacktransactie met snapshot- en preflighthash, succes/foutrapport, audit en runtime undo; gekoppelde release blokkeert undo | `execute_transaction`; `BOMBatchResult`; `_release_barrier` |
| Gedeelde rendercache | Procesbrede, thread-safe weak cache per exacte `MeshRepository`; immutable polydata en feature-edges gedeeld, actors/OpenGL per venster | `SharedRenderResourceCache`; hit/build-statistiek in Traceability |

## Automatische verificatie

```text
python tools/verify_bom_completion.py --output bom-completion-acceptance.json
python validation/run_all_smokes_v9.py --headless-windows --output validation/results/source-smokes
```

Op Windows voert `.github/workflows/build-windows-exe.yml` aanvullend de echte
Qt-capture, native selftest, PyInstaller-, portable-, installatie-, associatie-
en uninstallmatrix uit. Alleen een groen `CODEX_RELEASE_MANIFEST.json` geldt als
volledige softwareoplevering. Dit bewijs geeft geen fysieke machinevrijgave;
die grens blijft fail-closed.
