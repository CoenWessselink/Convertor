# Changelog

## v0.5.1

### Deterministische maatgrafiek

- Nieuwe `dimension_graph.py` met feature-gekoppelde maatobjecten en stabiele ID's.
- Totale hoofdafmetingen, gatdiameters, X/Y-ordinaten vanaf vaste datums, radii en profiel-/diktegegevens worden uit het canonieke model opgebouwd.
- Provenance, confidence, geometrische ankers, featureverwijzingen en maatketens worden per maat opgeslagen.
- Releasevalidatie controleert waarden, ankers, referenties, duplicaten, ketens en verplichte dekking.
- Trusted PDF-export wordt geblokkeerd bij een ongeldige of gemanipuleerde maatgrafiek.

### Interactieve PDF-review

- Nieuwe `review_workflow.py` met strikte allow-list voor menselijke correcties.
- Nieuwe `review_dialog.py` met bron-PDF links en deterministisch 2D-model rechts.
- Bronbewijs en modelonderdelen kunnen vanuit de veld-/featurelijst worden gemarkeerd.
- Veldwaarden, gaten en contourpunten kunnen gecontroleerd en gecorrigeerd worden.
- Blokkerende vragen kunnen worden beantwoord of door expliciete bewijsbevestiging worden opgelost.
- Reviewer, commentaar en auditinformatie worden in het canonieke model vastgelegd.
- `pdf-review` CLI-route en **Interactief reviewen** in de GUI toegevoegd.

### Externe vector-PDF naar productieobject

- Eenvoudige platen/strips kunnen na deterministische reconstructie en expliciete review als Trusted PDF worden vastgelegd.
- De synthetische LO4-keten behoudt gesloten contour, twee analytische R13,5-bogen, één analytisch Ø14-gat op X/Y 20 mm, materiaal, profiel, aantallen en titelgegevens.
- Reviewed PDF -> NC1 -> STEP -> semantisch IfcPlate -> Trusted PDF is als volledige testketen uitgevoerd.

### AI en GUI

- OpenAI-modelkeuze is zichtbaar en configureerbaar in het PDF/Tekening-tabblad.
- Standaardmodel voor de optionele provider is `gpt-5.6`.
- API-sleutel wordt uitsluitend uit `OPENAI_API_KEY` gelezen en niet in projectbestanden opgeslagen.
- AI blijft adviserend; geometry-/machinecodeguard en expliciete cloudtoestemming blijven verplicht.

### Distributie en validatie

- Versie verhoogd naar 0.5.1 in broncode, installer, workflow en buildscript.
- Windows-workflow voert ook maatgrafiek- en reviewsmokes uit.
- Workflow installeert de gebouwde applicatie stil, test de CLI met een minimaal systeem-`PATH` zonder Python en voert daarna de uninstaller uit.
- NC1 -> Trusted PDF -> exact NC1: 24/24 geslaagd.
- STEP -> Trusted PDF -> exact STEP: 19/19 geslaagd.
- Focus Trusted PDF -> IFC: 2/2 geslaagd.
- Synthetische LO4-keten: 1/1 geslaagd.
- AI-, integriteits-, review- en ambiguiteitstests: 11/11 geslaagd.

## v0.5.0

### Canoniek model en veiligheid

- Canoniek schema uitgebreid naar 1.1 met provenance, confidence, veldstatus, tekengegevens, open vragen, auditlog en vrijgavestatus.
- Gehashte payloads blijven achterwaarts compatibel met schema 1.x.
- Limieten, checksumcontrole en veilige decompressie toegevoegd aan payload en bijlagen.
- De onveilige productievalidatiebypass is uit GUI en CLI verwijderd; strikte controle is verplicht.

### IFC

- Converter-eigen IFC4 bevat zichtbare geometrie plus exacte gehashte productiedata.
- Analytische fallback uitgebreid met cirkel-, cilinder- en contourfitting en confidence.
- D20-rondstaal blijft analytisch rond in de verplichte roundtrip.
- Alle acht focusroundtrips zijn opnieuw geslaagd.

### Trusted Converter PDF

- Nieuwe bidirectionele technische PDF-laag.
- NC1, STEP en IFC kunnen een vectoriele onderdeeltekening genereren.
- Exact canoniek model, originele bron, XMP en zichtbare-tekeninghash worden ingesloten.
- Bronbijlage, canonieke hash, geometriehash, XMP en zichtbare hash worden bij import gecontroleerd.
- Zichtbare wijziging en beschadigd manifest blokkeren terugconversie.
- Standaard tekenschalen worden daadwerkelijk toegepast en correct in het titelblok vermeld.
- Titelblok, stukregel, hoofdmaten, diametercallouts, radii en doorsnede toegevoegd.
- Conceptwatermerk toegevoegd voor niet-vrijgegeven onderdelen.

### Externe PDF en AI

- Externe PDF-classificatie toegevoegd: vector, raster, hybride of tekst-only.
- Bladformaat, oriëntatie, tekst, vectorpaden, afbeeldingen en kwaliteitsscore worden lokaal geanalyseerd.
- Stukregel-, profiel-, materiaal-, positie-, lengte-, aantal-, merk-, schaal-, gat- en radiusherkenning toegevoegd.
- Lokale offline semantische AI-/regelprovider toegevoegd.
- Optionele OpenAI Responses-provider toegevoegd met expliciete toestemming, `store=false`, Structured Outputs, afbeeldinginput en request-ID-audit.
- AI-uitvoer is beperkt tot toegestane semantische velden; productiegeometrie, coördinaten, NC1, STEP en IFC worden actief geweigerd.
- Deterministische PDF-extractie blijft leidend en kan niet stilzwijgend door AI worden overschreven.
- PDF/AI-reviewtabblad en CLI-commando's toegevoegd.

### Distributie

- Runtimebasis voor Windows-release gewijzigd naar Python 3.12 x64.
- PyMuPDF en templates aan requirements/PyInstaller toegevoegd.
- GUI en CLI worden samen als PyInstaller `onedir` gebouwd.
- Inno Setup-project toegevoegd voor één installer-EXE, uninstaller, snelkoppelingen en bestandskoppelingen.
- PDF-contextmenu toegevoegd zonder de standaard PDF-lezer over te nemen.
- GitHub Actions-workflow uitgebreid met alle regressies, portable ZIP, installer-EXE en SHA-256-checksums.

### Validatie

- NC1 -> STEP: 24/24 geslaagd.
- STEP -> NC1: 19/19 geslaagd.
- NC1 -> IFC -> STEP -> NC1: 4/4 geslaagd.
- STEP -> IFC -> NC1 -> STEP: 4/4 geslaagd.
- PDF/AI-suite: 4 positieve tests geslaagd en 3 negatieve gevallen correct geblokkeerd.
- Echte LO4-PDF nog niet lokaal binair beschikbaar; synthetische LO4-test is daarom expliciet alleen semantisch.

## v0.4.0

- Canoniek onderdeelmodel en lossless IFC-payload ingevoerd.
- Converter-eigen IFC-roundtrips voor de acht focusbestanden hersteld.
- Ingebouwde IFC4-lezer/schrijver toegevoegd voor converter-eigen bestanden.

## v0.3.0

- IFC-richtingen, hoeveelheden/Excel en uitgebreidere viewer toegevoegd.
- Profielendatabase uitgebreid naar 1.718 records.

## v0.2.0

- STEP -> NC1 uitgebreid naar standaardprofielen via profielendatabase.
- Visuele vergelijking links/rechts toegevoegd.

## v0.1.0

- Eerste lokale NC1 -> STEP en beperkte STEP -> NC1 prototypeversie.
