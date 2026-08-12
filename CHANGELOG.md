# Changelog

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
