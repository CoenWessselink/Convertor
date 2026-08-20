[CmdletBinding()]
param(
    [string]$RepositoryRoot = 'C:\CONVERTOR',
    [string]$PackageBase = 'C:\CONVERTOR\CWS_CONVERTOR_COMPLETE_HANDOVER_0.10.3_V2'
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Get-UniquePath {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $Path }
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    return "${Path}_$stamp"
}

function New-PackageDirectory {
    param([Parameter(Mandatory)][string]$RelativePath)
    $path = Join-Path $script:PackageRoot $RelativePath
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    return $path
}

$script:PackageRoot = Get-UniquePath -Path $PackageBase
$archivePath = Get-UniquePath -Path ($script:PackageRoot + '.zip')

$directories = @(
    '00_START_HERE', '01_SOURCE', '02_RELEASE', '03_FROZEN_DONORS',
    '04_REFERENCE_IMAGES\DESIGN_REFERENCES', '04_REFERENCE_IMAGES\FIELD_REPORTS',
    '05_SAMPLE_FILES', '06_ORIGINAL_PROMPTS', '07_BIM_VISION',
    '08_TEST_EVIDENCE', '09_MANIFESTS'
)
foreach ($directory in $directories) { New-PackageDirectory -RelativePath $directory | Out-Null }

$missing = [System.Collections.Generic.List[string]]::new()

function Copy-HandoverFile {
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$DestinationDirectory,
        [string]$DestinationName
    )
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
        $script:missing.Add($Source)
        return
    }
    $targetName = if ($DestinationName) { $DestinationName } else { Split-Path -Leaf $Source }
    $target = Join-Path (Join-Path $script:PackageRoot $DestinationDirectory) $targetName
    Copy-Item -LiteralPath $Source -Destination $target -Force
}

$handoverDocs = @(
    'CODEX_STARTPROMPT_CWS_CONVERTOR_NEW_CHAT_V2.md',
    'CWS_CONVERTOR_COMPLETE_HANDOVER_V2.md',
    'CWS_CONVERTOR_REPOSITORIES_BRANCHES_V2.md',
    'CWS_CONVERTOR_ACCEPTANCE_STATUS_V2.md',
    'THIRD_PARTY_AND_ACCESS_BOUNDARIES_V2.md'
)
foreach ($doc in $handoverDocs) {
    Copy-HandoverFile -Source (Join-Path $RepositoryRoot "docs\handover\$doc") -DestinationDirectory '00_START_HERE'
}

$originalPromptFiles = @(
    'C:\Users\c.wesselink\Downloads\CODEX_STARTPROMPT_CWS_CONVERTOR_REINTEGRATION_V1.md',
    'C:\Users\c.wesselink\Downloads\CWS_CONVERTOR_REUSE_MATRIX_V1.csv',
    'C:\Users\c.wesselink\Downloads\CWS_CONVERTOR_REINTEGRATION_HANDOVER_V1.zip'
)
foreach ($file in $originalPromptFiles) { Copy-HandoverFile -Source $file -DestinationDirectory '06_ORIGINAL_PROMPTS' }
$masterPrompt = Get-ChildItem -LiteralPath 'C:\Converter' -File | Where-Object { $_.Name -like '# CWS CONVERTOR * MASTER SUPERPROMP_NIEUW.txt' } | Select-Object -First 1
if ($masterPrompt) {
    Copy-HandoverFile -Source $masterPrompt.FullName -DestinationDirectory '06_ORIGINAL_PROMPTS' -DestinationName 'CWS_CONVERTOR_MASTER_SUPERPROMPT_ORIGINAL.txt'
} else {
    $missing.Add('C:\Converter\# CWS CONVERTOR - MASTER SUPERPROMP_NIEUW.txt')
}

