#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# A stable PyPI mirror avoids intermittent files.pythonhosted.org TLS resets.
export PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"

if [ ! -x .venv/bin/python ]; then
  uv venv --python 3.13 .venv
fi
uv pip install --python .venv/bin/python -e ".[dev]"
exec .venv/bin/flet run --web \
  --host "${FLET_HOST:-127.0.0.1}" \
  --port "${FLET_PORT:-8765}" \
  -a assets \
  src/main.py
