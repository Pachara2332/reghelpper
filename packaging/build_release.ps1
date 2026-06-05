param(
    [string]$Version = "1.0.0",
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$distApp = Join-Path $root "dist\MSU Registration Helper"
$releaseDir = Join-Path $root "release"
$portableZip = Join-Path $releaseDir "MSU-Registration-Helper-$Version-portable.zip"
$installerScript = Join-Path $PSScriptRoot "installer.iss"

Set-Location $root

Write-Host "==> Building PyInstaller app"
python -m PyInstaller --clean --noconfirm "MSU Registration Helper.spec"

if (!(Test-Path -LiteralPath $distApp)) {
    throw "PyInstaller output not found: $distApp"
}

Write-Host "==> Copying Playwright Chromium runtime"
$browserSource = $env:PLAYWRIGHT_BROWSERS_PATH
if ([string]::IsNullOrWhiteSpace($browserSource)) {
    $browserSource = Join-Path $env:LOCALAPPDATA "ms-playwright"
}
if (!(Test-Path -LiteralPath $browserSource)) {
    throw "Playwright browser cache not found: $browserSource. Run: python -m playwright install chromium"
}

$browserTarget = Join-Path $distApp "ms-playwright"
if (Test-Path -LiteralPath $browserTarget) {
    Remove-Item -LiteralPath $browserTarget -Recurse -Force
}
New-Item -ItemType Directory -Path $browserTarget | Out-Null
Get-ChildItem -LiteralPath $browserSource -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $browserTarget -Recurse -Force
}

Write-Host "==> Removing local user data from distributable"
foreach ($name in @("msu_profile", "msu_helper.db", "logs", "screenshots")) {
    $target = Join-Path $distApp $name
    if (Test-Path -LiteralPath $target) {
        Remove-Item -LiteralPath $target -Recurse -Force
    }
}

New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
if (Test-Path -LiteralPath $portableZip) {
    Remove-Item -LiteralPath $portableZip -Force
}

Write-Host "==> Creating portable zip"
Compress-Archive -LiteralPath $distApp -DestinationPath $portableZip -Force

if (!$SkipInstaller) {
    $iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
    $isccPath = $null
    if (!$iscc) {
        $candidate = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        if (Test-Path -LiteralPath $candidate) {
            $isccPath = $candidate
        }
    } else {
        $isccPath = $iscc.Source
    }

    if ($isccPath) {
        Write-Host "==> Building installer with Inno Setup"
        & $isccPath "/DMyAppVersion=$Version" $installerScript
    } else {
        Write-Warning "Inno Setup not found. Portable zip created, installer skipped."
        Write-Warning "Install Inno Setup 6, then rerun this script without -SkipInstaller."
    }
}

Write-Host "==> Release output"
Get-ChildItem -LiteralPath $releaseDir | Select-Object Name, Length, LastWriteTime
