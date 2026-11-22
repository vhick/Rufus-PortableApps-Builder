param(
  [string]$Metadata = 'work/resolve.json',
  [string]$Audit = 'work/source-audit.json',
  [string]$Binary = 'work/official-rufus.exe',
  [string]$Stage = 'work/stage/RufusPortable'
)
$ErrorActionPreference = 'Stop'
$config = Get-Content -Raw -LiteralPath 'config/builder.json' | ConvertFrom-Json
$meta = Get-Content -Raw -LiteralPath $Metadata | ConvertFrom-Json
$auditMeta = Get-Content -Raw -LiteralPath $Audit | ConvertFrom-Json
if ($auditMeta.source_check -ne 'PASS' -or $auditMeta.upstream_version -ne $meta.version) { throw 'Source contract audit missing or version mismatch' }
if (Test-Path $Stage) { throw "Staging folder already exists (refusing unsafe overwrite): $Stage" }
if (-not (Test-Path $Binary)) { throw "Official Rufus executable missing: $Binary" }
$sig = Get-AuthenticodeSignature -LiteralPath $Binary
if ($sig.Status -ne 'Valid') { throw "Official upstream EXE signature invalid: $($sig.Status) - $($sig.StatusMessage)" }
if (-not $sig.SignerCertificate -or $sig.SignerCertificate.Subject -notmatch [regex]::Escape($config.allowed_signer_name)) {
  throw "Unexpected upstream signing publisher: $($sig.SignerCertificate.Subject)"
}
if ((Get-FileHash -LiteralPath $Binary -Algorithm SHA256).Hash.ToLowerInvariant() -ne $meta.downloaded_sha256) {
  throw 'Official binary was modified after download; SHA256 mismatch'
}
$info = (Get-Item -LiteralPath $Binary).VersionInfo
if (($info.ProductVersion + ' ' + $info.FileVersion) -notmatch ('(?<!\d)' + [regex]::Escape($meta.version) + '(?:\.|\b)')) {
  throw "Signed binary ProductVersion/FileVersion does not match upstream version $($meta.version): $($info.ProductVersion) / $($info.FileVersion)"
}
$root = New-Item -ItemType Directory -Path $Stage -Force
$folders = @('App/Rufus','App/AppInfo/Launcher','App/DefaultData','Data','Other/Source')
foreach ($p in $folders) { New-Item -ItemType Directory -Path (Join-Path $Stage $p) -Force | Out-Null }
$vendorDest = Join-Path $Stage 'App/Rufus/rufus.exe'
Copy-Item -LiteralPath $Binary -Destination $vendorDest
Set-Content -LiteralPath (Join-Path $Stage 'App/Rufus/rufus.sha256') -Value $meta.downloaded_sha256 -Encoding ascii
# The user's portable settings are NOT embedded in distributed ZIP/installer. Runtime
# creates Data/Runtime/rufus.ini directly. This avoids data-loss on crash/upgrade.
Add-Type -AssemblyName System.Drawing
$icon = [System.Drawing.Icon]::ExtractAssociatedIcon((Resolve-Path -LiteralPath $Binary).Path)
if (-not $icon) { throw 'Could not extract the genuine Rufus icon from the signed upstream executable' }
$iconPath = Join-Path $Stage 'App/AppInfo/appicon.ico'
$stream = [System.IO.File]::Open($iconPath,[System.IO.FileMode]::CreateNew)
try { $icon.Save($stream) } finally { $stream.Dispose() }
foreach ($size in @(16,32)) {
  $bmp = [System.Drawing.Bitmap]::new($size,$size)
  $graphics = [System.Drawing.Graphics]::FromImage($bmp)
  try {
    $graphics.DrawImage($icon.ToBitmap(), 0, 0, $size, $size)
    $path = Join-Path $Stage "App/AppInfo/appicon_$size.png"
    $bmp.Save($path,[System.Drawing.Imaging.ImageFormat]::Png)
  } finally { $graphics.Dispose(); $bmp.Dispose() }
}
$icon.Dispose()
$versionParts = @($meta.version.Split('.'))
while ($versionParts.Count -lt 4) { $versionParts += '0' }
$packageVersion = ($versionParts | Select-Object -First 4) -join '.'
$appinfo = @"
[Format]
Type=PortableApps.comFormat
Version=3.9

