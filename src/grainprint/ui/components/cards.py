import flet as ft
from typing import Optional, Callable
from grainprint.ui.components.styles import bordered, selected_border, pad_only, pad_sym


class StatCard(ft.Container):

    def __init__(self, label: str, value: int,
                 icon: Optional[str] = None,
                 color: str = ft.Colors.GREEN_700,
                 width: int = 200):
        if icon:
            content = ft.Row([
                ft.Container(
                    content=ft.Icon(icon, size=20, color=ft.Colors.WHITE),
                    bgcolor=color, padding=6, border_radius=6,
                ),
                ft.Text(str(value), size=22, weight=ft.FontWeight.BOLD),
                ft.Text(label, size=15, color=ft.Colors.GREY_600),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        else:
            content = ft.Row(
                [
                    ft.Text(str(value), size=26, weight=ft.FontWeight.BOLD, color=color),
                    ft.Text(label, size=13, color=ft.Colors.GREY_600),
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

        super().__init__(
            content=content,
            bgcolor=ft.Colors.WHITE,
            padding=pad_sym(horizontal=16, vertical=12),
            border_radius=8,
            width=width,
            height=60,
            border=bordered(),
            alignment=ft.Alignment.CENTER,
        )


class MarkerCard(ft.Container):

    def __init__(self, marker_id: int, name: str,
                 name_en: Optional[str], formula: Optional[str],
                 association_count: int,
                 is_selected: bool = False,
                 on_click: Optional[Callable] = None,
                 on_edit: Optional[Callable] = None,
                 on_delete: Optional[Callable] = None):
        formula_display = ft.Container(
            content=ft.Text(formula or "—", size=16,
                            color=ft.Colors.GREY_800,
                            text_align=ft.TextAlign.CENTER,
                            style=ft.TextStyle(font_family="Consolas")),
            bgcolor=ft.Colors.GREY_100, padding=10, border_radius=4,
            alignment=ft.Alignment.CENTER, height=60,
        )

        menu_items = []
        if on_edit:
            menu_items.append(ft.PopupMenuItem(
                content=ft.Text("编辑"),
                on_click=lambda e: on_edit(marker_id)))
        if on_delete:
            menu_items.append(ft.PopupMenuItem(
                content=ft.Text("删除"),
                on_click=lambda e: on_delete(marker_id)))

        title_row_controls = [
            ft.Text(name, size=18, weight=ft.FontWeight.W_600, expand=True),
        ]
        if menu_items:
            title_row_controls.append(
                ft.PopupMenuButton(items=menu_items, icon=ft.Icons.MORE_VERT))

        super().__init__(
            content=ft.Column([
                ft.Row(title_row_controls),
                formula_display,
                ft.Text(name_en or "—", size=14, color=ft.Colors.GREY_600),
                ft.Divider(),
                ft.Text(
                    f"关联到 {association_count} 个实体"
                    if association_count > 0 else "未关联",
                    size=13,
                    color=(ft.Colors.GREEN_700 if association_count > 0
                           else ft.Colors.GREY_500),
                ),
            ], spacing=8),
            bgcolor=ft.Colors.BLUE_50 if is_selected else ft.Colors.WHITE,
            padding=20, border_radius=8, ink=True,
            on_click=lambda e: on_click(marker_id) if on_click else None,
            border=selected_border(is_selected),
            data=marker_id,
        )


class EntityDetailCard(ft.Container):

    def __init__(self, title: str, count: int,
                 children: list[ft.Control],
                 add_label: str = "新建",
                 on_add: Optional[Callable] = None):
        header_controls = [
            ft.Text(f"{title} ({count})", size=16, weight=ft.FontWeight.W_500),
        ]
        if on_add:
            header_controls.append(ft.OutlinedButton(
                content=add_label, height=36, icon=ft.Icons.ADD, on_click=on_add,
            ))

        header = ft.Row(header_controls,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        if children:
            inner = ft.Column(
                children, spacing=0, height=360,
                scroll=ft.ScrollMode.AUTO,
            )
        else:
            inner = ft.Text(f"暂无{title}", color=ft.Colors.GREY_500, size=14)
        body = ft.Container(
            content=inner,
            padding=pad_only(top=10),
        )

        super().__init__(
            content=ft.Column([header, body]),
            bgcolor=ft.Colors.WHITE,
            padding=20, border_radius=8, expand=True,
            border=bordered(),
        )
