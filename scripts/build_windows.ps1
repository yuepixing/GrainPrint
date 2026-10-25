$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

# A stable PyPI mirror avoids intermittent files.pythonhosted.org TLS resets.
if (-not $env:PIP_INDEX_URL) {
    $env:PIP_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
}

if (-not (Test-Path ".venv/Scripts/python.exe")) {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv venv --python 3.13 .venv
    } else {
        python -m venv .venv
    }
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv pip install --python .venv/Scripts/python.exe -e ".[dev]"
} else {
    & .venv/Scripts/python.exe -m pip install --upgrade pip
    & .venv/Scripts/python.exe -m pip install -e ".[dev]"
}

& .venv/Scripts/flet.exe pack -y src/main.py `
  -n GrainPrint `
  --product-name GrainPrint `
  --product-version 0.5.0 `
  --bundle-id cn.digitalsalt.grainprint `
  --add-data "src/assets;assets" `
  --add-data "src/grainprint/data;grainprint/data" `
  --hidden-import grainprint.ui.views.crop `
  --hidden-import grainprint.ui.views.marker `
  --hidden-import grainprint.ui.views.stats_view

Write-Host "Windows executable: $((Get-Location).Path)/dist/GrainPrint.exe"
