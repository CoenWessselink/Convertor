# BOM productiehub — complete implementatie 0.10.21

Deze oplevering sluit de zeven expliciete BOM-gaps op één canonieke
`ProjectModel 2.25`- en `BOMSnapshot`-autoriteit. De Windows-releaseworkflow
maakt op de exacte Git-SHA een machineleesbaar acceptance-rapport, acht echte
Qt-afbeeldingen, installer, portable pakket, bron-ZIP, Git-bundle, SBOM en
checksums.

| Eis | Implementatie | Bewijs |
| --- | --- | --- |
| Selectieafhankelijke actiematrix | 87 unieke acties, gegroepeerd per bekijken, bewerken, tekenen, machine/productie, voorraad/optimalisatie en export; enablement per familie, blocker, fysieke beschikbaarheid, tekening-, machine-, inkoop-, NC-, vrijgave- en globale readiness | `BOMActionMatrix`; runtimecapture en acceptance controleren minimaal 87 unieke acties |
| Veldniveau revisie en verwijderd | Canonieke entity-ID-correlatie over gewijzigde groepssleutels; exacte `BOMFieldDelta`-paden met before/after per BOM- én entityveld; geometrie-, manufacturing- en featuredelta; historische verwijderde regels en rode 3D-bounds | `BOMHubState.revision_deltas`; revisietab; Viewer tombstones |
| Productiegereedheidskolommen | Elf afzonderlijke statussen: geometrie, materiaal, tekening, machine, nesting, NC, scribing, conflicten, vrijgave, productie en levering | 37-koloms `BomWorkspacePanel`; productiepreset |
| Voorraad/reststuk en inkoop | Deterministische occurrence-packing over gemengde fysieke reststukken en handelslengten met kerf, gedeeltelijke plannen, optimistische reserveringsrevisie en één atomaire ledgertransactie; exact resterend tekort voedt canonieke `PurchasedItem`-behoeften; edit, vrijgave, annulering en reserveringsvrijgave zijn beschikbaar | `BOMStockAllocationPlan`; `BOMStockAllocator.reserve_plan`; `BOMProcurementService`; restart-roundtriptests |
| Slimme selectie/lasso/kleur | Persistente, recursief geneste EN/OF/NIET-query's met tekst-, leegte- en numerieke operatoren; vrije schermpolygonen met volledige polygon/rechthoek-intersectie; selectie op effectieve renderkleur | `BOMQueryGroup`; `BOMScopeEngine.query`; `select_polygon`; `select_same_display_color` |
| Transacties/resultaten/undo | Eén projectbrede rollbacktransactie met snapshot- en preflighthash, succes/foutrapport per BOM-groep, duur, audit en persistente inverse patch; undo werkt na projectherstart, blokkeert bij latere inhoudswijziging en blijft gekoppeld aan externe vrijgaven | `execute_transaction`; `BOMBatchResult.item_results`; `persistent_inverse_patch`; `_release_barrier` |
| Gedeelde rendercache | Procesbrede, thread-safe weak cache per exacte `MeshRepository`; mesh-hashgebonden immutable polydata en feature-edges gedeeld, automatische invalidatie bij geometrievervanging en identity-hashbewijs; actors/OpenGL blijven per venster | `SharedRenderResourceCache.evidence`; `MeshRepository.revision`; hit/build/invalidation-statistiek in Traceability |

## Automatische verificatie

```text
python tools/verify_bom_completion.py --output bom-completion-acceptance.json
python validation/run_all_smokes_v9.py --headless-windows --output validation/results/source-smokes
```

Het acceptance-rapport gebruikt schema `cws-bom-completion-acceptance-2.0` en
rapporteert elk van de zeven eisen afzonderlijk met een voltooiingspercentage.
Op Windows voert `.github/workflows/build-windows-exe.yml` aanvullend de echte
Qt-capture, native selftest, PyInstaller-, portable-, installatie-, associatie-
en uninstallmatrix uit. Alleen een groen `CODEX_RELEASE_MANIFEST.json` geldt als
volledige softwareoplevering. Dit bewijs geeft geen fysieke machinevrijgave;
die grens blijft fail-closed.
