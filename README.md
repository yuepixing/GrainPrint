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

## 数据恢复说明

GrainPrint 会在启动和重置数据库时自动备份：

- `data/backup/grainprint_latest.duckdb`：最近一次备份
- `data/backup/grainprint_YYYYMMDD.duckdb`：当日首次启动时的备份

如果 `data/grainprint.duckdb` 丢失，应用会自动从最新备份恢复；不会直接变成空库。
如需手动恢复，可以先用最新备份覆盖 `grainprint.duckdb`，再重新打开软件。
