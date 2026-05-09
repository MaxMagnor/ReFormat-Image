param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$VenvPython = ".\.venv\Scripts\python.exe"

New-Item -ItemType Directory -Force .tmp | Out-Null
$env:TEMP = (Resolve-Path .tmp).Path
$env:TMP = $env:TEMP

if ($Clean) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist, ReFormatImage.spec
}

if (!(Test-Path $VenvPython)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $VenvPython -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $VenvPython -m PyInstaller `
    --onefile `
    --name ReFormatImage `
    --clean `
    --paths src `
    src\reformat_image\cli.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $VenvPython -m PyInstaller `
    --onefile `
    --noconsole `
    --name ReFormatImageContext `
    --clean `
    --paths src `
    src\reformat_image\cli.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Copy-Item -LiteralPath dist\ReFormatImage.exe -Destination dist\reformat.exe -Force

Write-Host "Built dist\ReFormatImage.exe"
Write-Host "Built dist\ReFormatImageContext.exe"
Write-Host "Built dist\reformat.exe"
