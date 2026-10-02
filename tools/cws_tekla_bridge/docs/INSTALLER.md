# CWS Tekla Bridge Windows-installer

De installerbuild levert `installer/CWS_Tekla_Bridge_v0.1_Setup.exe`. Start dit bestand op Windows 10 of hoger, x64, met .NET Framework 4.8 of een compatibele nieuwere versie. De Nederlandstalige wizard controleert deze vereisten en installeert voor de huidige gebruiker, zonder beheerdersrechten. Tekla hoeft niet actief te zijn om de disconnected app te installeren of te starten.

De programmabestanden worden standaard opgeslagen onder `%LOCALAPPDATA%\Programs\CWS\TeklaBridge`. Het startmenu krijgt **CWS Tekla Bridge**; de wizard biedt een bureaubladsnelkoppeling. Verwijderen kan via Windows **Geïnstalleerde apps**. Instellingen, journal en reviewgegevens onder `%LOCALAPPDATA%\CWS\TeklaBridge` blijven behouden. De installer past geen Tekla-macro's, modellen of native authority aan.

Dit blijft de bestaande v0.1-testbuild. De app start disconnected; native writes, save/reopen, verbindingen-AUTO en productie worden niet door installeren goedgekeurd. De compilerreferentie is Tekla Open API 2024.0.0. De daadwerkelijk geïnstalleerde Tekla-versie wordt pas gecontroleerd wanneer de gebruiker een echte verbinding configureert.

## Bouwen

Gebruik een volledige checkout van `CoenWessselink/Convertor`, branch `feature/cws-tekla-bridge-v0.1`, met een schone bronversie. Vereist zijn PowerShell 7, .NET SDK 8.0.413, de vastgelegde NuGet-dependencies en een geïnstalleerde Inno Setup 6-compiler (`ISCC.exe`). De Windows-CI gebruikt de compiler van het Windows-runnerimage en registreert zijn daadwerkelijke versie en SHA-256.

`pwsh -File tools/cws_tekla_bridge/scripts/build.ps1 -Smoke -Installer`

De build controleert de broncommit van de app, compileert de installer en test de geproduceerde EXE op Windows: installatie, iedere geïnstalleerde payloadhash, snelkoppelingen, daadwerkelijke start van de geïnstalleerde app, herinstallatie en verwijderen. Een afzonderlijke sentinelcontrole verifieert dat gebruikersgegevens behouden blijven. De test gebruikt een eigen tijdelijke installatiemap; het native Tekla-runtimebewijs blijft `NOT_RUN`.

De installer bevat een broncommit en een manifest van de ingesloten programmabestanden. De compiler- en lifecycle-rapporten vermelden de installerhash, zodat het geleverde installatieprogramma rechtstreeks aan de geteste versie is gekoppeld. Deze hashes zijn integriteitsbewijzen; digitale ondertekening wordt afzonderlijk gerapporteerd en wordt niet uit een succesvolle build afgeleid.
