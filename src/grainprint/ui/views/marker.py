import asyncio
from typing import Any, Optional

import flet as ft

from grainprint.domain.entities import EntityType, MarkerCreate, MarkerUpdate, DeleteConfirmation
from grainprint.domain.services import EntityService, MarkerService
from grainprint.domain.events import EventBus, EventType
from grainprint.ui.components import (
    StatCard, MarkerCard, FormDialog, ConfirmDialog, AssociationDialog,
    bordered, selected_border, pad_only, pad_sym,
)


MATERIAL_TYPES = ("标志物", "特征物质")
MATERIAL_SOURCES = ("自行筛选", "文献报道")


class MarkerView(ft.Column):
    """Material library. Classification is stored on Marker.notes/notes2."""

    def __init__(self, page: ft.Page):
        super().__init__(expand=True, spacing=12)
        self._page = page
        self.selected_id: Optional[int] = None
        self.view_mode = "list"
        self._detail_id: Optional[int] = None
        self._detail_dialog: Optional[ft.AlertDialog] = None
        self._pending_scroll_id: Optional[int] = None
        self._association_filter: Optional[str] = None
        self._material_filter: Optional[str] = None
        self._source_filter: Optional[str] = None
        self._summaries: list[dict[str, Any]] = []

        self._grid_inner = ft.Row(wrap=True, spacing=16, run_spacing=16, width=float("inf"))
        self.grid = ft.Column(controls=[self._grid_inner], scroll=ft.ScrollMode.AUTO, expand=True, width=float("inf"), visible=False)
        self.list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=4, width=float("inf"), visible=True)
        self.grid_btn = ft.IconButton(icon=ft.Icons.GRID_VIEW, tooltip="网格视图", on_click=lambda e: self._switch_view("grid"))
        self.list_btn = ft.IconButton(icon=ft.Icons.VIEW_LIST, tooltip="列表视图", on_click=lambda e: self._switch_view("list"))
        self._sync_toggle_style()
        self.view_toggle = ft.Container(
            ft.Row([self.grid_btn, self.list_btn], spacing=2),
            bgcolor=ft.Colors.GREY_100, border_radius=8, padding=2, height=60,
        )
        self.type_filter = ft.Dropdown(
            label="备注1：物质类型", width=180, dense=True,
            options=[ft.DropdownOption(key="", text="全部类型")],
            on_select=self._on_type_filter,
        )
        self.source_filter = ft.Dropdown(
            label="备注2：来源", width=180, dense=True,
            options=[ft.DropdownOption(key="", text="全部来源")],
            on_select=self._on_source_filter,
        )
        self.stats_row = ft.Row(spacing=12, wrap=True)
        self.new_btn = ft.Container(
            ft.FilledButton(content="新建物质", icon=ft.Icons.ADD, height=40, on_click=lambda e: self._create_marker()),
            alignment=ft.Alignment.CENTER,
        )
        self.controls = [
            ft.Container(
                ft.Row([
                    ft.Text("标志物及特征物质库", size=24, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    self.new_btn,
                ]),
                padding=pad_only(left=20, right=20, top=16),
            ),
            ft.Container(self.stats_row, padding=pad_only(left=20, right=20, bottom=4)),
            ft.Container(
                ft.Row([
                    self.type_filter,
                    self.source_filter,
                    ft.Container(expand=True),
                    self.view_toggle,
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=pad_only(left=20, right=20, bottom=4),
            ),
            self.list,
            self.grid,
        ]
        EventBus().subscribe(EventType.NAVIGATE_TO_MARKER, lambda e: self.select_marker(e.data['marker_id']))

    def refresh(self):
        self._summaries = EntityService.get_marker_summaries()
        self._refresh_filter_options()
        self._load_stats()
        self._render_all()

    def _refresh_filter_options(self):
        notes1 = sorted({m.get('notes') or "" for m in self._summaries if m.get('notes')})
        notes2 = sorted({m.get('notes2') or "" for m in self._summaries if m.get('notes2')})
        self.type_filter.options = [ft.DropdownOption(key="", text="全部类型")] + [
            ft.DropdownOption(key=x, text=x) for x in notes1
        ]
        self.source_filter.options = [ft.DropdownOption(key="", text="全部来源")] + [
            ft.DropdownOption(key=x, text=x) for x in notes2
        ]
        self.type_filter.value = self._material_filter if self._material_filter in notes1 else ""
        self.source_filter.value = self._source_filter if self._source_filter in notes2 else ""

    def select_marker(self, marker_id: int):
        self.selected_id = marker_id
        self._pending_scroll_id = marker_id
        self._render_all()

    def filter_by_id(self, marker_id: int):
        self._association_filter = None
        self.selected_id = marker_id
        self._pending_scroll_id = marker_id
        self._render([marker_id])

    def search(self, keyword: str):
        self._association_filter = None
        if not keyword:
            self.refresh()
            return
        results = EntityService.search(keyword, EntityType.MARKER)
        self._render([r.id for r in results])

    def filter_by_association(self, state: Optional[str]):
        self._association_filter = state
        self._render_all()

    def _on_type_filter(self, e):
        self._material_filter = e.control.value or None
        self._render_all()

    def _on_source_filter(self, e):
        self._source_filter = e.control.value or None
        self._render_all()

    def _switch_view(self, mode: str):
        if mode == self.view_mode:
            return
        self.view_mode = mode
        self.grid.visible = mode == "grid"
        self.list.visible = mode != "grid"
        self._sync_toggle_style()
        self._render_all()

    def _sync_toggle_style(self):
        active, inactive = (ft.Colors.GREEN_700, ft.Colors.GREEN_50), (ft.Colors.GREY_600, None)
        for btn, mode in ((self.grid_btn, "grid"), (self.list_btn, "list")):
            btn.icon_color, btn.bgcolor = active if self.view_mode == mode else inactive

    def _load_stats(self):
        stats = EntityService.get_stats()
        total = stats['total']['markers']
        types = stats['total']['material_types']
        unlinked = stats['markers']['markers_without_association']
        linked = total - unlinked
        cards = [
            StatCard("物质总数", total, ft.Icons.CATEGORY, ft.Colors.GREEN_700, width=170),
            StatCard("标志物数", types['标志物'], ft.Icons.SCIENCE, ft.Colors.BLUE_700, width=170),
            StatCard("特征物质数", types['特征物质'], ft.Icons.BIOTECH, ft.Colors.PURPLE_700, width=170),
            StatCard("未分类", types['未分类'], ft.Icons.HELP_OUTLINE, ft.Colors.AMBER_700, width=170),
            StatCard("已关联", linked, ft.Icons.LINK, ft.Colors.TEAL_700, width=170),
            StatCard("未关联", unlinked, ft.Icons.LINK_OFF, ft.Colors.ORANGE_700, width=170),
        ]
        for card, state in zip((cards[0], cards[3], cards[4], cards[5]), ("all", "unclassified", "linked", "unlinked")):
            card.ink, card.on_click = True, (lambda e, s=state: self.filter_by_association(s))
        self.stats_row.controls = cards

    def _visible_summaries(self) -> list[dict[str, Any]]:
        ret = self._summaries
        if self._association_filter == "linked":
            ret = [m for m in ret if m['association_count']]
        elif self._association_filter == "unlinked":
            ret = [m for m in ret if not m['association_count']]
        elif self._association_filter == "unclassified":
            ret = [m for m in ret if m['material_type'] not in ("标志物", "特征物质")]
        if self._material_filter:
            ret = [m for m in ret if m.get('notes') == self._material_filter]
        if self._source_filter:
            ret = [m for m in ret if m.get('notes2') == self._source_filter]
        return ret

    def _render_all(self):
        if not self._summaries:
            self._summaries = EntityService.get_marker_summaries()
        self._render([m['id'] for m in self._visible_summaries()])

    def _render(self, marker_ids: list[int]):
        by_id = {m['id']: m for m in self._summaries}
        rows = [(mid, by_id.get(mid)) for mid in marker_ids if mid in by_id]
        if self.view_mode == "grid":
            self._render_grid(rows)
        else:
            self._render_list(rows)
        self._page.update()
        self._try_scroll(marker_ids)

    def _render_grid(self, rows):
        self._grid_inner.controls.clear()
        for mid, marker in rows:
            card = MarkerCard(mid, marker['name'], marker['name_en'], marker['structure_formula'], marker['association_count'], mid == self.selected_id, self._open_detail, self._edit_marker, self._delete_marker)
            card.width, card.key = 360, ft.ScrollKey(str(mid))
            self._grid_inner.controls.append(card)

    def _render_list(self, rows):
        self.list.controls.clear()
        self.list.controls.append(self._list_header())
        for seq, (mid, marker) in enumerate(rows, 1):
            self.list.controls.append(self._list_row(seq, mid, marker))

    def _list_header(self):
        return ft.Container(ft.Row([
            ft.Text("序号", weight=ft.FontWeight.W_500, expand=1),
            ft.Text("名称", weight=ft.FontWeight.W_500, expand=2),
            ft.Text("英文名", weight=ft.FontWeight.W_500, expand=2),
            ft.Text("结构式", weight=ft.FontWeight.W_500, expand=3),
            ft.Text("备注1 / 类型", weight=ft.FontWeight.W_500, expand=2),
            ft.Text("备注2 / 来源", weight=ft.FontWeight.W_500, expand=2),
            ft.Text("关联", weight=ft.FontWeight.W_500, expand=1), ft.Container(width=90),
        ]), padding=pad_sym(horizontal=12, vertical=8), bgcolor=ft.Colors.GREY_100, border_radius=4, width=float("inf"))

    def _list_row(self, seq: int, mid: int, marker: dict[str, Any]):
        return ft.Container(ft.Row([
            ft.Text(str(seq), size=13, color=ft.Colors.GREY_600, expand=1),
            ft.Text(marker['name'], size=14, weight=ft.FontWeight.W_500, expand=2),
            ft.Text(marker['name_en'] or "—", size=13, color=ft.Colors.GREY_700, expand=2),
            ft.Text(marker['structure_formula'] or "—", size=13, expand=3),
            ft.Text(marker['notes'] or "未分类", size=12, expand=2, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(marker['notes2'] or "—", size=12, expand=2, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(str(marker['association_count']), size=13, expand=1),
            ft.Row([ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=18, tooltip="编辑物质", on_click=lambda e, x=mid: self._edit_marker(x)), ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=ft.Colors.RED, tooltip="删除物质", on_click=lambda e, x=mid: self._delete_marker(x))], spacing=0),
        ]), padding=pad_sym(horizontal=12, vertical=8), bgcolor=ft.Colors.BLUE_50 if mid == self.selected_id else ft.Colors.WHITE, border=selected_border(mid == self.selected_id), border_radius=4, on_click=lambda e, x=mid: self._open_detail(x), ink=True)

    def _try_scroll(self, ids: list[int]):
        if self._pending_scroll_id is None or self._pending_scroll_id not in ids:
            return
        target = self._pending_scroll_id
        self._pending_scroll_id = None
        async def scroll():
            await asyncio.sleep(0.05)
            try:
                await (self.grid if self.view_mode == "grid" else self.list).scroll_to(key=ft.ScrollKey(str(target)), duration=300)
            except Exception:
                pass
        self._page.run_task(scroll)

    def _get_marker(self, marker_id: int):
        return next((m for m in EntityService.get_children(EntityType.MARKER) if m.id == marker_id), None)

    def _find_association(self, entity_type: str, entity_id: int, marker_id: int):
        return next((a for a in MarkerService.get_associations_by_entity(EntityType(entity_type), entity_id) if a.marker_id == marker_id), None)

    def _create_marker(self):
        def done(data):
            EntityService.create(EntityType.MARKER, data)
            self.refresh()
        FormDialog(self._page, "新建物质", MarkerCreate, done).show()

    def _edit_marker(self, marker_id: int):
        marker = self._get_marker(marker_id)
        if not marker:
            return
        initial = {"name": marker.name, "name_en": marker.name_en, "structure_formula": marker.structure_formula, "notes": marker.notes, "notes2": marker.notes2}
        def done(data):
            EntityService.update(EntityType.MARKER, marker_id, data)
            self.refresh()
        FormDialog(self._page, "编辑物质", MarkerUpdate, done, initial).show()

    def _delete_marker(self, marker_id: int):
        confirmation = EntityService.get_delete_confirmation(EntityType.MARKER, marker_id)
        def done():
            EntityService.delete(EntityType.MARKER, marker_id)
            if self.selected_id == marker_id:
                self.selected_id = None
            self.refresh()
        ConfirmDialog(self._page, confirmation, done).show()

    def _open_detail(self, marker_id: int):
        self._detail_id = marker_id
        self._render_detail()

    def _render_detail(self):
        mid = self._detail_id
        detail = EntityService.get_detail(EntityType.MARKER, mid)
        marker = self._get_marker(mid)
        summary = next((m for m in self._summaries if m['id'] == mid), {})
        body = ft.Container(ft.Column([
            ft.Text(detail.name_en or "—", color=ft.Colors.GREY_600),
            ft.Text(f"结构式：{marker.structure_formula or '—'}"),
            ft.Text(f"备注1 / 物质类型：{marker.notes or '未分类'}"),
            ft.Text(f"备注2 / 来源：{marker.notes2 or '—'}"),
            ft.Divider(),
            ft.Row([ft.Text(f"关联对象（{len(detail.children)}）", size=16, weight=ft.FontWeight.W_500), ft.OutlinedButton(content="添加关联", icon=ft.Icons.ADD, height=32, on_click=lambda e: self._add_association())], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self._build_assoc_list(mid, detail.children),
        ], spacing=10), width=620)
        if self._detail_dialog:
            self._page.pop_dialog()
        self._detail_dialog = ft.AlertDialog(title=ft.Text(detail.name), content=body, actions=[ft.TextButton(content="关闭", on_click=self._close_detail)])
        self._page.show_dialog(self._detail_dialog)

    def _close_detail(self, e):
        self._page.pop_dialog(); self._detail_dialog = None

    def _build_assoc_list(self, marker_id: int, children: list):
        column = ft.Column(spacing=8, height=300, scroll=ft.ScrollMode.AUTO)
        if not children:
            column.controls.append(ft.Container(ft.Text("暂无关联", color=ft.Colors.GREY_500), padding=20, alignment=ft.Alignment.CENTER))
        for child in children:
            column.controls.append(self._assoc_item(marker_id, child))
        return column

    def _assoc_item(self, marker_id: int, child):
        return ft.Container(ft.Row([
            ft.Text(" > ".join(child.path), weight=ft.FontWeight.W_500, expand=True),
            ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=18, tooltip="编辑关联", on_click=lambda e, t=child.type, i=child.id: self._edit_association(t, i)),
            ft.IconButton(ft.Icons.OPEN_IN_NEW, icon_size=18, tooltip="跳转到实体", on_click=lambda e, t=child.type, i=child.id: self._navigate_entity(t, i)),
            ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=ft.Colors.RED, tooltip="删除关联", on_click=lambda e, t=child.type, i=child.id: self._delete_association(marker_id, t, i)),
        ]), padding=10, border_radius=4, bgcolor=ft.Colors.GREY_100)

    def _add_association(self):
        AssociationDialog.open_for_create(self._page, on_done=self._after_association_change, marker_id=self._detail_id)

    def _edit_association(self, entity_type: str, entity_id: int):
        association = self._find_association(entity_type, entity_id, self._detail_id)
        if association:
            AssociationDialog.open_for_edit(self._page, association, (entity_type, entity_id), self._after_association_change)

    def _after_association_change(self):
        self.refresh()
        self._render_detail()

    def _delete_association(self, marker_id: int, entity_type: str, entity_id: int):
        association = self._find_association(entity_type, entity_id, marker_id)
        if not association:
            return
        ConfirmDialog(self._page, DeleteConfirmation(entity_type=EntityType.ASSOCIATION, entity_id=association.id, entity_name="物质关联", impact={}), lambda: self._delete_association_confirmed(association.id)).show()

    def _delete_association_confirmed(self, association_id: int):
        EntityService.delete(EntityType.ASSOCIATION, association_id)
        self._after_association_change()

    def _navigate_entity(self, entity_type: str, entity_id: int):
        if self._detail_dialog:
            self._page.pop_dialog(); self._detail_dialog = None
        EventBus().emit_navigate_to_entity(entity_type, entity_id)
