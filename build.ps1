$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Find-InnoSetupCompiler {
    $cmd = Get-Command iscc -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 5\ISCC.exe"
    )

    foreach ($path in $candidates) {
        if (Test-Path $path) {
            return $path
        }
    }

    return $null
}

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

$version = & $python -c "from version import __version__; print(__version__)"
if (-not $version) {
    throw "Не удалось прочитать __version__ из version.py"
}

Write-Host "Сборка ChatList $version"

& $python -m pip install pyinstaller --quiet
& $python -m PyInstaller 4-ChatList.spec --noconfirm

$exePath = Join-Path $PSScriptRoot "dist\4-ChatList-$version.exe"
if (-not (Test-Path $exePath)) {
    throw "Не найден файл для установщика: $exePath"
}

$iscc = Find-InnoSetupCompiler
if ($iscc) {
    Write-Host "Сборка установщика ChatList-Setup-$version.exe"
    & $iscc "/DAppVersion=$version" "installer.iss"
    Write-Host "Готово:"
    Write-Host "  dist\4-ChatList-$version.exe"
    Write-Host "  dist\ChatList-Setup-$version.exe"
} else {
    Write-Host "Inno Setup не найден — exe собран, установщик не создан."
    Write-Host "Установите Inno Setup 6: https://jrsoftware.org/isinfo.php"
    Write-Host "Затем выполните:"
    Write-Host "  iscc /DAppVersion=$version installer.iss"
    Write-Host "Готово: dist\4-ChatList-$version.exe"
}
