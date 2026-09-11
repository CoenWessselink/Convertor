# PDF/UI V3 — originele specificatie en herstelcontrole

## Exacte invoer en bron

De gebruiker heeft `CWS_CODEX_PDF_UI_INTEGRATIE_V3_2026-09-06(2).zip` opnieuw aangeleverd.
De daadwerkelijk gelezen 4.022.148 bytes hebben SHA-256
`f20b9597ee02eab1c45f06d85ae3d652d03eaeddb68614cc3bbcd15716a7f06e`.
Alle zes manifestbestanden zijn afzonderlijk gehasht; volledige prompt, README,
referentietoelichting en alle drie originele PNG's zijn gelezen/bekeken. De
bestandsnaam verschilt, de bytes zijn identiek aan de historische specificatie.

Hervat vanaf de opnieuw gecontroleerde branch-HEAD
`abe29e0447b8bed034711eddf7cf2bffdaa74e7a` en tree
`ef4fa2423def5ac194facf47f473e5a3c770c855`. De lokale bron is per Git-blob en
volledige tree tegen de commitgebonden bronsnapshot gecontroleerd, met lege
werkboom vóór wijzigingen. Er is geen oudere UI-branch gemerged of vervangend
programma gebouwd. De drie oorspronkelijke basiscommits zijn in de ancestry
van de bronsnapshot bevestigd. Een remote GitHub-commit zegt niets over
niet-gepusht werk op een andere computer; dat is niet als gecontroleerd geclaimd.

`pdf_ui_v3_original/INPUT_REVIEW.json` bevat de originele bestandshashes, werkelijke
afmetingen en de visuele vergelijking. De originele tekstbestanden staan
byte-identiek in dezelfde map. De originele PNG's zijn designinput, geen runtime-
bewijs en geen UI-achtergrond. De ZIP/PNG-bytes zijn vóór commit gecontroleerd;
CI herhaalt de hashcontrole van de vastgelegde tekst en review, niet van PNG's
die niet in zijn checkout staan. De oorspronkelijke ZIP blijft bij de chatoplevering.
`tools/verify_original_pdf_ui_spec.py --archive <originele ZIP> --output <rapport>`
herhaalt desgewenst de volledige controle van de daadwerkelijke ZIP-bytes.

## Gerichte correcties na inhoudelijke controle

1. Vrijgave regenereert de bestaande tekening vanuit de actuele selectie en
   componentgeometrie, controleert documentbinding en voert DrawingLinter opnieuw uit.
   Ontbrekend, leeg of vals groen cachebewijs is nooit een vrijgaveautorisatie.
   De nieuwe native regressie was vóór herstel rood op drie concrete aanvallen.
   Geen nieuwe drawing-engine of extra projectstore is toegevoegd.
2. De canonieke DimensionGraph levert `dimension_ids`, datum, absolute ketens en
   totaalmaat. De eerdere linter controleerde uitsluitend het andere `members`-
   contract en blokkeerde daardoor ook een correct gecontroleerde gatplaat.
   Beide expliciete contracts worden nu gevalideerd. Ontbrekende/dubbele/onbekende
   verwijzingen, niet-eindige waarden, afwijkende cumulatieve/absolute ketens en
   overschrijding van de totaalmaat blokkeren. De bestaande 0,05 mm graphtolerantie
   is behouden. Ongeldige DimensionGraph-validatie is geen actuele Trusted-authoriteit.
3. De onderste statusregel wordt niet meer verticaal afgesneden. Lange teksten zijn
   herkenbaar afgekort met volledige tooltip/toegankelijke beschrijving; de Linter-tab
   houdt alle afzonderlijke meldingen beschikbaar. Nominale maten worden niet gewijzigd.

Een positieve native knoptest gebruikt een gedeclareerde synthetische canonieke
plaat, werkelijke BREP-rebuild, NC1/STEP/IFC/PDF-roundtrips en Workbench-vrijgave.
Hierna moet de echte maatvoering-vrijgaveknop slagen. Negatieve tests blijven blokkeren.
Het echte hoofdvenster test cachebeschadiging ook binnen bron, onefolder, portable
en geïnstalleerde EXE. De finale gate vereist deze nieuwe testnamen in alle acht
runtime-/DPI-groepen: oude screenshots of rapporten kunnen ze niet vervangen.

## Vergelijking per originele afbeelding

