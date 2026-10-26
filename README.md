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

## 数据安全规则

- 每个数据文件夹只能运行一份 GrainPrint；再次启动会提示使用已打开的软件，避免 DuckDB 文件锁冲突。
- 已使用过的项目若找不到 `data/grainprint.duckdb`，软件会停止并显示路径，**不会静默创建新数据库**。
- 编辑关联、批量关联和新增数据均使用完整事务：失败时不保存任何部分修改。
- `备注1`用于物质类型：`标志物` 或 `特征物质`；`备注2`用于来源：`自行筛选` 或 `文献报道：https://…`。
