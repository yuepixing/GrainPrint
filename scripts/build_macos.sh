#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# A stable PyPI mirror avoids intermittent files.pythonhosted.org TLS resets.
export PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"

if [ ! -x .venv/bin/python ]; then
  uv venv --python 3.13 .venv
fi
uv pip install --python .venv/bin/python -e ".[dev]"

args=(
  -y src/main.py
  -n GrainPrint
  --product-name GrainPrint
  --product-version 0.5.0
  --bundle-id cn.digitalsalt.grainprint
  -i src/assets/logo.icns
  --add-data "src/assets:assets"
  --add-data "src/grainprint/data:grainprint/data"
  --hidden-import grainprint.ui.views.crop
  --hidden-import grainprint.ui.views.marker
  --hidden-import grainprint.ui.views.stats_view
)
if [ -n "${MACOS_SIGNING_IDENTITY:-}" ]; then
  args+=(--codesign-identity "$MACOS_SIGNING_IDENTITY")
fi

.venv/bin/flet pack "${args[@]}"

# PyInstaller does not currently map Flet's --product-version to macOS plist.
plutil -replace CFBundleShortVersionString -string 0.5.0 dist/GrainPrint.app/Contents/Info.plist
plutil -replace CFBundleVersion -string 1 dist/GrainPrint.app/Contents/Info.plist
codesign --force --deep --sign "${MACOS_SIGNING_IDENTITY:--}" dist/GrainPrint.app

echo "macOS app: $(pwd)/dist/GrainPrint.app"
