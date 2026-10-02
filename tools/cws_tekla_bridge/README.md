# CWS Tekla Bridge v0.1 — Build 01
Kleine Windows x64-bridge volgens het aangeleverde startpakket. Tekla blijft de primaire modelomgeving. Er is één samenhangende build met broncode, Windows-programma, beveiligde lokale API, controles en bewijsbestanden.

Dit is een **testbuild**. De productieautoriteit bevat geen goedgekeurde native writes. Het programma leest/plant/proposeert en toont ontbrekend bewijs. Een succesvolle API-call, fixturetest, compiler of disconnected UI-start is geen vrijgave van een Tekla-model.

## Starten
1. Start `installer/CWS_Tekla_Bridge_v0.1_Setup.exe` uit de installerbuild en doorloop de Nederlandstalige wizard. Deze installeert voor de huidige gebruiker en heeft geen beheerdersrechten nodig.
2. Start **CWS Tekla Bridge** uit het startmenu of via de gekozen bureaubladsnelkoppeling. Voor portable gebruik kunt u het complete pakket uitpakken en `windows/Cws.TeklaBridge.exe` starten. Windows 10 of hoger, x64 en .NET Framework 4.8 zijn vereist.
3. Vul bij Instellingen de daadwerkelijk geïnstalleerde Tekla-versie in en open het bedoelde model in Tekla. De compileerreferentie is API 2024.0.0; een afwijkende versie wordt geblokkeerd.
4. Kies **Verbinden**, laad een canonical SteelModel-JSON en maak eerst een plan. CHECK_ONLY en PROPOSE voeren geen native modelwrites uit.

De EXE-installer biedt ook verwijderen via Windows **Geïnstalleerde apps**. Instellingen, journal en reviewgegevens onder `%LOCALAPPDATA%/CWS/TeklaBridge` blijven bewaard. De Windows-CI controleert installeren, herinstalleren, de start van de daadwerkelijk geïnstalleerde app, bestandsintegriteit, snelkoppelingen en verwijderen. Zie `docs/INSTALLER.md` en de commitgebonden installerbewijzen.

`Install.cmd` in de scripts-map installeert deze versie voor de huidige gebruiker en maakt een bureaubladsnelkoppeling. Het installatiescript controleert eerst de pakketbestanden tegen PACKAGE_MANIFEST.json. De Windows-CI test dit script, de geïnstalleerde bestanden en de snelkoppeling. De productie- en Tekla-runtimegates blijven afzonderlijk. Bestaande CWS-macro's en Tekla-instellingen worden niet door dit pakket vervangen.

De bestaande Convertor-snapshot kan via `scripts/import_steel_model.py` read-only worden overgedragen. Die summary bevat geen volledige geometrie; de importer geeft daarom REVIEW_REQUIRED. Lees `docs/SOURCE_HANDOVER.md` voor de exacte grens.

## Uitgevoerde fasen en harde gates
| Fase | Code in deze build | Harde eindgate |
|---|---|---|
| 0 | Actuele GitHub-branch/bronfreeze; standaard v1.20; schemas, autorisatiematrix, authoritycontrole | Bron- en contracttests; native authority nog leeg |
| 1 | Compacte Windows x64-shell, 11 schermen, dynamische loopback API/sessiontoken, versiecontrole | Windows-startstatus in bewijsbestand; actieve Tekla-verbinding nog te bewijzen |
| 2 | Native model/part/catalogus/selectie lezen; canonical mapping; punten/plaatsing/bbox observeren | Echt Tekla-model nog te lezen/testen; exacte BRep/manufacturing niet bewezen |
| 3 | Gevalideerde plannen, native beam/polybeam/plate-code, journal/checkpoints, ownership-bescherming | Native write/save/reopen/idempotentie nog te bewijzen; standaard geblokkeerd |
| 4 | Bronfreeze, conflictbewaking, one-round planning/execution/readback, begrensde veilige herstelroute | Het Koraal offline broncontrole; native eindregressie NOT_RUN |
| 5 | Corpus-runner met SHA-controle, echte referentie/snapshot-vereisten | 20-modelcorpus NOT_RUN; geen fictieve vervanging |
| 6 | Revisies/delta, scoped planning, expliciete REMOVE-intentie en bescherming manual werk | Native revisieronde NOT_RUN; dependency graph/uitbreiding niet geïmplementeerd |
| 7 | Core-services voor connection fingerprints/analyse/voorstellen en families/attributes parser | Volledige UI/API-inspect/propose-werkstroom niet aangesloten; echte TS-map/detailvoorbeelden nog nodig |
| 8 | AUTO-authority/applicability/runtime/clash-gates | Native connection apply/readback niet geïmplementeerd; BLOCKED |
| 9 | Persistent review, scoped projectbesluiten, korte eenmalige lokale challenges, source-superseding | Besluit→native rebuild→persistentie nog te bewijzen |
| 10 | Reproduceerbare single-build CI, versiegebonden binair, hashes, installatiescript, releaseblokkades | Nummering/NC/productie NOT_RUN; Windows EXE- en scriptinstallatie zie afzonderlijke bewijsbestanden |

## Valideren en reproduceren
`powershell -File scripts/build.ps1 -Smoke -Installer` vanaf de exacte GitHub-branch met een schone bronversie. Dependencies zijn in packages.lock.json vastgelegd. De Windows-smoke maakt een echte afbeelding van het draaiende disconnected formulier en controleert de lokale API; dat is uitsluitend UI-startbewijs.

`dotnet exec artifacts/tests/Cws.TeklaBridge.Tests.dll --corpus corpus/manifest.json corpus-report.json` rapporteert ontbrekende echte referenties als NOT_RUN en eindigt dan met exitcode 2. Een fixture kan nooit RELEASED opleveren.

Iedere nieuwe native authority vereist bron-SHA, commit, schema, tests, echt runtimebewijs en referentiemodel op dezelfde bronversie. Geen engineeringbesluit wordt uit een tekstprompt of GPT-actor afgeleid. `force=true` bestaat niet.
