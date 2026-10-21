# GrainPrint 项目地图

## 项目定位

GrainPrint 是一个“粮食品质劣变标志物数据库”桌面/Web 应用，用于维护粮食、品类、品种、标志物及其关联信息，并支持 Excel 导入导出和统计展示。

技术栈：Python 3.12+、Flet 1.0.4、SQLAlchemy、DuckDB、pandas、openpyxl。

## 目录结构

```text
GrainPrint/
├── src/main.py                      # 应用入口，调用 ft.run(main)
├── src/assets/                      # Flet 静态资源（logo 等）
├── src/data/                         # 历史开发数据（不再作为运行时数据库）
├── src/grainprint/
│   ├── config.py                     # 便携式数据目录、运行时数据库、种子数据库
│   ├── data/grainprint.duckdb        # 打包用种子数据库（首次启动复制）
│   ├── core/
│   │   ├── database.py               # SQLAlchemy engine/session、初始化与重置
│   │   ├── models.py                 # Crop/Subspecies/Variety/Marker/Association ORM
│   │   ├── repository.py             # 通用数据访问仓储
│   │   └── schemas.py                # 搜索与详情结果结构
│   ├── domain/
│   │   ├── entities.py               # 领域实体与创建/更新模型
│   │   ├── services.py               # 实体与标志物业务服务
│   │   └── events.py                 # 导航事件与 EventBus
│   ├── services/excel.py             # Excel 导入导出
│   ├── scripts/                      # 数据库初始化/诊断脚本
│   └── ui/
│       ├── main.py                   # WelcomePage 与 GrainPrintApp 壳
│       ├── views/crop.py             # 粮食树、搜索、详情面板
│       ├── views/marker.py           # 标志物列表与详情
│       ├── views/stats_view.py       # 统计视图
│       └── components/               # 卡片、表单、关联对话框、样式
├── scripts/
│   ├── dev_web.sh                    # 本地 Web 启动
│   ├── build_macos.sh                # macOS .app 构建（PyInstaller）
│   └── build_windows.ps1             # Windows .exe 构建（PyInstaller）
└── docs/                             # 项目地图与迁移记录
```

## 运行时数据

- 开发模式：`<项目>/data/grainprint.duckdb`
- Windows 打包模式：`GrainPrint.exe` 所在目录下的 `data/grainprint.duckdb`
- macOS 打包模式：`GrainPrint.app` 所在目录下的 `data/grainprint.duckdb`
- 首次启动时若运行时数据库不存在，会复制 `src/grainprint/data/grainprint.duckdb`。

## 常用命令

```bash
# 本地 Web
./scripts/dev_web.sh

# 本地桌面
.venv/bin/flet run -a assets src/main.py

# macOS 构建（PyInstaller，输出 dist/GrainPrint.app）
./scripts/build_macos.sh

# Windows 构建（PyInstaller，输出 dist/GrainPrint.exe）
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

如果安装了完整 Xcode，也可以使用 Flet 官方 `flet build macos`；Windows 上同理可使用 `flet build windows`。当前脚本选择 `flet pack`/PyInstaller，便于在没有完整 Xcode 的机器上构建。

## 核心数据流

1. `src/main.py` 启动 Flet 并创建 `GrainPrintApp`。
2. UI 视图调用 `domain/services.py`。
3. 服务层调用 `core/repository.py` 和 SQLAlchemy session。
4. SQLAlchemy 通过 DuckDB engine 读写运行时数据库。
5. Excel 导入导出由 `services/excel.py` 完成。
6. 视图之间通过 `domain/events.py` 的 EventBus 导航。

## CI / 跨平台构建

`.github/workflows/build.yml` 提供 macOS 与 Windows 的 GitHub Actions 构建矩阵，可手动触发 `Build GrainPrint`，并上传两个平台的构建产物。仓库推送到 GitHub 后即可验证 Windows 真实构建。

## 当前验证状态（2026-10-20）

- Flet：`1.0.4`
- FastAPI：`0.115.12`
- 编译：`python -m compileall` 通过
- 测试：`pytest -q`，6 项通过
- Web：`http://127.0.0.1:8765` 正在运行
- macOS：`dist/GrainPrint.app` 已构建并通过 ad-hoc 签名校验
- Windows：`scripts/build_windows.ps1` 已提供；需要在 Windows 主机上执行，或推送到 GitHub 后运行 `Build GrainPrint` workflow
