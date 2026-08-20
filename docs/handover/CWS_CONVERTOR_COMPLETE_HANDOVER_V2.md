# CWS Convertor - complete overdracht V2

## Doel

Dit pakket is bedoeld om een nieuwe GPT/Codex-chat zonder verlies van technische context te starten. Het bundelt de actuele GitHub-branch, een bronarchief, de verified release, frozen donors, oorspronkelijke prompts, UI-referenties, voorbeeldmodellen en testbewijs.

## Pakketindeling

- `00_START_HERE`: actuele overdrachtsprompt, repositorygegevens, acceptatiestatus en derde-partijgrenzen.
- `01_SOURCE`: exact Git-archief van de branchcommit uit `BRANCH_SNAPSHOT.txt`.
- `02_RELEASE`: verified portable Windows-release, checksums en verificatierapporten.
- `03_FROZEN_DONORS`: aangeleverde Viewer V15-, Scribing M18- en Profile Nesting-overdrachten plus overige frozen referentiepakketten.
- `04_REFERENCE_IMAGES`: alle eerder expliciet genoemde ontwerp-, controle- en foutafbeeldingen die nog beschikbaar waren.
- `05_SAMPLE_FILES`: IFC-, STEP-, NC1- en XLSX-bestanden voor reproduceerbare tests.
- `06_ORIGINAL_PROMPTS`: historische startprompt, reuse matrix en masterprompt.
- `07_BIM_VISION`: lokale BIM Vision-inventaris, versies en hashes; geen herverdeelde propriëtaire binaries.
- `08_TEST_EVIDENCE`: bestaande acceptatie- en releasebewijzen.
- `09_MANIFESTS`: branchsnapshot, volledig SHA256-bestandsmanifest en ontbrekende-bestandenrapport.

## Wat is leidend

De actuele gebruikersopdracht en `CODEX_STARTPROMPT_CWS_CONVERTOR_NEW_CHAT_V2.md` zijn leidend. Historische prompts en afbeeldingen beschrijven oorspronkelijke doelen en visuele verwachtingen, maar mogen de huidige brancharchitectuur niet terugdraaien.

## Belangrijke technische keuzes

- Canoniek Project Model 2.25.
- Centrale `UnifiedApplicationContext`.
- Viewer V15 via `VtkRealProjectWidgetFeelV2` en bestaande VTK/OCCT-backends.
- Een gedeelde selectie tussen projectboom, tabel, viewer en properties.
- Elf unieke hoofdwerkruimten; PDF en Tekening zijn samengevoegd.
- Fail-closed productie- en exportgedrag bij onvoldoende bewijs.
- Geen runtime-afbeeldingen als vervanging van echte PySide6-widgets.

## Release gebruiken

Pak `02_RELEASE/CWS_Convertor_Portable_0.10.3-beta-dev_x64_verified.zip` volledig uit en start daarna `CWS_Convertor.exe`. Start de EXE niet los vanuit de ZIP en kopieer de EXE niet zonder de meegeleverde `_internal`-map.

## Bron gebruiken

De primaire bron is GitHub-branch `agent/cws-product-ui-reintegration-v1`. `01_SOURCE` is een offline snapshot van exact dezelfde commit. Gebruik GitHub voor vervolgwerk zodat geschiedenis, review en branchstatus behouden blijven.

## Beveiliging en licenties

Het pakket bevat geen GitHub-token, accountwachtwoord, licentiesleutel of andere secret. De gebruiker moet zelf bij GitHub en eventuele commerciele software zijn aangemeld. Derde-partijbestanden blijven onder hun eigen licenties vallen en mogen niet automatisch worden gepubliceerd.
