[CmdletBinding()]
param([string]$TeklaApiVersion = '2024.0.0', [switch]$Smoke)
$ErrorActionPreference = 'Stop'
$BridgeRoot = Split-Path $PSScriptRoot -Parent
Push-Location $BridgeRoot
try {
  $RepoRoot = (git rev-parse --show-toplevel).Trim()
  if ($LASTEXITCODE -ne 0) { throw 'Build must run in the frozen source repository.' }
  $Branch = (git branch --show-current).Trim()
  if ($Branch -ne 'feature/cws-tekla-bridge-v0.1') { throw "Wrong branch: $Branch" }
  $Commit = (git rev-parse HEAD).Trim()
  $Dirty = git -C $RepoRoot status --porcelain -- tools/cws_tekla_bridge
  if ($Dirty) { throw 'Bridge source is dirty. Commit before building evidence.' }
  $Output = Join-Path $BridgeRoot 'artifacts'
  New-Item -ItemType Directory -Force -Path $Output | Out-Null
  dotnet restore src/Windows/Windows.csproj -p:TeklaApiVersion=$TeklaApiVersion --locked-mode
  if ($LASTEXITCODE -ne 0) { throw 'Windows dependency restore failed.' }
  dotnet restore tests/Tests.csproj --locked-mode
  if ($LASTEXITCODE -ne 0) { throw 'Core dependency restore failed.' }
  dotnet build src/Windows/Windows.csproj --no-restore -c Release -p:SourceCommit=$Commit -p:TeklaApiVersion=$TeklaApiVersion -o (Join-Path $Output 'windows')
  if ($LASTEXITCODE -ne 0) { throw 'Windows build failed.' }
  dotnet build tests/Tests.csproj --no-restore -c Release -p:SourceCommit=$Commit -o (Join-Path $Output 'tests')
  if ($LASTEXITCODE -ne 0) { throw 'Core test build failed.' }
  dotnet exec (Join-Path $Output 'tests/Cws.TeklaBridge.Tests.dll') (Join-Path $Output 'core-tests.json')
  if ($LASTEXITCODE -ne 0) { throw 'Core tests failed.' }
  if ($Smoke) {
    $Exe = Join-Path $Output 'windows/Cws.TeklaBridge.exe'
    $Evidence = Join-Path $Output 'windows-smoke'
    $Process = Start-Process -FilePath $Exe -ArgumentList @('--smoke', "`"$Evidence`"") -PassThru
    if (-not $Process.WaitForExit(60000)) { $Process.Kill(); throw 'Windows startup smoke timed out.' }
    if ($Process.ExitCode -ne 0) { throw 'Windows startup smoke failed.' }
    if (-not (Test-Path (Join-Path $Evidence 'windows-startup.json'))) { throw 'Windows startup evidence missing.' }
  }
  @{schema_version='1.0';commit=$Commit;branch=$Branch;tekla_compile_reference=$TeklaApiVersion;windows_compile='PASS';windows_smoke=$(if($Smoke){'PASS'}else{'NOT_RUN'});active_tekla='NOT_RUN';save_reopen_readback='NOT_RUN';production_release=$false} | ConvertTo-Json | Set-Content (Join-Path $Output 'build-evidence.json') -Encoding UTF8
} finally { Pop-Location }
