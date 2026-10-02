[CmdletBinding()]
param([string]$TeklaApiVersion = '2024.0.0', [switch]$Smoke, [switch]$Installer)
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
  # Exercise the same per-user PowerShell installer shipped in the package.
  $PackageScripts = Join-Path $Output 'scripts'
  New-Item -ItemType Directory -Force -Path $PackageScripts | Out-Null
  Copy-Item (Join-Path $PSScriptRoot 'Install-CWS-Bridge.ps1') $PackageScripts
  Copy-Item (Join-Path $PSScriptRoot 'Install.cmd') $PackageScripts
  $PackageFiles = @(Get-ChildItem $Output -File -Recurse | Where-Object { $_.Name -ne 'PACKAGE_MANIFEST.json' } | ForEach-Object {
    @{path=[IO.Path]::GetRelativePath($Output, $_.FullName).Replace('\','/');sha256=(Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
  })
  @{source_commit=$Commit;files=$PackageFiles;production_release=$false} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $Output 'PACKAGE_MANIFEST.json') -Encoding UTF8
  if ($Smoke) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PackageScripts 'Install-CWS-Bridge.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'Per-user installer smoke failed.' }
    $InstalledExe = Join-Path $env:LOCALAPPDATA ("CWS\TeklaBridge\versions\" + $Commit + "\Cws.TeklaBridge.exe")
    if (-not (Test-Path $InstalledExe)) { throw 'Installed executable missing.' }
    $ExpectedHash = (Get-FileHash (Join-Path $Output 'windows/Cws.TeklaBridge.exe') -Algorithm SHA256).Hash
    if ((Get-FileHash $InstalledExe -Algorithm SHA256).Hash -ne $ExpectedHash) { throw 'Installed executable differs from the tested build.' }
    $ShortcutPath = Join-Path ([Environment]::GetFolderPath('Desktop')) 'CWS Tekla Bridge.lnk'
    $Shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($ShortcutPath)
    if ($Shortcut.TargetPath -ne $InstalledExe) { throw 'Installed shortcut does not target the frozen build.' }
    @{schema_version='1.0';commit=$Commit;status='PASS_PER_USER_SCRIPT_INSTALL';windows=$true;exe_sha256=$ExpectedHash.ToLowerInvariant();active_tekla='NOT_RUN';production_release=$false} | ConvertTo-Json | Set-Content (Join-Path $Output 'installer-smoke.json') -Encoding UTF8
  }

  if ($Installer) {
    & (Join-Path $PSScriptRoot 'installer/build-installer.ps1') -SourceCommit $Commit -Smoke:$Smoke
  }
} finally { Pop-Location }
