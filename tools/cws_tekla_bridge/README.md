# CWS Tekla Bridge v0.1 — Build 01
Kleine Windows x64-bridge volgens het aangeleverde startpakket. Tekla blijft de primaire modelomgeving. Er is één samenhangende build met broncode, Windows-programma, beveiligde lokale API, controles en bewijsbestanden.

Dit is een **testbuild**. De productieautoriteit bevat geen goedgekeurde native writes. Het programma leest/plant/proposeert en toont ontbrekend bewijs. Een succesvolle API-call, fixturetest, compiler of disconnected UI-start is geen vrijgave van een Tekla-model.

## Starten
1. Pak het complete pakket uit.
2. Start `windows/Cws.TeklaBridge.exe` op Windows x64 met .NET Framework 4.8.
3. Vul bij Instellingen de daadwerkelijk geïnstalleerde Tekla-versie in en open het bedoelde model in Tekla. De compileerreferentie is API 2024.0.0; een afwijkende versie wordt geblokkeerd.
4. Kies **Verbinden**, laad een canonical SteelModel-JSON en maak eerst een plan. CHECK_ONLY en PROPOSE voeren geen native modelwrites uit.

`Install.cmd` in de scripts-map installeert deze versie voor de huidige gebruiker en maakt een bureaubladsnelkoppeling. Het installatiescript controleert eerst de pakketbestanden tegen PACKAGE_MANIFEST.json. De Windows-CI test dit script, de geïnstalleerde bestanden en de snelkoppeling. De productie- en Tekla-runtimegates blijven afzonderlijk. Bestaande CWS-macro's en Tekla-instellingen worden niet door dit pakket vervangen.

De bestaande Convertor-snapshot kan via `scripts/import_steel_model.py` read-only worden overgedragen. Die summary bevat geen volledige geometrie; de importer geeft daarom REVIEW_REQUIRED. Lees `docs/SOURCE_HANDOVER.md` voor de exacte grens.

## Uitgevoerde fasen en harde gates
| Fase | Code in deze build | Harde eindgate |
|---|---|---|
| 0 | Actuele GitHub-branch/bronfreeze; standaard v1.20; schemas, autorisatiematrix, authoritycontrole | Bron- en contracttests; native authority nog leeg |
| 1 | Compacte Windows x64-shell, 11 schermen, dynamische loopback API/sessiontoken, versiecontrole | Windows-startstatus in bewijsbestand; actieve Tekla-verbinding nog te bewijzen |
| 2 | Native model/part/catalogus/selectie lezen; canonical mapping; onafhankelijk geometry-readback | Echt Tekla-model nog te lezen/testen |
| 3 | Gevalideerde plannen, native beam/polybeam/plate-code, journal/checkpoints, ownership-bescherming | Native write/save/reopen/idempotentie nog te bewijzen; standaard geblokkeerd |
| 4 | Bronfreeze, conflictbewaking, one-round planning/execution/readback, begrensde veilige herstelroute | Het Koraal offline broncontrole; native eindregressie NOT_RUN |
| 5 | Corpus-runner met SHA-controle, echte referentie/snapshot-vereisten | 20-modelcorpus NOT_RUN; geen fictieve vervanging |
| 6 | Revisies/delta, scope/dependencies, expliciete REMOVE-intentie en bescherming manual werk | Native revisieronde NOT_RUN |
| 7 | Fingerprints, families/attributes parser, connection inspect/propose | Echte TS-map/detailvoorbeelden nog nodig voor bewijs |
| 8 | AUTO-authority/applicability/runtime/clash-gates | Native connection apply/readback niet geïmplementeerd; BLOCKED |
| 9 | Persistent review, scoped projectbesluiten, korte eenmalige lokale challenges, source-superseding | Besluit→native rebuild→persistentie nog te bewijzen |
| 10 | Reproduceerbare single-build CI, versiegebonden binair, hashes, installatiescript, releaseblokkades | Nummering/NC/productie NOT_RUN; Windows-scriptinstallatie zie bewijsbestand |

## Valideren en reproduceren
`powershell -File scripts/build.ps1 -Smoke` vanaf de exacte GitHub-branch met een schone bronversie. Dependencies zijn in packages.lock.json vastgelegd. De Windows-smoke maakt een echte afbeelding van het draaiende disconnected formulier en controleert de lokale API; dat is uitsluitend UI-startbewijs.

`dotnet exec artifacts/tests/Cws.TeklaBridge.Tests.dll --corpus corpus/manifest.json corpus-report.json` rapporteert ontbrekende echte referenties als NOT_RUN en eindigt dan met exitcode 2. Een fixture kan nooit RELEASED opleveren.

Iedere nieuwe native authority vereist bron-SHA, commit, schema, tests, echt runtimebewijs en referentiemodel op dezelfde bronversie. Geen engineeringbesluit wordt uit een tekstprompt of GPT-actor afgeleid. `force=true` bestaat niet.