| Referentie | Overgenomen informatiehiërarchie | Bewuste afwijkingen en bewijs |
|---|---|---|
| 01 — volledige werkruimte | Native gegroepeerde maattools, blijvend zichtbare papierinstellingen, modelboom, vectorblad, inklapbare inspecteur | Bestaande CWS-hoofdschil/productnavigatie blijft behouden. Echte STEP-geometrie bepaalt schaal en bladinhoud. Oranje Review in plaats van een fictieve vaste PASS. `UI3-01-native-workspace.png`. |
| 02 — maat selecteren/bewerken | Echte selectiegrips, geometrische ankers, inline offset/tolerantie/prefix/suffix/opmaak, puntgestuurd verplaatsen en herankeren | Gegroepeerde eigenschappenboom met verticale scroll, geen tweede modal als primaire inspecteur. Gemengde multiselectie overschrijft geen ongewijzigde velden. Geen fictieve DWG of hardcoded 1250 mm. `UI3-02-native-selection-inspector.png` en PDF-GUI-16 t/m 24. |
| 03 — assembly, persistentie, linter | Afzonderlijke P1/P2-identiteiten, assemblymaten, modelboom/BOM/revisies/linter, onafhankelijke projectherstart | Contexttabbladen bewaren tekenruimte. Alleen echte opgeslagen status wordt getoond. Een niet-gekwalificeerde mesh-assembly blijft Review/Trusted-geblokkeerd zonder partfallback. `UI3-04`, `UI3-07`, `UI3-08`, PDF-GUI-28 t/m 35. |

Dit is een inhoudelijke vergelijking met de oorspronkelijke referenties, geen
pixel-identieke reproductie of onafhankelijke handmatige goedkeuring van alle
Windows-/hardwarecombinaties. De oorspronkelijke CWS-stijl heeft conform de
opdracht voorrang. Nieuwe screenshotbestanden en hashes staan uitsluitend in de
uiteindelijke runtime-manifesten; lokale werkboomproeven zijn geen releasebewijs.

## Requirement-to-code en verplichte uitvoering

De volledige originele prompt staat in
`pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md`.
De tabel in `PDF_UI_V3_NATIVE_INTEGRATION.md` koppelt alle hoofdgroepen aan de
bestaande authorities en tests. Aanvullend zijn nu verplicht:

| Gerichte eis | Productiecode | Test/bewijs |
|---|---|---|
| Geen vrijgave met ontbrekend/tegenstrijdig bewijs | `functional_workspaces.py::_release_dimension_revision` | `drawing_v3_release_evidence_smoke.py`, echte native `UI3-08`, 8 runtime/DPI-rapporten |
| Canonieke ketens en positieve geldige vrijgave | `drawings/linter.py`, `engineering_drawing.py` | `drawing_canonical_chain_binding_smoke.py`, positieve native vrijgave met 4 echte roundtrips |
| Volledige status toegankelijk, geen verticale clipping | `drawing_workspace_layout.py::_DrawingStatusLabel` | Gerichte statustest en echte hoofdvenstercontrole bij elke DPI/runtime |
| Originele invoercontrole niet vervangen door hardcoded hash | `verify_original_pdf_ui_spec.py` | `ui_v3_original_input_smoke.py`, inputreview + ongewijzigde prompt in uiteindelijke release |
| Geen oude groene rapporten na beveiligingsherstel | `finalize_ui_v3_delivery.py` | Negatieve manifesttest en verplichte nieuwe checks in alle 8 rapportgroepen |

Alle bestaande gate-eisen blijven staan: PDF-V2 23 tests zonder fail/skip, 43
PDF-functies met daadwerkelijke uitvoering, 35 PDF-GUI-scenario's, volledige
Phase 1/2/3 en 600 seconden soak, 12 packaged conversieroutes, vijf DPI's,
drie runtimes, onafhankelijke herstarts, installatie/herinstallatie/uninstall.
De 35 oudere scenario's gebruiken een echte productiepanel met gedeclareerde
synthetische fixture; de extra hoofdvensterproeven gebruiken werkelijke STEP-intake
in de volledige native CWS-app. Dit zijn verschillende, elkaar aanvullende
bewijslagen. Geen enkel designbeeld geldt als screenshotbewijs.

## Oplevergrens

De definitieve broncommit, echte aantallen en checksums staan in de gegenereerde
releasebestanden. Dit document bevat geen vooraf toegekende test-PASS.
Het resultaat blijft een niet-ondertekende softwarebeta: geen universele
herkenningsgarantie, hardwarecertificering, machineautorisatie of vrijgave van
onvoldoende bewezen assemblygeometrie. Historische upgrades buiten de geteste
herinstallatie blijven afzonderlijk te kwalificeren. Deze grenzen mogen niet met
het percentage van de concrete 43 geautomatiseerde PDF-functies worden verward.
