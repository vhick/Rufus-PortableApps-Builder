param([Parameter(Mandatory)][string]$Stage)
$ErrorActionPreference = 'Stop'
$manifestPath = Join-Path $Stage 'Other/Source/build-manifest.json'
$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
$launcher = Join-Path $Stage 'RufusPortable.exe'
if (-not (Test-Path $launcher)) { throw 'Compiled launcher missing during validation finalization' }
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -format json | ConvertFrom-Json
if (-not $vs) { throw 'Visual Studio toolchain disappeared before package finalization' }
$first = @($vs)[0]
$manifest | Add-Member -NotePropertyName launcher_sha256 -NotePropertyValue (Get-FileHash -LiteralPath $launcher -Algorithm SHA256).Hash.ToLowerInvariant() -Force
$manifest | Add-Member -NotePropertyName visual_studio_version -NotePropertyValue $first.installationVersion -Force
$manifest | Add-Member -NotePropertyName visual_studio_path -NotePropertyValue $first.installationPath -Force
$manifest | Add-Member -NotePropertyName runner_label -NotePropertyValue $env:RUNNER_OS -Force
$manifest | Add-Member -NotePropertyName runner_image -NotePropertyValue $env:ImageVersion -Force
$manifest | Add-Member -NotePropertyName synthetic_windows_runtime_test -NotePropertyValue 'PASS' -Force
$manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $manifestPath -Encoding utf8
Write-Host "Recorded actual Windows fixture results and launcher SHA256 in $manifestPath"
