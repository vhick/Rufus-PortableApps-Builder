param(
  [Parameter(Mandatory)][string]$Stage,
  [string]$Source = 'launcher/RufusPortable.cpp'
)
$ErrorActionPreference = 'Stop'
$stagePath = (Resolve-Path -LiteralPath $Stage).Path
$sourcePath = (Resolve-Path -LiteralPath $Source).Path
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
if (-not (Test-Path -LiteralPath $vswhere)) { throw 'vswhere.exe is missing: Microsoft Visual Studio build tools required' }
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if ($LASTEXITCODE -ne 0 -or -not $vs) { throw 'No compatible installed MSVC C++ toolchain; do not silently substitute compilers' }
$vcvars = Join-Path ($vs | Select-Object -First 1) 'VC/Auxiliary/Build/vcvars64.bat'
if (-not (Test-Path $vcvars)) { throw "MSVC initialization missing: $vcvars" }
$src = $sourcePath.Replace('"', '')
$rootExe = (Join-Path $stagePath 'RufusPortable.exe').Replace('"', '')
$resource = (Join-Path $stagePath 'launcher.res').Replace('"', '')
$resourceScript = (Join-Path $stagePath 'launcher.rc').Replace('"', '')
$icon = (Join-Path $stagePath 'App/AppInfo/appicon.ico').Replace('"', '')
# Use a separate .cmd because vcvars64.bat sets PATH, INCLUDE, LIB in its cmd session.
$cmd = Join-Path $stagePath 'build-launcher.cmd'
$contents = @"
@echo off
setlocal EnableExtensions
call "$vcvars" >nul
if errorlevel 1 exit /b 11
where cl.exe >nul || exit /b 12
where rc.exe >nul || exit /b 13
rc.exe /nologo /fo "$resource" "$resourceScript" || exit /b 14
cl.exe /nologo /std:c++17 /EHsc /MT /O2 /W4 /utf-8 /DUNICODE /D_UNICODE "$src" "$resource" /link /SUBSYSTEM:WINDOWS /OUT:"$rootExe" || exit /b 15
exit /b 0
"@
Set-Content -LiteralPath $cmd -Value $contents -Encoding ascii
# Make sure rc.exe sees the absolute icon path, independent of working dir.
$rcIcon = $icon.Replace('\','/')
Set-Content -LiteralPath $resourceScript -Value ('1 ICON "' + $rcIcon + '"') -Encoding ascii
& cmd.exe /d /c "`"$cmd`""
if ($LASTEXITCODE -ne 0) { throw "Launcher compilation failed (exit=$LASTEXITCODE); Visual Studio: $vs" }
if (-not (Test-Path $rootExe)) { throw 'Compiled RufusPortable.exe not found' }
Get-ChildItem -LiteralPath $stagePath -File | Where-Object { $_.Extension -in '.obj','.res','.rc' -or $_.Name -eq 'build-launcher.cmd' } | Remove-Item -Force
Write-Host "Compiled a genuine native Windows C++ launcher: $rootExe"
