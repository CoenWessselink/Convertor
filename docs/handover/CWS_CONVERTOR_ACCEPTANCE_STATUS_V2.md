# CWS Convertor - acceptatiestatus overdracht V2

## Vastgelegde levering

- Versie: `0.10.3-beta-dev`
- Platform: Windows x64, PyInstaller one-folder release.
- Verified portable ZIP SHA256: `93C92CEEF461FC733BB917E8FA5FCFDA481EA50D94083FAE214C42DA6BA4D31A`
- EXE SHA256 in verified release: `F1FF55757B082CA9D24F5BD5F71EDC5418A843EC6183D95FA9732905FFB55D49`

## Uitgevoerde acceptatie voor deze levering

- Acht van acht bronacceptatietests geslaagd.
- Packaged native self-test geslaagd.
- Packaged lege GUI-smoke geslaagd.
- Packaged project-GUI-smoke geslaagd.
- Elf unieke hoofdtabbladen aanwezig; dubbel tabblad `Tekeningen` verwijderd.
- IFC-, STEP-, NC1-, PDF-, OCCT- en VTK-roundtrips in de vastgelegde acceptatieronde geslaagd.
- Portable release bevat de benodigde Python-runtime en `_internal`-afhankelijkheden.

De gedetailleerde, machineleesbare rapporten staan in `02_RELEASE` en `08_TEST_EVIDENCE`.

## Bewuste grenzen

- Een willekeurige of gescande PDF is geen betrouwbare manufacturing-bron. Alleen een vertrouwde CWS-PDF met machineleesbare payload kan automatisch terugconverteren; overige PDF's gaan naar review.
- Productieautorisatie en machineoverdracht zijn niet automatisch vrijgegeven.
- SQL-, MATLAB- en commerciele solver-DLL's zijn niet toegevoegd omdat de actuele kern ze niet nodig heeft en licenties niet mogen worden omzeild.
- BIM Vision- en Trimble Connect-pariteit is een referentiedoel, geen gecertificeerde 100%-claim.
- Grote en leveranciersspecifieke IFC-bestanden kunnen aanvullende geometriegevallen bevatten; regressies moeten met de meegeleverde IFC-samples worden vastgelegd.
- Profiel- en materiaalherkenning moet onzekerheid en herkomst tonen; niet-herkende geometrie mag niet stilzwijgend als exact profiel worden gepresenteerd.

## Verplichte regressiepunten bij vervolgwerk

- Grote IFC laadt progressief en eindigt niet blijvend op 18%.
- Alle relevante geometrie, inclusief hoofdprofielen en bevestigingsmiddelen, blijft zichtbaar en correct geplaatst.
- Tabel-, boom- en viewerselectie lichten hetzelfde object in beide richtingen op.
- Viewer blijft scherp en bedienbaar bij orbit, pan, zoom, selecteren, meten, clip en doorsnede.
- Losgekoppelde viewer bevat dezelfde relevante viewerfuncties en gedeelde selectiecontext.
- Bewerken, Converteren, PDF/Tekening, BOM en Exporteren hebben elk een eigen functioneel scherm zonder overlap.
- Technische tekeningen passen lange onderdelen op het blad en behouden een geldige schaal en maatvoering.
- NC1-sleufgaten en verzonken gaten blijven brongetrouw.
