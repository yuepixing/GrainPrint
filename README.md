# GrainPrint 粮食品质劣变标志物数据库

基于 **Flet 1.0.4**、SQLAlchemy 和 DuckDB 的跨平台谷物管理系统。

## 快速开始

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/flet run --web --host 127.0.0.1 --port 8765 -a assets src/main.py
```

打开：<http://127.0.0.1:8765>

也可以直接运行：

```bash
./scripts/dev_web.sh
```

## 打包

- macOS：`./scripts/build_macos.sh` → `dist/GrainPrint.app`
- Windows：`powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1` → `dist/GrainPrint.exe`

详细结构见 [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md)。
Flet 1.0 升级说明见 [`docs/FLET_1_MIGRATION.md`](docs/FLET_1_MIGRATION.md)。
