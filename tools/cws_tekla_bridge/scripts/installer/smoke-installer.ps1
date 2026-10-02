[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$InstallerPath,
  [Parameter(Mandatory=$true)][string]$ManifestPath,
  [Parameter(Mandatory=$true)][string]$EvidenceRoot
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or -not [Environment]::Is64BitProcess) { throw 'Installer smoke requires Windows x64 PowerShell.' }
$InstallerPath = [IO.Path]::GetFullPath($InstallerPath)
$EvidenceRoot = [IO.Path]::GetFullPath($EvidenceRoot)
$Manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
$RegistryPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\CWS.TeklaBridge_is1'
if (Test-Path $RegistryPath) { throw 'An existing wizard-installed bridge is registered. Smoke refuses to replace a real installation.' }
if (Get-Process -Name 'Cws.TeklaBridge' -ErrorAction SilentlyContinue) { throw 'Close the bridge before running an isolated installer smoke.' }
$Id = [Guid]::NewGuid().ToString('N')
$TempRoot = Join-Path ([IO.Path]::GetTempPath()) ('CWS-Installer-Smoke-' + $Id)
$InstallDir = Join-Path $TempRoot 'Installed App'
# DisableProgramGroupPage fixes the installed Start Menu group to this name;
# Inno ignores /GROUP in that mode. Test the actual shipped default.
$GroupName = 'CWS Tekla Bridge'
$GroupDir = Join-Path ([Environment]::GetFolderPath('Programs')) $GroupName
$ShortcutPath = Join-Path $GroupDir 'CWS Tekla Bridge.lnk'
if (Test-Path -LiteralPath $GroupDir) { throw 'An existing bridge Start Menu group exists. Smoke refuses to replace it.' }
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'CWS Tekla Bridge.lnk'
$DataRoot = Join-Path $env:LOCALAPPDATA 'CWS\TeklaBridge'
$OwnedFiles = New-Object 'Collections.Generic.List[string]'
$OwnedDirs = New-Object 'Collections.Generic.List[string]'
$Report = @{schema_version='1.0';source_commit=$Manifest.source_commit;status='FAILED';installation_scope='PER_USER_NO_ELEVATION_REQUEST';standard_user_token='NOT_PROVEN';desktop_shortcut='NOT_REQUESTED';active_tekla='NOT_RUN';production_release=$false}
New-Item -ItemType Directory -Force -Path $EvidenceRoot,$TempRoot | Out-Null
function Write-Json([string]$Path, $Value) { [IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth 12), (New-Object Text.UTF8Encoding($false))) }
function Run-Checked([string]$Exe, [string[]]$Arguments) {
  $Process = Start-Process -FilePath $Exe -ArgumentList $Arguments -PassThru
  if (-not $Process.WaitForExit(60000)) { $Process.Kill(); throw "Process timed out: $([IO.Path]::GetFileName($Exe))" }
  $Process.Refresh()
  if ($Process.ExitCode -ne 0) { throw "Process failed: $([IO.Path]::GetFileName($Exe)) exit $($Process.ExitCode)" }
}
function Snapshot-Data {
  @(Get-ChildItem -LiteralPath $DataRoot -File -Recurse | Sort-Object FullName | ForEach-Object {
    [ordered]@{path=$_.FullName.Substring($DataRoot.Length+1).Replace('\','/');sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
  })
}
function Assert-DataPreserved($Before) {
  $After = Snapshot-Data
  if (($Before | ConvertTo-Json -Depth 5 -Compress) -cne ($After | ConvertTo-Json -Depth 5 -Compress)) { throw 'Shared settings/journal/review data changed during installer smoke.' }
}
function Assert-Payload {
  foreach ($File in $Manifest.files) {
    if ($File.path -match '(^/|(^|/)\.\.(/|$)|:|\\)') { throw 'Unsafe payload manifest path.' }
    $Path = Join-Path $InstallDir $File.path.Replace('/','\')
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf) -or (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $File.sha256) { throw "Installed file differs from frozen build: $($File.path)" }
  }
  if ((Get-FileHash -LiteralPath (Join-Path $InstallDir 'INSTALLER_PAYLOAD_MANIFEST.json') -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $ManifestPath -Algorithm SHA256).Hash) { throw 'Installed payload manifest is different.' }
  if (-not (Test-Path -LiteralPath $ShortcutPath -PathType Leaf)) { throw 'Per-user Start Menu shortcut missing.' }
  $Shell = New-Object -ComObject WScript.Shell
  $Shortcut = $Shell.CreateShortcut($ShortcutPath)
  if ($Shortcut.TargetPath -ine (Join-Path $InstallDir 'Cws.TeklaBridge.exe') -or $Shortcut.WorkingDirectory -ine $InstallDir) { throw 'Start Menu shortcut targets wrong executable or working directory.' }
}
$DesktopBefore = if (Test-Path -LiteralPath $DesktopShortcut) { (Get-FileHash -LiteralPath $DesktopShortcut -Algorithm SHA256).Hash } else { $null }
try {
  foreach ($Dir in @($DataRoot, (Join-Path $DataRoot 'journal'), (Join-Path $DataRoot 'review'))) {
    if (-not (Test-Path -LiteralPath $Dir)) { New-Item -ItemType Directory -Path $Dir -Force | Out-Null; $OwnedDirs.Add($Dir) }
  }
  $SettingsPath = Join-Path $DataRoot 'settings.json'
  if (-not (Test-Path -LiteralPath $SettingsPath)) {
    Write-Json $SettingsPath @{ExpectedTeklaVersion='';LastCanonicalPath='';Mode='CHECK_ONLY'}
    $OwnedFiles.Add($SettingsPath)
  }
  foreach ($Dir in @((Join-Path $DataRoot 'journal'), (Join-Path $DataRoot 'review'))) {
    $Sentinel = Join-Path $Dir ('installer-smoke-' + $Id + '.proof.json')
    Write-Json $Sentinel @{purpose='installer data retention proof';id=$Id}; $OwnedFiles.Add($Sentinel)
  }
  $Before = Snapshot-Data
  $InstallerArguments = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',('/DIR="'+$InstallDir+'"'),('/GROUP="'+$GroupName+'"'),'/TASKS=""',('/LOG="'+(Join-Path $EvidenceRoot 'install.log')+'"'))
  Run-Checked $InstallerPath $InstallerArguments
  Assert-Payload; Assert-DataPreserved $Before
  $UiEvidence = Join-Path $EvidenceRoot 'installed-ui'
  Run-Checked (Join-Path $InstallDir 'Cws.TeklaBridge.exe') @('--smoke', ('"'+$UiEvidence+'"'))
  $Startup = Get-Content -LiteralPath (Join-Path $UiEvidence 'windows-startup.json') -Raw | ConvertFrom-Json
  if ($Startup.Status -ne 'PASS_DISCONNECTED_UI_ONLY' -or $Startup.Fixture -ne $false -or $Startup.X64 -ne $true -or -not $Startup.SourceVersion.Contains($Manifest.source_commit)) { throw 'Installed real UI smoke failed or does not match source commit.' }
  if (-not (Test-Path -LiteralPath (Join-Path $UiEvidence 'Windows_Bridge_DISCONNECTED.png'))) { throw 'Actual installed UI screenshot is missing.' }
  Assert-DataPreserved $Before
  $InstallerArguments[-1] = '/LOG="'+(Join-Path $EvidenceRoot 'reinstall.log')+'"'
  Run-Checked $InstallerPath $InstallerArguments
  Assert-Payload; Assert-DataPreserved $Before
  Run-Checked (Join-Path $InstallDir 'unins000.exe') @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="'+(Join-Path $EvidenceRoot 'uninstall.log')+'"'))
  Assert-DataPreserved $Before
  foreach ($File in $Manifest.files) { if (Test-Path -LiteralPath (Join-Path $InstallDir $File.path.Replace('/','\'))) { throw "Uninstall retained an installed app payload file: $($File.path)" } }
  if (Test-Path -LiteralPath $ShortcutPath) { throw 'Uninstall retained Start Menu shortcut.' }
  if (Test-Path $RegistryPath) { throw 'Uninstall retained bridge registration.' }
  $DesktopAfter = if (Test-Path -LiteralPath $DesktopShortcut) { (Get-FileHash -LiteralPath $DesktopShortcut -Algorithm SHA256).Hash } else { $null }
  if ($DesktopAfter -cne $DesktopBefore) { throw 'Unselected desktop shortcut was unexpectedly changed.' }
  $Report.status = 'PASS_INSTALL_REINSTALL_UNINSTALL'
  $Report.payload_files_verified = @($Manifest.files).Count
  $Report.settings_journal_review_files_preserved = @($Before).Count
  $Report.settings_journal_review_hashes = $Before
  $Report.installed_ui = 'PASS_DISCONNECTED_UI_ONLY'
  $Report.installer_sha256 = (Get-FileHash -LiteralPath $InstallerPath -Algorithm SHA256).Hash.ToLowerInvariant()
  $Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $Principal = New-Object Security.Principal.WindowsPrincipal($Identity)
  $Report.runner_admin_token = $Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  if (-not $Report.runner_admin_token) { $Report.standard_user_token = 'PASS_CURRENT_NONADMIN_TOKEN' }
}
catch { $Report.error = $_.Exception.ToString(); throw }
finally {
  Write-Json (Join-Path $EvidenceRoot 'installer-smoke.json') $Report
  # Clean only this smoke's app registration and files, never user application data.
  $Uninstaller = Join-Path $InstallDir 'unins000.exe'
  if (Test-Path -LiteralPath $Uninstaller) {
    try { Run-Checked $Uninstaller @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') } catch { Write-Warning 'Smoke cleanup uninstall failed; see evidence.' }
  }
  foreach ($File in $OwnedFiles) { if (Test-Path -LiteralPath $File) { Remove-Item -LiteralPath $File -Force } }
  for ($Index=$OwnedDirs.Count-1; $Index -ge 0; $Index--) {
    $Dir = $OwnedDirs[$Index]
    if ((Test-Path -LiteralPath $Dir) -and -not @(Get-ChildItem -LiteralPath $Dir -Force).Count) { Remove-Item -LiteralPath $Dir }
  }
  if (Test-Path -LiteralPath $TempRoot) { Remove-Item -LiteralPath $TempRoot -Recurse -Force }
}
Write-Output 'PASS: install, file hashes, Start Menu shortcut, actual installed UI, reinstall, uninstall and shared data retention.'
