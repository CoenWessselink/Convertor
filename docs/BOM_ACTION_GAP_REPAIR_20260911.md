# BOM-actierouting: eerste gerichte gapreparatie — 11 september 2026

## Baseline en scope

Deze wijziging bouwt door op `e5e28fb4ce2a504f244dce829f5247a3af366cfc`,
branch `agent/cws-pdf-ui-v3-complete-20260909`. Geen oudere UI-branch gemerged,
geen vervangend programma. De bestaande project-, selectie-, JobManager-,
voorraad-, tekening-, export- en vrijgaveketens blijven leidend.

## Uitgevoerd

- **W01:** BOM-plaatnesting gaat naar de bestaande plaatnestinguitvoerder.
  Zowel plaat- als profielsolver krijgt uitsluitend expliciete geselecteerde
  canonieke onderdeel-IDs met hun werkelijke quantities/occurrences. Een lege,
  onbekende, gemengde of verkeerde familieselectie wordt niet verbreed.
- **W02:** aanbevelen, opnieuw controleren, alternatieven en uitleg gebruiken
  de bestaande machinedetails. Per onderdeel wordt ReadinessGate opnieuw
  uitgevoerd en worden bestaande capabilityrapporten met actuele
  manufacturing-hashbinding gecontroleerd. Het advies blijft zichtbaar na
  verversen; gewijzigde onderdelen/rapporten of beschadigde opgeslagen data
  maken het zichtbaar verouderd. Er worden geen assignments of machine- of
  transportrechten verleend. Dit is geen nieuwe fysieke machinekwalificatie
  of herberekening van nog ontbrekende capabilityrapporten.
- **W03 gedeeltelijk:** een expliciete, gehashte opdracht bewaart de actie,
  selectie, project-, BOM- en preflightbinding. Naar een scherm navigeren of
  exportinstellingen voorbereiden telt als `prepared`, niet als `passed`.
  Nesting telt pas als uitgevoerd na een werkelijk voltooid, geldig resultaat;
  project-/berekeningswissels blokkeren de oude callback.
- Reststukken wel/niet opnemen heeft effect op de daadwerkelijke
  plaatvoorraad of profielvoorraadpolicy. Deze keuze wordt met het plaatplan
  opgeslagen en bij heropenen hersteld. Fysieke voorraad wordt niet verzonnen.
- Expliciete NC1/STEP/IFC/DXF/PDF-keuzes worden met dezelfde geselecteerde IDs
  in het bestaande Export Center voorbereid. De actuele uitvoergates blijven
  vereist. Een geblokkeerd exportresultaat telt nooit als re-import verified,
  ook niet wanneer er al een package-pad bestaat.
- Niet-aangesloten groeperings-, alternatieven-, print- en batchtekenacties
  worden expliciet geweigerd, niet vervangen door een andere functie. Een
  handmatig gekozen niet-ondersteunde exportgroepering kan deze blokkade niet
  omzeilen. Combined is de expliciet ondersteunde packagegroepering.
- Een canonieke voorraadcompatibiliteitsfout is hersteld: oudere optionele
  voorraadvelden worden uit de bestaande properties gelezen, met ontbrekend
  bewijs als onbekend/leeg en niet als verzonnen certificaat.

## Bewijssoorten

1. `tests/bom_scope_safety_smoke.py`: domein- en veiligheidstests met werkelijke
   geselecteerde profielsolve/commit, voorraad en opgeslagen plaatplan.
2. `tests/bom_action_routing_smoke.py`: echte shipping Qt-panelen en QAction-
   triggers in een herkenbaar gelabelde testhost, echte plaatberekening en
   expliciet synthetische materiaal-/capabilitydata. Dit is geen complete
   hoofdapplicatie of machinekwalificatie.
3. `pdf_ui_v3_evidence.py`: extra machine-actie via echte QAction en echte
   bevestigingsdialoog in de bestaande native CWSMainWindow, zonder vervangen
   viewer of router. Vijf bron-DPI's en de drie packaged runtimes gebruiken
   dezelfde bestaande acceptatieketen.
4. `--bom-action-evidence` wordt in de nieuw geïnstalleerde EXE aangeroepen
   zonder externe Python op PATH. Het nieuwe rapport en screenshots worden
   aan dezelfde broncommit/EXE-hash gebonden en zijn verplicht bij promotie.
5. Bestaande BOM-selectie/undo, plaatintegratie, profielnesting en PDF/V3-
   regressies blijven verplicht. De bestaande skips worden niet als PASS
   gepresenteerd.

Lokale dirty-tree-tests zijn voorcontrole. Alleen een nieuwe clean-source
Windows-run met installer, onafhankelijke reopen, volledige regressies,
600-seconden-soak en de aanvullende BOM-bewijsgates mag een nieuwe beta
promoveren. Oude installers en bewijs van `e5e28fb4` bewijzen deze wijziging
niet. De finale broncommit wordt door de bouwmanifesten vastgelegd.

## Niet gesloten door deze wijziging

W03/W18 blijven deels open: afzonderlijke grouped packages, complete batch-/
print-/tekenacties, volledig onderscheid van XLSX/CSV/JSON reviewexports,
alle 87 acties met volledige transactie/revisie/undo-lifecycle, en relevante
voorraad/inkoop/las/renderer-cacheketens. Blokkeren is niet implementeren.
Het advies hergebruikt alleen brongebonden bestaande capabilityrapporten;
ontbrekende rapporten, machineprofielwijzigingen en externe fysieke afname
blijven afzonderlijke verantwoordelijkheden van de capability-/vrijgaveketen.

W04–W35 buiten de hier genoemde deelreparaties blijven ongewijzigd: onder meer
317 actuele requirements, skips, leveranciers-/extrusieherkenning, externe
PDF/AI, doelhardware/Trimble/60 UI-beelden, 481 referentiemodellen, machines,
ondertekening, update/rollback en licentieafname. Er is geen algemene
100%-herkenning of volledige productvrijgave geclaimd.
