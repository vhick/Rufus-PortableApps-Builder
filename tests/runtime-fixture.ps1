param([Parameter(Mandatory)][string]$Launcher)
$ErrorActionPreference = 'Stop'
$testRoot = Join-Path $env:RUNNER_TEMP ('RufusPortableFixture-' + [guid]::NewGuid().ToString('N'))
$portable = Join-Path $testRoot 'RufusPortable'
New-Item -ItemType Directory -Path (Join-Path $portable 'App/Rufus') -Force | Out-Null
Copy-Item -LiteralPath $Launcher -Destination (Join-Path $portable 'RufusPortable.exe')
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
$vcvars = Join-Path ($vs | Select-Object -First 1) 'VC/Auxiliary/Build/vcvars64.bat'
$fake = (Resolve-Path 'tests/fake-rufus.cpp').Path
$target = Join-Path $portable 'App/Rufus/rufus.exe'
$cmd = Join-Path $testRoot 'compile-fixture.cmd'
function Make-Fake([int]$number) {
  $lines = "@echo off`r`ncall `"$vcvars`" >nul`r`ncl.exe /nologo /std:c++17 /EHsc /O1 /DUNICODE /D_UNICODE /DTEST_VERSION=$number `"$fake`" /link /SUBSYSTEM:WINDOWS /OUT:`"$target`"`r`n"
  [IO.File]::WriteAllText($cmd,$lines,[Text.Encoding]::ASCII)
  & cmd.exe /d /c "`"$cmd`""
  if ($LASTEXITCODE -ne 0) { throw "Synthetic app compilation failed: $LASTEXITCODE" }
  (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() | Set-Content -LiteralPath (Join-Path $portable 'App/Rufus/rufus.sha256') -Encoding ascii
}
function Run-Portable([string]$location) {
  $program = Join-Path $location 'RufusPortable.exe'
  $process = Start-Process -FilePath $program -ArgumentList @('--gui') -Wait -PassThru
  if ($process.ExitCode -ne 0) { throw "Portable launcher fixture failed with code $($process.ExitCode)" }
  $runtime = Join-Path $location 'Data/Runtime'
  foreach($required in @('rufus.exe','rufus.ini','data-created.txt','empty-folder','empty-folder/nested-empty')) {
    if(-not(Test-Path (Join-Path $runtime $required))) { throw "Runtime missing $required" }
  }
  $inventory = Get-Content -Raw -LiteralPath (Join-Path $location 'Data/TraceGuard/runtime-inventory.tsv')
  if ($inventory -notmatch 'nested-empty') { throw 'TraceGuard omitted nested empty directories' }
  if (Test-Path (Join-Path $location 'App/Rufus/rufus.ini')) { throw 'Settings escaped Data to App/Rufus' }
}
try {
  Make-Fake 1
  Run-Portable $portable
  $settings = Get-Content -Raw -LiteralPath (Join-Path $portable 'Data/Runtime/rufus.ini')
  if ($settings -notmatch 'fixture_version=1') { throw 'Initial INI persistence failed' }
  Make-Fake 2
  Run-Portable $portable
  $backups = @(Get-ChildItem -LiteralPath (Join-Path $portable 'Data/TraceGuard/Backups') -File)
  if ($backups.Count -lt 1) { throw 'Upgrade did not back up existing INI' }
  $settings = Get-Content -Raw -LiteralPath (Join-Path $portable 'Data/Runtime/rufus.ini')
  if ($settings -notmatch 'fixture_version=1' -or $settings -notmatch 'fixture_version=2') { throw 'Settings lost across upgrade' }
  Set-Content -LiteralPath (Join-Path $portable 'Data/TraceGuard/active-session.txt') -Value 'simulated crash session'
  Run-Portable $portable
  if (@(Get-ChildItem -LiteralPath (Join-Path $portable 'Data/TraceGuard') -Filter 'recovered-session-*').Count -lt 1) { throw 'Crash journal was not recovered' }
  $moved = Join-Path $testRoot 'MovedPortable'
  Move-Item -LiteralPath $portable -Destination $moved
  Run-Portable $moved
  Write-Host 'PASS: synthetic first launch, crash recovery, INI preservation, binary upgrade, nested empty folders, TraceGuard, directory relocation.'
} finally {
  # Fixture contains no real USB tool and cannot access a physical drive.
  if (Test-Path $testRoot) { Remove-Item -LiteralPath $testRoot -Force -Recurse }
}
