# PDF/UI V3 — native integratie in CWS Convertor

Specificatie: `CWS_CODEX_PDF_UI_INTEGRATIE_V3_2026-09-06(1)(1)(3).zip`.
SHA-256: `f20b9597ee02eab1c45f06d85ae3d652d03eaeddb68614cc3bbcd15716a7f06e`.
De volledige prompt en de drie referentiebeelden zijn als uitgangspunt gebruikt.
De programmaversie is 0.10.19-beta-dev. Definitieve broncommit en daadwerkelijke
uitkomsten staan uitsluitend in de bij deze build gegenereerde manifesten;
dit document op zichzelf verklaart geen test geslaagd.

## Integratie, geen vervanging

De bestaande CWSMainWindow, DrawingWorkspacePanel, ProjectSession, ProjectContext,
VTK-viewer en ProductionDrawingEngine/Renderer blijven de autoriteiten. PDF/Tekening
opent één gedeelde native tekenwerkplek. De oorspronkelijke externe-PDF-analyse blijft
als afzonderlijke route beschikbaar. Openen van een PDF opent die analyse en wisselt
niet het huidige modelproject om. Viewer, converteren, controleren, scribing, BOM,
beide nestingroutes en het bestaande Export Center blijven bereikbaar.

De presentatie volgt de driedelige referentieopbouw: model-/maatselectie links,
vectorblad in het midden en een contextgevoelige inspecteur rechts. De veertien
maattools zijn gegroepeerd. Bladformaat, oriëntatie, schaal en vijf aanzichten blijven
bewerkt via de bestaande instellingen. De groep aanzichten kan worden uitgeklapt.
De oorspronkelijke vijf hoofddomeinen en de overige productfuncties worden behouden.
Dit is geen pixel-identieke reproductie: bestaande productnavigatie, echte modelinhoud
en werkelijke reviewmeldingen gaan vóór de fictieve inhoud van de referentiebeelden.

## Requirement / code / bewijs

| Eisgroep | Productiecode | Verplicht bewijs |
|---|---|---|
| Native hoofdschil, één tekenautoriteit, behoud analyse | ui_qt/u4_shell.py, native_product_navigation.py | pdf_ui_v3_evidence.py; echte hoofdvensters, routewisseling |
| Toolbar 14 tools, model en assemblyselectie, vijf aanzichten | drawing_workspace_layout.py, functional_workspaces.py | drawing_workspace_v3_smoke.py, drawing_v3_inspector_smoke.py, volledige hoofdvenstertest |
| Maatselectie en directe inspecteur, tekst, tolerantie, positie | drawing_property_editor.py | drawing_v3_inspector_smoke.py, PDF12 V2, native toetsen/muis |
| Objectkleur, laag, lijntype, teksthoogte, pijltype | drawings/interactive.py, engine.py | drawing_ui_v3_presentation_smoke.py; atomaire bulkmutaties en checkergoedkeuring |
| Snaps, stabiele ID's, selectie, verplaatsen, re-anchor | interactive.py, drawing_dimension_canvas.py | interactive_dimension_editor_v2_smoke.py, drawing_canvas_native_events_smoke.py |
| Geometrische nominale maat blijft ongewijzigd | interactive.py, drawing_property_editor.py | directe inspecteurtest plus native vergelijking vóór/na |
| Undo/redo, projectopslag en onafhankelijke herstart | ui_v51_contract.py, ProjectSession | run_pdf_ui_v3_acceptance.py; verschillende PIDs, pakket-SHA en alle maatvelden |
| Assemblytekening zonder hoofdonderdeelterugval | engineering_drawing.py | drawing_v3_completion_smoke.py; twee werkelijk ingelezen STEP-componenten |
| Vaste schaal exact of expliciet geweigerd; A0–A4 | drawings/engine.py | drawing_v3_all_sheet_scale_smoke.py; onafhankelijke PDF MediaBox-controle |
| Vectorpreview en uitvoer uit één document | drawings/renderer.py | production_drawing_renderer_parity_smoke.py; onafhankelijke PDF-parser |
| BOM, linter, revisies, readonly en releasebeveiliging | drawing_workspace_layout.py, interactive.py, linter.py | V3 completion/inspector/presentation, PDF12 native 35 controles |
| Normal / Trusted / externe PDF fail closed | engineering_drawing.py, bestaande PDF-keten | positieve bekende-NC1 Trusted roundtrip, negatieve assembly, 12 conversieroutes |
| DPI 100/125/150/175/200, glyphs en primaire bediening | drawing_workspace_layout.py, runtime_typography.py | vijf verse hoofdvensterprocessen plus vijf onafhankelijke herstarts |
| 43 PDF-functies met daadwerkelijke testbinding | build_pdf_function_proof.py, pdf_function_test_binding.py | PDF_FUNCTION_GAP_MATRIX, FUNCTION_TEST_EXECUTION, onafhankelijk gerenderde PDFs en proofbook |
| Phase 1, 2, 3, regressie, 600-seconden soak | bestaande gates, run_phase3_gates.py | commitgebonden CI-kern, vier regressiegroepen en verse Phase 3 |
| Onefolder, vers uitgepakte portable, geïnstalleerd | build_tested_installer.py | 35 PDF12-interacties per runtime, native hoofdvenster plus tweede proces per runtime |
| Herinstallatie, uninstall, gebruikerdata en associaties | bestaande Inno-/acceptatieketen | INSTALLER_ACCEPTANCE.json; daadwerkelijke cleanupscan |
| Zelfde bron, EXE en bewijs, geen oude installer | verify_integrated_delivery.py, finalize_ui_v3_delivery.py | RELEASE_MANIFEST, PDF_RUNTIME_EVIDENCE, SHA256SUMS |