$donorFiles = @(
    'C:\Users\c.wesselink\Downloads\CWS_PROFILE_NESTING_COMPLETE_OVERDRACHT_0.8.12-beta-dev (1) (1).zip',
    'C:\Users\c.wesselink\Downloads\CWS_Convertor_Scribing_M18_DELIVERY_0.8.30-beta-dev(1).zip',
    'C:\Users\c.wesselink\Downloads\CWS_Viewer_V15_T8_diagnostics (1).zip',
    'C:\Users\c.wesselink\Desktop\CWS_Viewer_1.4.0-v15-preview.2_INSTALLER_x64.zip',
    'C:\Users\c.wesselink\Desktop\Trimble Connect.zip',
    'C:\Users\c.wesselink\AppData\Local\Temp\STP_files (1).zip'
)
foreach ($file in $donorFiles) { Copy-HandoverFile -Source $file -DestinationDirectory '03_FROZEN_DONORS' }

$sampleFiles = @(
    'C:\Users\c.wesselink\Desktop\Pr193.nc1',
    'C:\Users\c.wesselink\Desktop\Pr193_BOM.xlsx',
    'C:\Users\c.wesselink\Desktop\Pr193.step',
    'C:\Users\c.wesselink\Desktop\Pr1298.step',
    'C:\Users\c.wesselink\Desktop\Pr1301.step',
    'C:\Users\c.wesselink\Desktop\Pr1707.step',
    'C:\Users\c.wesselink\Desktop\P1793.step',
    'C:\Users\c.wesselink\Desktop\P1796.step',
    'C:\Users\c.wesselink\Desktop\Pr1293.step',
    'C:\Users\c.wesselink\Desktop\IFC_files\Powerspex te Oldenzaal_Fase 3 _3.ifc'
)
foreach ($file in $sampleFiles) { Copy-HandoverFile -Source $file -DestinationDirectory '05_SAMPLE_FILES' }

$designNames = @(
    'ChatGPT Image 19 aug 2026, 10_20_22.png', 'ChatGPT Image 19 aug 2026, 10_12_20.png',
    'ChatGPT Image 19 aug 2026, 08_50_54.png', 'ChatGPT Image 19 aug 2026, 09_47_56.png',
    'ChatGPT Image 19 aug 2026, 09_38_36.png', 'ChatGPT Image 19 aug 2026, 07_36_08.png',
    'ChatGPT Image 19 aug 2026, 10_40_44.png', 'ChatGPT Image 19 aug 2026, 10_39_44.png',
    'ChatGPT Image 19 aug 2026, 10_23_13.png', 'ChatGPT Image 19 aug 2026, 10_41_23.png',
    'CWS_Convertor_PartFirst_UI_PARITY_V2_CONTROL.png', 'CWS_Convertor_PartFirst_BUILD1_CONTROL.png'
)
foreach ($name in $designNames) {
    Copy-HandoverFile -Source (Join-Path 'C:\Users\c.wesselink\Downloads' $name) -DestinationDirectory '04_REFERENCE_IMAGES\DESIGN_REFERENCES'
}

