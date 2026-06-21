$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

$version = & $python -c "from version import __version__; print(__version__)"
if (-not $version) {
    throw "Не удалось прочитать __version__ из version.py"
}

$distDir = Join-Path $PSScriptRoot "..\dist"
$releaseDir = Join-Path $PSScriptRoot "..\release"

$portableName = "4-ChatList-$version.exe"
$setupName = "ChatList-Setup-$version.exe"
$portableSrc = Join-Path $distDir $portableName
$setupSrc = Join-Path $distDir $setupName

if (-not (Test-Path $portableSrc)) {
    Write-Host "Сборка не найдена, запускаю build.ps1..."
    & (Join-Path $PSScriptRoot "..\build.ps1")
}

if (-not (Test-Path $portableSrc)) {
    throw "Не найден: $portableSrc`nСначала выполните .\build.ps1"
}

New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

Copy-Item $portableSrc (Join-Path $releaseDir $portableName) -Force
if (Test-Path $setupSrc) {
    Copy-Item $setupSrc (Join-Path $releaseDir $setupName) -Force
} else {
    Write-Warning "Установщик не найден: $setupSrc"
}

$checksumLines = @()
Get-ChildItem $releaseDir -Filter "*.exe" | ForEach-Object {
    $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()
    $checksumLines += "$hash  $($_.Name)"
}

$checksumPath = Join-Path $releaseDir "SHA256SUMS.txt"
$checksumLines | Set-Content -Path $checksumPath -Encoding UTF8

Write-Host ""
Write-Host "Release $version подготовлен: $releaseDir"
Get-ChildItem $releaseDir | Format-Table Name, Length
Write-Host ""
Write-Host "Release notes: скопируйте docs\release-notes-template.md в release\notes-v$version.md"
Write-Host ""
Write-Host "GitHub Release (пример):"
Write-Host "  git tag -a v$version -m `"ChatList $version`""
Write-Host "  git push origin v$version"
Write-Host ""
Write-Host "  gh release create v$version --title `"ChatList $version`" --notes-file release\notes-v$version.md release\*"
