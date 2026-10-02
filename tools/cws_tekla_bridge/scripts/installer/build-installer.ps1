[CmdletBinding()]
param(
  [string]$IsccPath,
  [string]$WindowsArtifactsRoot,
  [string]$OutputRoot,
  [string]$SourceCommit,
  [switch]$Smoke
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Inno Setup compilation requires Windows.' }
$BridgeRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not $WindowsArtifactsRoot) { $WindowsArtifactsRoot = Join-Path $BridgeRoot 'artifacts\windows' }
if (-not $OutputRoot) { $OutputRoot = Join-Path $BridgeRoot 'artifacts\installer' }
$WindowsArtifactsRoot = [IO.Path]::GetFullPath($WindowsArtifactsRoot).TrimEnd('\')
$OutputRoot = [IO.Path]::GetFullPath($OutputRoot)
$RepoRoot = (git -C $BridgeRoot rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0) { throw 'A source repository is required.' }
$Branch = (git -C $RepoRoot branch --show-current).Trim()
if ($Branch -cne 'feature/cws-tekla-bridge-v0.1') { throw "Wrong source branch: $Branch" }
$Head = (git -C $RepoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $Head -notmatch '^[0-9a-f]{40}$') { throw 'A frozen Git source commit is required.' }
if (-not $SourceCommit) { $SourceCommit = $Head }
if ($SourceCommit -cne $Head) { throw 'Installer SourceCommit differs from repository HEAD.' }
if (git -C $RepoRoot status --porcelain -- tools/cws_tekla_bridge) { throw 'Commit bridge source before building installer evidence.' }
$BuildEvidencePath = Join-Path (Split-Path $WindowsArtifactsRoot -Parent) 'build-evidence.json'
if (-not (Test-Path -LiteralPath $BuildEvidencePath -PathType Leaf)) { throw 'Commit-bound Windows build evidence is missing.' }
$BuildEvidence = Get-Content -LiteralPath $BuildEvidencePath -Raw | ConvertFrom-Json
if ($BuildEvidence.commit -cne $SourceCommit -or $BuildEvidence.windows_compile -ne 'PASS' -or $BuildEvidence.production_release -ne $false) { throw 'Windows build evidence is stale, unverified or unexpectedly claims production release.' }
$AppExe = Join-Path $WindowsArtifactsRoot 'Cws.TeklaBridge.exe'
$Required = @('Cws.TeklaBridge.exe','Cws.TeklaBridge.exe.config','Cws.TeklaBridge.Core.dll','Cws.TeklaBridge.Native.dll','Newtonsoft.Json.dll','Tekla.Structures.dll','Tekla.Structures.Model.dll','Tekla.Structures.Catalogs.dll','Tekla.Structures.Datatype.dll','schemas\authorization-matrix.json','schemas\authority-manifest.json')
foreach ($Path in $Required) { if (-not (Test-Path -LiteralPath (Join-Path $WindowsArtifactsRoot $Path) -PathType Leaf)) { throw "Windows payload file missing: $Path" } }
$AppVersion = [Diagnostics.FileVersionInfo]::GetVersionInfo($AppExe).ProductVersion
if (-not $AppVersion -or -not $AppVersion.Contains($SourceCommit)) { throw 'Windows app version does not contain the frozen source commit.' }
function Write-Json([string]$Path, $Value) { [IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth 12), (New-Object Text.UTF8Encoding($false))) }
function Get-PayloadFiles {
  if (((Get-Item -LiteralPath $WindowsArtifactsRoot).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse-point payload root is not allowed.' }
  foreach ($Directory in @(Get-ChildItem -LiteralPath $WindowsArtifactsRoot -Directory -Recurse -Force)) {
    if (($Directory.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse-point payload directories are not allowed.' }
  }
  @(Get-ChildItem -LiteralPath $WindowsArtifactsRoot -File -Recurse -Force | Sort-Object FullName | ForEach-Object {
    if (($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse-point payload files are not allowed.' }
    [ordered]@{path=$_.FullName.Substring($WindowsArtifactsRoot.Length + 1).Replace('\','/'); sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant(); bytes=$_.Length}
  })
}
if (-not $IsccPath) {
  $CompilerCommand = Get-Command 'ISCC.exe' -ErrorAction SilentlyContinue
  if ($CompilerCommand) { $IsccPath = $CompilerCommand.Source }
  if (-not $IsccPath) {
    $CompilerCandidates = @()
    foreach ($Base in @(${env:ProgramFiles(x86)}, $env:ProgramFiles)) {
      if ($Base) { $CompilerCandidates += Join-Path $Base 'Inno Setup 6\ISCC.exe'; $CompilerCandidates += Join-Path $Base 'Inno Setup 7\ISCC.exe' }
    }
    $IsccPath = $CompilerCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
  }
}
if (-not $IsccPath -or -not (Test-Path -LiteralPath $IsccPath -PathType Leaf)) { throw 'ISCC.exe is not installed. Install Inno Setup from jrsoftware.org or pass its verified compiler path with -IsccPath.' }
$IsccPath = [IO.Path]::GetFullPath($IsccPath)
$CompilerInfo = [Diagnostics.FileVersionInfo]::GetVersionInfo($IsccPath)
if ($CompilerInfo.ProductName -notlike '*Inno Setup*' -or $CompilerInfo.FileDescription -notlike '*Compiler*' -or [version]($CompilerInfo.FileMajorPart.ToString()+'.'+$CompilerInfo.FileMinorPart+'.'+$CompilerInfo.FileBuildPart) -lt [version]'6.3.0') { throw 'Selected compiler is not a supported Inno Setup command-line compiler (6.3+).' }
$CompilerSignature = Get-AuthenticodeSignature -LiteralPath $IsccPath
if ($CompilerSignature.Status -notin @('Valid','NotSigned')) { throw "Compiler Authenticode validation failed: $($CompilerSignature.Status)" }
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$Files = Get-PayloadFiles
$TestedManifestPath = Join-Path (Split-Path $WindowsArtifactsRoot -Parent) 'PACKAGE_MANIFEST.json'
if (-not (Test-Path -LiteralPath $TestedManifestPath -PathType Leaf)) { throw 'The tested artifact PACKAGE_MANIFEST.json is missing.' }
$TestedManifest = Get-Content -LiteralPath $TestedManifestPath -Raw | ConvertFrom-Json
if ($TestedManifest.source_commit -cne $SourceCommit -or $TestedManifest.production_release -ne $false) { throw 'The tested artifact manifest has a stale commit or production claim.' }
$TestedWindowsFiles = @($TestedManifest.files | Where-Object { $_.path.StartsWith('windows/', [StringComparison]::Ordinal) })
if ($TestedWindowsFiles.Count -ne $Files.Count) { throw 'The Windows payload file set differs from the tested artifact manifest.' }
$TestedByPath = @{}
foreach ($File in $TestedWindowsFiles) {
  $Relative = $File.path.Substring(8)
  if ($Relative -match '(^/|(^|/)\.\.(/|$)|:|\\)' -or $TestedByPath.ContainsKey($Relative) -or $File.sha256 -notmatch '^[0-9a-f]{64}$') { throw 'The tested Windows artifact manifest contains unsafe or duplicate paths/hashes.' }
  $TestedByPath[$Relative] = $File.sha256
}
foreach ($File in $Files) {
  if (-not $TestedByPath.ContainsKey($File.path) -or $TestedByPath[$File.path] -cne $File.sha256) { throw "Windows file does not match its tested artifact hash: $($File.path)" }
}
$ManifestPath = Join-Path $OutputRoot 'INSTALLER_PAYLOAD_MANIFEST.json'
$Manifest = @{schema_version='1.0';source_commit=$SourceCommit;app_version=$AppVersion;platform='WINDOWS_X64';installation_scope='CURRENT_USER';production_release=$false;active_tekla='NOT_RUN';native_write_authority='BLOCKED';files=$Files}
Write-Json $ManifestPath $Manifest
$InstallerPath = Join-Path $OutputRoot 'CWS_Tekla_Bridge_v0.1_Setup.exe'
if (Test-Path -LiteralPath $InstallerPath) { Remove-Item -LiteralPath $InstallerPath -Force }
$Arguments = @('/Qp', "/DPayloadDir=$WindowsArtifactsRoot", "/DOutputDir=$OutputRoot", "/DManifestFile=$ManifestPath", "/DSourceCommit=$SourceCommit", (Join-Path $PSScriptRoot 'CWS-Tekla-Bridge.iss'))
& $IsccPath @Arguments
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $InstallerPath -PathType Leaf)) { throw 'Inno Setup compilation failed.' }
$AfterFiles = Get-PayloadFiles
if (($Files | ConvertTo-Json -Depth 5 -Compress) -cne ($AfterFiles | ConvertTo-Json -Depth 5 -Compress)) { throw 'Windows payload changed during installer compilation.' }
$SetupSignature = Get-AuthenticodeSignature -LiteralPath $InstallerPath
$InstallerEvidence = @{schema_version='1.0';source_commit=$SourceCommit;status='PASS_INSTALLER_COMPILE';installer_file='CWS_Tekla_Bridge_v0.1_Setup.exe';installer_sha256=(Get-FileHash -LiteralPath $InstallerPath -Algorithm SHA256).Hash.ToLowerInvariant();tested_artifact_manifest_sha256=(Get-FileHash -LiteralPath $TestedManifestPath -Algorithm SHA256).Hash.ToLowerInvariant();payload_manifest_sha256=(Get-FileHash -LiteralPath $ManifestPath -Algorithm SHA256).Hash.ToLowerInvariant();compiler=@{path=$IsccPath;product=$CompilerInfo.ProductName;version=$CompilerInfo.ProductVersion;sha256=(Get-FileHash -LiteralPath $IsccPath -Algorithm SHA256).Hash.ToLowerInvariant();authenticode=$CompilerSignature.Status.ToString()};setup_authenticode=$SetupSignature.Status.ToString();install_scope='PER_USER_NO_ELEVATION_REQUEST';windows_install_smoke='NOT_RUN';active_tekla='NOT_RUN';production_release=$false}
Write-Json (Join-Path $OutputRoot 'installer-build-evidence.json') $InstallerEvidence
if ($Smoke) {
  & (Join-Path $PSScriptRoot 'smoke-installer.ps1') -InstallerPath $InstallerPath -ManifestPath $ManifestPath -EvidenceRoot (Join-Path $OutputRoot 'installer-smoke')
  $InstallerEvidence.windows_install_smoke = 'PASS'
  Write-Json (Join-Path $OutputRoot 'installer-build-evidence.json') $InstallerEvidence
}
Write-Output "Installer: $InstallerPath"
