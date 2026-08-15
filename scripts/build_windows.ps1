$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.11+ first."
}

if (-not (Test-Path .venv)) {
    py -3.12 -m venv .venv
}

$python = Join-Path $PWD ".venv\Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt pyinstaller
& $python -m pytest

Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
& $python -m PyInstaller --clean --noconfirm packaging\SouthParkDownloader.spec

$iscc = @(
    "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Warning "Inno Setup 6 was not found. The portable PyInstaller build is ready in dist\SouthParkDownloader."
    exit 0
}

& $iscc packaging\SouthParkDownloader.iss
Write-Host "Release artifacts are in dist\"