$fieldReportNames = @(
    'codex-clipboard-f0703a55-359c-40b3-be2a-addd840db3a2.png',
    'codex-clipboard-1c53107b-1a75-40fd-a2e1-71244eaa7a15.png',
    'codex-clipboard-d046c3b9-00b5-400f-b343-1c2de95ea4d0.png',
    'codex-clipboard-d6b25ecb-7260-4f24-93b4-66030e8c19f7.png',
    'codex-clipboard-71c0228c-0f5f-40a2-b3fb-35184df1e4fc.png',
    'codex-clipboard-e2e22587-6b8f-4759-8e5d-b86264fdc60e.png',
    'codex-clipboard-14054cbb-8ebf-4454-b39b-c6cffd6e7450.png',
    'codex-clipboard-c89a2fe2-e631-41fb-b21a-f0ae62c3076a.png',
    'codex-clipboard-eb1a4a3a-5e1f-4621-a730-49ae7108d366.png',
    'codex-clipboard-8f0c29b5-fbcd-4fae-8493-b995dbe2f2ee.png',
    'codex-clipboard-c702bbe5-f476-48da-b6ed-76737ee4f4eb.png',
    'codex-clipboard-8bf202b1-45a3-4d79-9fba-e231ec0ff25b.png',
    'codex-clipboard-912a8b62-251b-42e9-b002-425c4023bd4d.png',
    'codex-clipboard-c2edd0c5-383e-4d71-872a-8cb5779cadb5.png',
    'codex-clipboard-5ff828c2-893a-449e-aa46-79b5effd5e64.png',
    'codex-clipboard-8324aa4e-d48f-4a5e-a9db-8da38a789296.png',
    'codex-clipboard-36858073-a456-492f-a0fa-b1e17d87ecd7.png',
    'codex-clipboard-9966c527-938e-481e-9415-8331b510b02f.png',
    'codex-clipboard-c4dc575b-e517-4ddd-a932-f9161ddea900.png',
    'codex-clipboard-af7bd389-c712-4f15-b4a5-dbfd2b79b7a7.png',
    'codex-clipboard-cc7aa2eb-f46e-4789-8ae3-ab0ab203a5a3.png',
    'codex-clipboard-c7dba8bb-32c2-49bc-9ef3-686766118d6d.png',
    'codex-clipboard-6afd18e7-da00-4b45-9d21-93ed1025eb35.png',
    'codex-clipboard-c1a53983-7db8-4613-8cd0-dfd468f5418e.png',
    'codex-clipboard-91b0da02-00b6-454c-b83c-ece3c11fbaa4.png'
)
foreach ($name in $fieldReportNames) {
    Copy-HandoverFile -Source (Join-Path 'C:\Users\c.wesselink\AppData\Local\Temp' $name) -DestinationDirectory '04_REFERENCE_IMAGES\FIELD_REPORTS'
}

Copy-HandoverFile -Source (Join-Path $RepositoryRoot 'CWS_Convertor_Portable_0.10.3-beta-dev_x64_verified.zip') -DestinationDirectory '02_RELEASE'
Copy-HandoverFile -Source (Join-Path $RepositoryRoot 'CWS_Convertor_Portable_0.10.3-beta-dev_x64_verified.zip.sha256') -DestinationDirectory '02_RELEASE'

$releaseEvidence = @(
    'release_manifest.json', 'release_verification_report.json',
    'test_evidence.json', 'verification_report.json', 'README.txt'
)
foreach ($name in $releaseEvidence) {
    $candidate = Join-Path $RepositoryRoot "release_0103_verified2\$name"
    if (Test-Path -LiteralPath $candidate) {
        Copy-HandoverFile -Source $candidate -DestinationDirectory '02_RELEASE'
        Copy-HandoverFile -Source $candidate -DestinationDirectory '08_TEST_EVIDENCE'
    }
}

$branch = (git -C $RepositoryRoot branch --show-current).Trim()
$commit = (git -C $RepositoryRoot rev-parse HEAD).Trim()
$remote = (git -C $RepositoryRoot remote get-url origin).Trim()
$snapshot = @"
PackageCreatedUtc=$((Get-Date).ToUniversalTime().ToString('o'))
Repository=$remote
Branch=$branch
Commit=$commit
BranchUrl=https://github.com/CoenWessselink/Convertor/tree/agent/cws-product-ui-reintegration-v1
ReleaseVersion=0.10.3-beta-dev
"@
Set-Content -LiteralPath (Join-Path $script:PackageRoot '09_MANIFESTS\BRANCH_SNAPSHOT.txt') -Value $snapshot -Encoding utf8

$sourceArchive = Join-Path $script:PackageRoot '01_SOURCE\CWS_Convertor_Source_agent-cws-product-ui-reintegration-v1.zip'
git -C $RepositoryRoot archive --format=zip --output=$sourceArchive HEAD
if ($LASTEXITCODE -ne 0) { throw 'git archive failed' }

