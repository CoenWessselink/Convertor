# Codex Windows release-runbook

Dit document is het uitvoercontract voor CWS Convertor `0.10.19-beta-dev`.
Een release is alleen geslaagd wanneer `release/CODEX_RELEASE_MANIFEST.json`
`"status": "passed"` bevat. Een losse EXE, ZIP of screenshot is geen releasebewijs.

## Snelste route: GitHub Actions

1. Push de exacte broncommit naar `agent/cws-bom-production-hub-v1` of start
   workflow **Build SteelConverter Windows installer and portable package**
   handmatig op die commit.
2. Wacht tot job `build-windows-x64` groen is.
3. Download artifact
   `CWS_Convertor_0.10.19-beta-dev_Windows_x64`.
4. Pak het artifact uit en voer in PowerShell uit:

   ```powershell
   Get-Content .\SHA256SUMS.txt | ForEach-Object {
     $hash, $path = $_ -split '  ', 2
     if ((Get-FileHash -Algorithm SHA256 $path).Hash.ToLowerInvariant() -ne $hash) {
       throw "Checksum wijkt af: $path"
     }
   }
   (Get-Content .\CODEX_RELEASE_MANIFEST.json -Raw | ConvertFrom-Json).status
   ```

De laatste regel moet `passed` tonen. De workflow stopt direct bij ontbrekende
evidence, een foutieve versie, een andere commit, een dirty productbron of een
runtime die externe Python gebruikt.

## Lokale Windows-build

Vereisten op de buildcomputer:

- Windows x64;
- Git;
- Python Launcher met CPython 3.12 x64;
- Inno Setup 6;
- een schone checkout van de te publiceren commit.

Start vanuit de repository-root:

```bat
build_windows_exe.bat
```

Het script maakt zelf `.venv-build`, installeert de exact gelockte dependencies
en voert dezelfde eindgate uit als CI. De eindgebruiker heeft geen Python nodig.

## Verplichte testmatrix

| Laag | Verplichte controle |
| --- | --- |
| Bron | compileall, volledige smoke-suite, CLI-contracten, native selftest en echte Qt GUI-smoke |
| Fase 1 | reproduceerbare 5.000-objecten-IFC, alle uniforme brongates |
| Fase 2 | alle 16 uniforme integratiegates |
| Fase 3 | volledige regression en minimaal 600 seconden soak |
| BOM | echte `BomWorkspacePanel`, HVPC-project, vijf PNG-captures met SHA-256 |
| Dist | PyInstaller onedir, native inventory, GUI/CLI/conversie/project-roundtrip zonder externe Python |
| Portable | schoon uitgepakte ZIP, volledige packaged-runtime-smoke zonder externe Python |
| Installer | stille per-user-installatie, volledige packaged-runtime-smoke, zes associaties en PDF-contextactie |
| Uninstall | GUI/CLI verwijderd, CWS-extensiewaarden weg of vorig systeemdefault hersteld, eigen ProgID/PDF-contextsleutels verwijderd |
| Overdracht | installer, portable, bron-ZIP, Git-bundle, CycloneDX-SBOM, manifest en recursieve checksums |

## Opleverbestanden

Voor commit `<sha7>` bevat `release/` minimaal:

- `CWS_Convertor_Setup_0.10.19-beta-dev_<sha7>_x64.exe`;
- `CWS_Convertor_Portable_0.10.19-beta-dev_<sha7>_x64.zip`;
- `CWS_Convertor_Source_0.10.19-beta-dev_<sha7>.zip`;
- `CWS_Convertor_0.10.19-beta-dev_<sha7>.bundle`;
- `CWS_Convertor_SBOM_0.10.19-beta-dev_<sha7>.cdx.json`;
- `CODEX_RELEASE_MANIFEST.json` en `SHA256SUMS.txt`;
- `BOM_EVIDENCE/` met vijf werkelijke GUI-afbeeldingen en capturemanifest;
- `TEST_EVIDENCE/` met fase- en soakrapporten;
- de runtime-JSON-rapporten en `WINDOWS_RUNTIME_VALIDATION.md`.

## Bewuste veiligheidsgrens

De build bewijst software-, package-, installatie- en uninstallgedrag op de
Windows-runner. Hij beweert niet dat een fysieke machine door CWS is gezien of
dat overdracht naar een machine is toegestaan. `CODEX_RELEASE_MANIFEST.json`
houdt deze velden daarom expliciet op `false`. Projectspecifieke
`production_ready=false` uit de BOM-validatie wordt eveneens niet overschreven.
