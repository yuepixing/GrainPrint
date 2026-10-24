#!/usr/bin/env python3
import flet as ft
from pathlib import Path
from datetime import datetime

from grainprint.services.excel import ExcelService
from grainprint.ui.components.styles import bottom_border
from grainprint.domain.entities import EntityType
from grainprint.domain.services import EntityService


class WelcomePage:
    def __init__(self, page: ft.Page, on_enter_app):
        self.page = page
        self.on_enter_app = on_enter_app
        self.setup_ui()

    def setup_ui(self):
        self.search_field = ft.TextField(
            prefix_icon=ft.Icons.SEARCH,
            hint_text="搜索粮食、标志物...",
            width=400, height=50, text_size=16,
            border={
                ft.ControlState.DEFAULT: ft.OutlineInputBorder(
                    border_radius=25,
                    side=ft.BorderSide(color=ft.Colors.GREEN_300),
                ),
                ft.ControlState.FOCUSED: ft.OutlineInputBorder(
                    border_radius=25,
                    side=ft.BorderSide(width=2, color=ft.Colors.GREEN_500),
                ),
            },
            on_submit=self.on_search,
        )

        self.content = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Image(
                                    src="/logo.png",
                                    width=300, height=300,
                                    fit=ft.BoxFit.CONTAIN,
                                ),
                                ft.Text(
                                    "粮食品质劣变标志物数据库",
                                    size=36, weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.GREEN_700,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ),
                    ft.Container(height=50),
                    ft.Container(
                        content=ft.Column(
                            [
                                self.search_field,
                                ft.IconButton(
                                    icon=ft.Icons.SEARCH,
                                    tooltip="搜索",
                                    on_click=self.on_search,
                                ),
                                ft.Container(height=25),
                                ft.Row(
                                    [
                                        ft.Button(
                                            content="进入数据库",
                                            icon=ft.Icons.ARROW_FORWARD,
                                            on_click=self.enter_main_app,
                                            style=ft.ButtonStyle(
                                                color=ft.Colors.WHITE,
                                                bgcolor=ft.Colors.GREEN_600,
                                                padding=ft.Padding.all(15),
                                            ),
                                        ),
                                        ft.OutlinedButton(
                                            content="快速导入",
                                            icon=ft.Icons.UPLOAD,
                                            on_click=self.quick_import,
                                            style=ft.ButtonStyle(
                                                color=ft.Colors.GREEN_600,
                                                side=ft.BorderSide(2, ft.Colors.GREEN_600),
                                                padding=ft.Padding.all(15),
                                            ),
                                        ),
                                        ft.OutlinedButton(
                                            content="清空数据库",
                                            icon=ft.Icons.DELETE_FOREVER,
                                            on_click=self.clear_database,
                                            style=ft.ButtonStyle(
                                                color=ft.Colors.RED_600,
                                                side=ft.BorderSide(2, ft.Colors.RED_600),
                                                padding=ft.Padding.all(15),
                                            ),
                                        ),
                                    ],
                                    spacing=20,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=ft.Colors.GREY_50,
            expand=True,
            padding=40,
        )

    def on_search(self, e):
        keyword = self.search_field.value
        if keyword:
            self.on_enter_app(search_keyword=keyword)

    def enter_main_app(self, e):
        self.on_enter_app()

    def quick_import(self, e):
        self.on_enter_app(action="import")

    def clear_database(self, e):
        def do_clear(_):
            from grainprint.core.database import reset_db
            self.page.pop_dialog()
            reset_db()
            self._show_message("✅ 已清空", "数据库已重置为空")

        def cancel(_):
            self.page.pop_dialog()

        confirm_dialog = ft.AlertDialog(
            title=ft.Text("⚠️ 确认清空数据库", color=ft.Colors.RED),
            content=ft.Text(
                "此操作将删除所有数据：\n\n"
                "• 全部粮食、品类、品种\n"
                "• 全部标志物及其关联\n\n"
                "删除后无法恢复！确定继续吗？",
                size=14,
            ),
            actions=[
                ft.TextButton(content="取消", on_click=cancel),
                ft.TextButton(
                    content="确认清空",
                    on_click=do_clear,
                    style=ft.ButtonStyle(color=ft.Colors.RED),
                ),
            ],
        )
        self.page.show_dialog(confirm_dialog)

    def _show_message(self, title: str, message: str, is_error: bool = False):
        dialog = ft.AlertDialog(
            title=ft.Text(title, color=ft.Colors.RED if is_error else None),
            content=ft.Text(message),
            actions=[ft.TextButton(
                content="确定",
                on_click=lambda e: self.page.pop_dialog(),
            )],
        )
        self.page.show_dialog(dialog)


class GrainPrintApp:

    def __init__(self, page: ft.Page):
        print("[APP] __init__ start")
        self.page = page
        self.page.title = "粮食品质劣变标志物数据库"
        self.page.window.maximized = True
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(font_family="Microsoft YaHei UI", use_material3=True)

        self._crop_view = None
        self._marker_view = None
        self._stats_view = None

        self.current_view = "welcome"
        self.main_view = "crop"

        print("[APP] 创建 ExcelService")
        self.excel_service = ExcelService()

        print("[APP] 创建 FilePicker")
        self.file_picker = ft.FilePicker()
        self.page.services.append(self.file_picker)

        self.page.navigate_to_marker = self.navigate_to_marker
        self.page.navigate_to_entity = self.navigate_to_entity

        print("[APP] 订阅 EventBus")
        from grainprint.domain.events import EventBus, EventType
        event_bus = EventBus()
        event_bus.subscribe(
            EventType.NAVIGATE_TO_MARKER,
            lambda e: self.navigate_to_marker(e.data['marker_id']),
        )
        event_bus.subscribe(
            EventType.NAVIGATE_TO_ENTITY,
            lambda e: self.navigate_to_entity(e.data['entity_type'], e.data['entity_id']),
        )

        print("[APP] 创建 WelcomePage")
        self.welcome_page = WelcomePage(page, self.enter_main_app)

        print("[APP] setup_ui")
        self.setup_ui()
        print("[APP] __init__ done")

    @property
    def crop_view(self):
        if self._crop_view is None:
            from grainprint.ui.views.crop import CropView
            self._crop_view = CropView(self.page)
        return self._crop_view

    @property
    def marker_view(self):
        if self._marker_view is None:
            from grainprint.ui.views.marker import MarkerView
            self._marker_view = MarkerView(self.page)
        return self._marker_view

    @property
    def stats_view(self):
        if self._stats_view is None:
            from grainprint.ui.views.stats_view import StatsView
            self._stats_view = StatsView(self.page)
        return self._stats_view

    def setup_ui(self):
        self.search_field = ft.TextField(
            prefix_icon=ft.Icons.SEARCH,
            hint_text="搜索...",
            width=300, height=40,
            border=ft.OutlineInputBorder(border_radius=20),
            on_submit=self.on_search,
            text_size=14,
        )

        self.nav_bar = ft.Container(
            content=ft.Row(
                [
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.HOME, on_click=self.go_to_welcome, tooltip="返回首页"),
                        ft.Text("粮食品质劣变标志物数据库", size=20,
                                weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700),
                    ]),
                    ft.Row([
                        self.create_nav_tab("粮食管理", "crop", True),
                        self.create_nav_tab("标志物库", "marker"),
                        self.create_nav_tab("统计分析", "stats"),
                    ], spacing=30),
                    ft.Row([
                        self.search_field,
                        ft.IconButton(
                            icon=ft.Icons.SEARCH,
                            tooltip="搜索",
                            on_click=self.on_search,
                        ),
                        ft.OutlinedButton(content="导入", icon=ft.Icons.UPLOAD, on_click=self.import_data),
                        ft.OutlinedButton(content="导出", icon=ft.Icons.DOWNLOAD, on_click=self.export_data),
                    ], spacing=10),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=10,
            bgcolor=ft.Colors.WHITE,
            border=bottom_border(ft.Colors.GREY_300),
            visible=False,
        )

        self.content = ft.Container(expand=True)

        self.page.add(ft.Column([self.nav_bar, self.content], spacing=0, expand=True))

        self.show_welcome_page()

    def show_welcome_page(self):
        print("[APP] show_welcome_page")
        self.current_view = "welcome"
        self.nav_bar.visible = False
        self.content.content = self.welcome_page.content
        self.page.update()
        print("[APP] show_welcome_page done")

    def enter_main_app(self, **kwargs):
        self.nav_bar.visible = True

        if "search_keyword" in kwargs:
            self.search_field.value = kwargs["search_keyword"]
            self._search_and_navigate(kwargs["search_keyword"])
        elif kwargs.get("action") == "import":
            self.switch_view("crop")
            self.page.run_task(self.import_data, None)
        else:
            self.switch_view("crop")

    def go_to_welcome(self, e):
        self.show_welcome_page()

    def create_nav_tab(self, text: str, view_name: str, active: bool = False):
        tab = ft.Container(
            content=ft.Text(
                text, size=16, weight=ft.FontWeight.W_500,
                color=ft.Colors.GREEN_700 if active else ft.Colors.BLACK_87,
            ),
            padding=10,
            border=ft.Border(bottom=ft.BorderSide(
                3, ft.Colors.GREEN_700 if active else ft.Colors.TRANSPARENT)),
            on_click=lambda e: self.switch_view(view_name),
        )
        tab.data = view_name
        return tab

    def switch_view(self, view_name: str, **kwargs):
        self.main_view = view_name

        for tab in self.nav_bar.content.controls[1].controls:
            is_active = tab.data == view_name
            tab.border = ft.Border(bottom=ft.BorderSide(
                3, ft.Colors.GREEN_700 if is_active else ft.Colors.TRANSPARENT))
            tab.content.color = ft.Colors.GREEN_700 if is_active else ft.Colors.BLACK_87

        if view_name == "crop":
            self.content.content = self.crop_view
            self.crop_view.refresh()
        elif view_name == "marker":
            self.content.content = self.marker_view
            self.marker_view.refresh()
            if marker_id := kwargs.get('marker_id'):
                self.marker_view.select_marker(marker_id)
        elif view_name == "stats":
            self.content.content = self.stats_view
            self.stats_view.refresh()

        self.page.update()

    def navigate_to_marker(self, marker_id: int):
        self.switch_view("marker", marker_id=marker_id)

    def navigate_to_entity(self, entity_type: str, entity_id: int):
        if entity_type in ['crop', 'subspecies', 'variety']:
            self.switch_view("crop")
            self.crop_view.select_entity(entity_type, entity_id)

    def on_search(self, e):
        keyword = self.search_field.value
        if keyword:
            self._search_and_navigate(keyword)

    def _search_and_navigate(self, keyword: str):
        results = EntityService.search(keyword)
        if not results:
            self._show_dialog("未找到", f"没有找到与“{keyword}”相关的数据")
            return

        exact = [r for r in results if r.name == keyword]
        candidates = exact or results
        if len(candidates) == 1:
            self._go_search_result(candidates[0])
            return

        dialog_items = []
        for r in candidates[:20]:
            label = f"[{r.type}] {' > '.join(r.path)}"

            def pick(e, result=r):
                self.page.pop_dialog()
                self._go_search_result(result)

            dialog_items.append(ft.TextButton(
                content=label,
                on_click=pick,
            ))
        dialog = ft.AlertDialog(
            title=ft.Text("请选择搜索结果"),
            content=ft.Column(dialog_items, tight=True, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton(
                content="取消",
                on_click=lambda e: self.page.pop_dialog(),
            )],
        )
        self.page.show_dialog(dialog)

    def _go_search_result(self, result):
        if result.type == 'marker':
            self.switch_view("marker")
            self.marker_view.filter_by_id(result.id)
        elif result.type in ('crop', 'subspecies', 'variety'):
            self.switch_view("crop")
            self.crop_view.select_entity(result.type, result.id)
        self.page.update()

    async def import_data(self, e):
        result = await self.file_picker.pick_files(
            dialog_title="选择Excel文件",
            allowed_extensions=["xlsx", "xls"],
        )
        if not result:
            return
        results = self.excel_service.import_data(result[0].path)
        total = sum(results.values())
        self._show_dialog(
            "导入成功",
            f"共导入 {total} 条数据\n\n"
            f"粮食: {results['crops']}\n"
            f"品级: {results['subspecies']}\n"
            f"品种: {results['varieties']}\n"
            f"标志物: {results['markers']}\n"
            f"关联: {results['associations']}",
        )
        self.switch_view(self.main_view)

    async def export_data(self, e):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = await self.file_picker.save_file(
            dialog_title="保存导出文件",
            file_name=f"grainprint_export_{timestamp}.xlsx",
            allowed_extensions=["xlsx"],
        )
        if not path:
            return
        filepath = Path(path)
        if not filepath.suffix:
            filepath = filepath.with_suffix('.xlsx')
        self.excel_service.export_data(filepath)
        self._show_dialog("导出成功", f"数据已导出到:\n{filepath.absolute()}")

    def _show_dialog(self, title: str, message: str):
        dlg = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[ft.TextButton(
                content="确定",
                on_click=lambda e: self.page.pop_dialog(),
            )],
        )
        self.page.show_dialog(dlg)

    def show_error(self, message: str):
        self._show_dialog("错误", message)


def main(page: ft.Page):
    print("[MAIN] main() called")
    page.title = "粮食品质劣变标志物数据库"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = ft.Colors.GREY_50

    print("[MAIN] 创建 GrainPrintApp")
    GrainPrintApp(page)
    print("[MAIN] main() done")


if __name__ == "__main__":
    ft.run(main)
