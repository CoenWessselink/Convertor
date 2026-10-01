[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT' -or -not [Environment]::Is64BitOperatingSystem) { throw 'Windows x64 is required.' }
$PackageRoot = Split-Path $PSScriptRoot -Parent
$Manifest = Get-Content (Join-Path $PackageRoot 'PACKAGE_MANIFEST.json') -Raw | ConvertFrom-Json
if ($Manifest.source_commit -notmatch '^[0-9a-f]{40}$') { throw 'A commit-bound package is required.' }
$Boundary = [IO.Path]::GetFullPath($PackageRoot).TrimEnd('\') + '\'
foreach ($Item in $Manifest.files) {
  $Path = [IO.Path]::GetFullPath((Join-Path $PackageRoot $Item.path))
  if (-not $Path.StartsWith($Boundary, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid package path.' }
  if ((Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant() -ne $Item.sha256) { throw "Package changed: $($Item.path)" }
}
$Destination = Join-Path $env:LOCALAPPDATA ("CWS\TeklaBridge\versions\" + $Manifest.source_commit)
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
Copy-Item -Path (Join-Path $PackageRoot 'windows/*') -Destination $Destination -Recurse -Force
$Exe = Join-Path $Destination 'Cws.TeklaBridge.exe'
if (-not (Test-Path $Exe)) { throw 'Compiled Windows app is missing.' }
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'CWS Tekla Bridge.lnk'))
$Shortcut.TargetPath = $Exe
$Shortcut.WorkingDirectory = $Destination
$Shortcut.Description = 'CWS Tekla Bridge v0.1 - testbuild; Tekla runtime gates pending'
$Shortcut.Save()
Write-Host "Installed testbuild $($Manifest.source_commit)."
Write-Host 'Start CWS Tekla Bridge from the desktop. Tekla connection and release gates are shown in the app.'
