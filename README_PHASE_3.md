# CONVERTOR Phase 3 - Release Gate kandidaat

Dit pakket bevat de opgeschoonde volledige broncode van app en api, zonder node_modules, plus bewijsbestanden.

In deze fase is vastgezet:
- schone bronstructuur zonder node_modules
- app unit tests geslaagd
- app productiebuild geslaagd
- api unit tests geslaagd
- api smoke flow geslaagd: health, login, me, upload, jobs, detail, viewer, dxf
- release-documentatie toegevoegd

Belangrijk:
De browser-E2E met Playwright is in deze omgeving NIET groen geworden, omdat de vereiste Chromium Playwright-browser niet aanwezig was.
Daarom mag deze fase niet als 100% definitief vrijgegeven worden zolang die browser-run niet alsnog groen is gemaakt.
