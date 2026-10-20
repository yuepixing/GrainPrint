# Flet 1.0 迁移记录

## 版本结论

- 原项目依赖：Flet `>=0.83.1`
- 当前最新稳定版：Flet `1.0.4`（2026-10-08 发布）
- 运行时依赖：`flet>=1.0.4,<1.1`
- 开发/构建依赖：`flet[all]>=1.0.4,<1.1`（放在 `dev` extra，避免把 CLI 打进应用包）
- Python 版本：开发环境使用 3.13，Flet 构建使用 3.14，项目声明 `>=3.12`

依据：

- [Flet 1.0 发布说明](https://flet.dev/blog/flet-1-0/)
- [Breaking changes and deprecations](https://flet.dev/docs/updates/breaking-changes/)
- [TextField 文档](https://flet.dev/docs/controls/textfield/)

## 已完成的语法/API 更新

### 1. 应用入口

Flet 1.0 中 `ft.app()` 已移除，统一使用 `ft.run()`。项目原本已经使用：

```python
ft.run(main)
```

### 2. TextField 边框

Flet 1.0 将 `InputBorder` 改为类层级，并弃用 `TextField.border_radius`、`border_color`、`focused_border_color`。项目已改为：

```python
border={
    ft.ControlState.DEFAULT: ft.OutlineInputBorder(
        border_radius=25,
        side=ft.BorderSide(color=ft.Colors.GREEN_300),
    ),
    ft.ControlState.FOCUSED: ft.OutlineInputBorder(
        border_radius=25,
        side=ft.BorderSide(width=2, color=ft.Colors.GREEN_500),
    ),
}
```

### 3. Padding / Border

项目继续使用 Flet 0.85+ 的类方法形式：

```python
ft.Padding.all(15)
ft.Border(bottom=ft.BorderSide(...))
```

不再使用已移除的 `ft.padding.all()` / `ft.border.all()` 模块级函数。

### 4. Button

Flet 1.0 中 `ElevatedButton` 已移除，替换为 `Button`。项目使用 `ft.Button`，符合最新 API。

### 5. 打包存储目录

Flet 0.86+ 的应用包目录只读。项目已改为：

```python
FLET_APP_STORAGE_DATA
```

并将 DuckDB 数据库写入该目录。首次启动会从包内种子数据库复制一份。

## Web 兼容性

`flet-web 1.0.4` 当前与 FastAPI `0.152` 的 `FastAPI.__init__(openapi_prefix=...)` 不兼容。因此项目临时固定：

```text
fastapi>=0.115.12,<0.116
```

等 Flet 发布兼容 FastAPI 新版本的修复后，可以移除该上界。

## 验证

- Python 3.13 环境安装成功。
- `python -m compileall` 通过。
- `flet run --web --host 127.0.0.1 --port 8765 -a assets src/main.py` 启动成功。
- 浏览器页面标题显示“粮食品质劣变标志物数据库”。
- 升级后的启动过程不再出现 Flet 1.0 弃用警告。