## Gebruik en veiligheidsgrenzen

Kies PDF/Tekening in de bestaande hoofdapplicatie en selecteer een onderdeel of assembly
in de modelboom. Selecteer een maat voor contextvelden. De globale knoppen Ongedaan
maken en Opnieuw gebruiken de tekenhistorie wanneer de tekenwerkplek actief is.
Ctrl+S slaat het project op. Een tekstoverride is geen geometriewijziging en vereist
motivering; afwijkende maatstijlen vereisen checkergoedkeuring voor vrijgave.
Niet-passende vaste schaal wordt geweigerd; Auto of een passende schaal herstelt het blad.

Normale PDF-uitvoer mag review-inhoud duidelijk weergeven. Trusted export mag nooit
ontbrekende assembly-authoriteit vervangen door één onderdeel. De positieve Trusted
voorbeeldtest gebruikt een expliciet bekende NC1-bron en controleert een byte-exacte
roundtrip. Dit is geen productievrijgave van een willekeurige STEP-assembly.

Ruwe screenshots zijn echte Qt-hoofdvensteropnamen, zonder nagemaakt achtergrondbeeld.
De 43 functiebeelden zijn herkenbaar gelabelde kopieën van die opnamen of onafhankelijke
PDF-rasterisaties; de ruwe originele beelden en hashes blijven behouden. Meerdere eisen
kunnen dezelfde testmethode gebruiken: 43 eisen is niet hetzelfde als 43 disjuncte tests.
Een PASS voor een negatieve test betekent dat de onveilige handeling geweigerd is.

De installer is een niet digitaal ondertekende softwarebeta. Windows CI met Mesa is
geen meting op de eigen werkplek, geen certificering van machinepostprocessors en geen
universele materiaalherkenningsgarantie. Verklaarde externe-/hardware-skips blijven
zichtbaar; zij worden niet als geslaagd meegeteld. Historische upgrades buiten de
geteste herinstallatie van dezelfde versie blijven afzonderlijke acceptatie.