[Details]
Name=Rufus Portable
AppID=RufusPortable
Publisher=Pete Batard
Homepage=https://rufus.ie/
Category=Utilities
Description=Create bootable USB drives
Language=Multilingual

[License]
Shareable=true
OpenSource=true
Freeware=true
CommercialUse=true

[Version]
PackageVersion=$packageVersion
DisplayVersion=$($meta.version) ($($config.package_revision))

[Control]
Icons=1
Start=RufusPortable.exe
"@
Set-Content -LiteralPath (Join-Path $Stage 'App/AppInfo/appinfo.ini') -Value $appinfo -Encoding utf8
$launcherInfo = @"
; This is descriptive metadata for a custom compiled launcher, NOT an official
; PortableApps.com Launcher executable or an official PAL configuration.
[RufusPortable]
LauncherImplementation=Native-C++
OfficialPayload=App\Rufus\rufus.exe
RuntimeLocation=Data\Runtime\rufus.exe
ConfigurationLocation=Data\Runtime\rufus.ini
RecoveryInventory=Data\TraceGuard\runtime-inventory.tsv
"@
Set-Content -LiteralPath (Join-Path $Stage 'App/AppInfo/Launcher/RufusPortable.ini') -Value $launcherInfo -Encoding utf8
$license = Get-ChildItem -LiteralPath 'work/source' -File | Where-Object { $_.Name -in @('LICENSE.txt','LICENSE','COPYING') } | Select-Object -First 1
if (-not $license) { throw 'Cannot locate official upstream redistribution license in source tag; refuse packaging' }
Copy-Item -LiteralPath $license.FullName -Destination (Join-Path $Stage 'Other/Source/UPSTREAM-LICENSE.txt')
Copy-Item -LiteralPath 'LICENSE' -Destination (Join-Path $Stage 'Other/Source/LAUNCHER-LICENSE.txt')
Copy-Item -LiteralPath 'launcher/RufusPortable.cpp' -Destination (Join-Path $Stage 'Other/Source/RufusPortable.cpp')
Copy-Item -LiteralPath 'scripts/build-launcher.ps1' -Destination (Join-Path $Stage 'Other/Source/build-launcher.ps1')
Copy-Item -LiteralPath 'docs/PORTABILITY-AUDIT.md' -Destination (Join-Path $Stage 'Other/Source/PORTABILITY-AUDIT.md')
Copy-Item -LiteralPath $Audit -Destination (Join-Path $Stage 'Other/Source/source-audit.json')
$manifest = [ordered]@{
  upstream = $config.upstream
  upstream_version = $meta.version
  upstream_tag = $meta.tag
  release_id = $meta.release_id
  asset_name = $meta.asset_name
  asset_id = $meta.asset_id
  asset_sha256 = $meta.downloaded_sha256
  asset_digest_verified = [bool]($meta.asset_digest)
  authenticode_status = $sig.Status.ToString()
  authenticode_subject = $sig.SignerCertificate.Subject
  source_commit = $auditMeta.source_commit
  source_portability_contract = $auditMeta.source_check
  compiler = 'MSVC (version recorded by GitHub Actions summary)'
  source_compilation = $false
  toolchain_policy = 'Compiler applies only to portable launcher, not upstream Rufus'
  shared_packager = $config.package_builder
  shared_publisher = $config.release_publisher
  package_revision = $config.package_revision
  runtime_validation = 'Windows synthetic fixture required; Rufus USB operations manual only'
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $Stage 'Other/Source/build-manifest.json') -Encoding utf8
& "$PSScriptRoot/build-launcher.ps1" -Stage $Stage
if ($LASTEXITCODE -ne 0) { throw "Failed C++ launcher build: $LASTEXITCODE" }
$launcherExe = Join-Path $Stage 'RufusPortable.exe'
$peFile = [IO.File]::ReadAllBytes((Resolve-Path $launcherExe).Path)
if ($peFile.Length -lt 2048 -or $peFile[0] -ne 0x4d -or $peFile[1] -ne 0x5a) { throw 'Compiled launcher is not a valid PE candidate' }
Write-Host 'Stage complete: ' $Stage