$bimRoots = @('C:\ProgramData\BIM Vision', 'C:\Program Files (x86)\Datacomp\BIM Vision')
$bimInventory = foreach ($root in $bimRoots) {
    if (-not (Test-Path -LiteralPath $root -PathType Container)) {
        [pscustomobject]@{ Root=$root; RelativePath=''; Exists=$false; Length=0; LastWriteTimeUtc=$null; SHA256=$null; FileVersion=$null; ProductVersion=$null }
        continue
    }
    foreach ($file in Get-ChildItem -LiteralPath $root -File -Recurse -ErrorAction SilentlyContinue) {
        $version = $file.VersionInfo
        [pscustomobject]@{
            Root = $root
            RelativePath = $file.FullName.Substring($root.Length).TrimStart('\')
            Exists = $true
            Length = $file.Length
            LastWriteTimeUtc = $file.LastWriteTimeUtc.ToString('o')
            SHA256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
            FileVersion = $version.FileVersion
            ProductVersion = $version.ProductVersion
        }
    }
}
$bimInventory | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $script:PackageRoot '07_BIM_VISION\BIM_VISION_INVENTORY.json') -Encoding utf8
$bimInventory | Export-Csv -LiteralPath (Join-Path $script:PackageRoot '07_BIM_VISION\BIM_VISION_INVENTORY.csv') -NoTypeInformation -Encoding utf8
@'
# BIM Vision lokale referentie

Deze map bevat uitsluitend een technische inventaris van de lokaal aangetroffen BIM Vision-installatie. De propriëtaire programmabinaries zijn bewust niet herverdeeld. Gebruik de paden, versies en hashes om op dezelfde geautoriseerde werkplek te vergelijken. Voor gebruik op een andere machine moet BIM Vision via de rechthebbende en met een geldige licentie worden geinstalleerd.
'@ | Set-Content -LiteralPath (Join-Path $script:PackageRoot '07_BIM_VISION\README.md') -Encoding utf8

$missing | Sort-Object -Unique | Set-Content -LiteralPath (Join-Path $script:PackageRoot '09_MANIFESTS\MISSING_FILES.txt') -Encoding utf8

$manifestPath = Join-Path $script:PackageRoot '09_MANIFESTS\HANDOVER_FILE_MANIFEST.csv'
$manifest = Get-ChildItem -LiteralPath $script:PackageRoot -File -Recurse | Where-Object { $_.FullName -ne $manifestPath } | ForEach-Object {
    [pscustomobject]@{
        RelativePath = $_.FullName.Substring($script:PackageRoot.Length).TrimStart('\')
        Length = $_.Length
        LastWriteTimeUtc = $_.LastWriteTimeUtc.ToString('o')
        SHA256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    }
}
$manifest | Sort-Object RelativePath | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding utf8
$manifest | Sort-Object RelativePath | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $script:PackageRoot '09_MANIFESTS\HANDOVER_FILE_MANIFEST.json') -Encoding utf8

$sevenZip = 'C:\Program Files\7-Zip\7z.exe'
if (Test-Path -LiteralPath $sevenZip) {
    & $sevenZip a -tzip -mx=5 $archivePath $script:PackageRoot | Out-Null
    if ($LASTEXITCODE -ne 0) { throw '7-Zip packaging failed' }
} else {
    tar.exe -a -c -f $archivePath -C (Split-Path -Parent $script:PackageRoot) (Split-Path -Leaf $script:PackageRoot)
    if ($LASTEXITCODE -ne 0) { throw 'tar packaging failed' }
}

$archiveHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
"$archiveHash  $(Split-Path -Leaf $archivePath)" | Set-Content -LiteralPath ($archivePath + '.sha256') -Encoding ascii

[pscustomobject]@{
    PackageRoot = $script:PackageRoot
    Archive = $archivePath
    SHA256 = $archiveHash
    Files = (Get-ChildItem -LiteralPath $script:PackageRoot -File -Recurse).Count
    Missing = ($missing | Sort-Object -Unique).Count
} | ConvertTo-Json -Depth 3
