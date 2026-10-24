import asyncio
import flet as ft
from typing import Optional, Any
from grainprint.domain.entities import (
    EntityType, MarkerCreate, MarkerUpdate, DeleteConfirmation,
)
from grainprint.domain.services import EntityService, MarkerService
from grainprint.domain.events import EventBus, EventType
from grainprint.ui.components import (
    StatCard, MarkerCard, FormDialog, ConfirmDialog, AssociationDialog,
    bordered, selected_border, pad_only, pad_sym,
)


class MarkerView(ft.Column):

    def __init__(self, page: ft.Page):
        super().__init__(expand=True, spacing=12)
        self._page = page
        self.selected_id: Optional[int] = None
        self.view_mode = "list"
        self._detail_id: Optional[int] = None
        self._detail_dialog: Optional[ft.AlertDialog] = None
        self._pending_scroll_id: Optional[int] = None
        self._filter: Optional[str] = None
        self._detail_cache: dict[int, Any] = {}

        self._grid_inner = ft.Row(
            wrap=True, spacing=16, run_spacing=16,
            width=float("inf"),
        )
        self.grid = ft.Column(
            controls=[self._grid_inner],
            scroll=ft.ScrollMode.AUTO, expand=True,
            width=float("inf"),
        )
        self.list = ft.Column(
            scroll=ft.ScrollMode.AUTO, expand=True, spacing=4,
            width=float("inf"),
        )
        self.content = ft.Container(
            content=self.list,
            padding=pad_only(left=20, right=20, bottom=20),
            expand=True,
        )

        self.grid_btn = ft.IconButton(
            icon=ft.Icons.GRID_VIEW, tooltip="网格视图",
            on_click=lambda e: self._switch_view("grid"),
        )
        self.list_btn = ft.IconButton(
            icon=ft.Icons.VIEW_LIST, tooltip="列表视图",
            on_click=lambda e: self._switch_view("list"),
        )
        self._sync_toggle_style()

        self.stats_row = ft.Row(spacing=16)
        self.controls = [
            ft.Container(
                self.stats_row,
                padding=pad_only(left=20, right=20, top=16, bottom=4),
            ),
            self.content,
        ]

        EventBus().subscribe(
            EventType.NAVIGATE_TO_MARKER,
            lambda e: self.select_marker(e.data['marker_id']),
        )

    def refresh(self):
        self._load_stats()
        self._render_all()

    def select_marker(self, marker_id: int):
        self.selected_id = marker_id
        self._pending_scroll_id = marker_id
        self._render_all()

    def filter_by_id(self, marker_id: int):
        """搜索跳转时只展示该标志物，便于确认已定位到目标。"""
        self._filter = None
        self.selected_id = marker_id
        self._pending_scroll_id = marker_id
        self._render([marker_id])

    def search(self, keyword: str):
        self._filter = None
        self._detail_cache.clear()
        if not keyword:
            self.refresh()
            return
        results = EntityService.search(keyword, EntityType.MARKER)
        self._render([r.id for r in results])

    def filter_by_association(self, state: Optional[str]):
        """state: all / linked / unlinked，点统计卡片时过滤列表。"""
        self._filter = state
        self._detail_cache.clear()
        self._render_all()

    def _switch_view(self, mode: str):
        if mode == self.view_mode:
            return
        self.view_mode = mode
        self.content.content = self.grid if mode == "grid" else self.list
        self._sync_toggle_style()
        self._render_all()

    def _sync_toggle_style(self):
        active = (ft.Colors.GREEN_700, ft.Colors.GREEN_50)
        inactive = (ft.Colors.GREY_600, None)
        for btn, mode in [(self.grid_btn, "grid"), (self.list_btn, "list")]:
            btn.icon_color, btn.bgcolor = active if self.view_mode == mode else inactive

    def _load_stats(self):
        stats = EntityService.get_stats()
        total = stats['total']['markers']
        unlinked = stats['markers']['markers_without_association']
        linked = total - unlinked

        toggle = ft.Container(
            content=ft.Row([self.grid_btn, self.list_btn], spacing=2),
            bgcolor=ft.Colors.GREY_100, border_radius=8, padding=2,
            alignment=ft.Alignment.CENTER, height=60,
        )
        new_btn = ft.Container(
            content=ft.FilledButton(
                content="新建标志物", icon=ft.Icons.ADD,
                width=float("inf"), height=40,
                on_click=lambda e: self._create_marker(),
            ),
            expand=True, height=60, alignment=ft.Alignment.CENTER,
        )
        stats_cards = [
            StatCard(
                "标志物总数", total, icon=ft.Icons.CATEGORY,
                color=ft.Colors.GREEN_700,
            ),
            StatCard(
                "已关联", linked, icon=ft.Icons.LINK,
                color=ft.Colors.BLUE_700,
            ),
            StatCard(
                "未关联", unlinked, icon=ft.Icons.LINK_OFF,
                color=ft.Colors.ORANGE_700,
            ),
        ]
        for card, state in zip(stats_cards, ["all", "linked", "unlinked"]):
            card.data = state
            card.ink = True
            card.on_click = lambda e, s=state: self.filter_by_association(s)

        self.stats_row.controls = [
            *stats_cards,
            toggle,
            new_btn,
        ]

    def _render_all(self):
        markers = EntityService.get_children(EntityType.MARKER)
        if self._filter in ("linked", "unlinked"):
            linked_ids = {
                m.id for m in markers
                if self._get_detail_cached(m.id).children
            }
            ids = [
                m.id for m in markers
                if (self._filter == "linked" and m.id in linked_ids)
                or (self._filter == "unlinked" and m.id not in linked_ids)
            ]
        else:
            ids = [m.id for m in markers]
        self._render(ids)

    def _render(self, marker_ids: list[int]):
        markers = {m.id: m for m in EntityService.get_children(EntityType.MARKER)}
        rows = [
            (mid, markers.get(mid), self._get_detail_cached(mid))
            for mid in marker_ids
        ]

        if self.view_mode == "grid":
            self._render_grid(rows)
        else:
            self._render_list(rows)

        self._page.update()
        self._try_scroll(marker_ids)

    def _get_detail_cached(self, marker_id: int):
        detail = self._detail_cache.get(marker_id)
        if detail is None:
            detail = EntityService.get_detail(EntityType.MARKER, marker_id)
            self._detail_cache[marker_id] = detail
        return detail

    def _render_grid(self, rows):
        self._grid_inner.controls.clear()
        for mid, marker, detail in rows:
            card = MarkerCard(
                marker_id=mid, name=detail.name, name_en=detail.name_en,
                formula=marker.structure_formula if marker else None,
                association_count=len(detail.children),
                is_selected=mid == self.selected_id,
                on_click=self._open_detail,
                on_edit=self._edit_marker,
                on_delete=self._delete_marker,
            )
            card.width = 360
            card.key = ft.ScrollKey(str(mid))
            self._grid_inner.controls.append(card)

    def _render_list(self, rows):
        self.list.controls.clear()
        self.list.controls.append(self._list_header())
        for idx, (mid, marker, detail) in enumerate(rows, start=1):
            self.list.controls.append(self._list_row(idx, mid, marker, detail))

    def _list_header(self) -> ft.Container:
        # 需求 5：左边增加“序号”；需求 7：备注分列。
        return ft.Container(
            content=ft.Row([
                ft.Text("序号", weight=ft.FontWeight.W_500, expand=1),
                ft.Text("名称", weight=ft.FontWeight.W_500, expand=2),
                ft.Text("英文名", weight=ft.FontWeight.W_500, expand=2),
                ft.Text("结构式", weight=ft.FontWeight.W_500, expand=3),
                ft.Text("备注1", weight=ft.FontWeight.W_500, expand=2),
                ft.Text("备注2", weight=ft.FontWeight.W_500, expand=2),
                ft.Text("关联", weight=ft.FontWeight.W_500, expand=1),
                ft.Container(width=90),
            ]),
            padding=pad_sym(horizontal=12, vertical=8),
            bgcolor=ft.Colors.GREY_100, border_radius=4,
            width=float("inf"),
        )

    def _list_row(self, seq: int, mid: int, marker, detail) -> ft.Container:
        is_selected = mid == self.selected_id
        formula = (marker.structure_formula if marker and marker.structure_formula
                   else "—")
        n = len(detail.children)
        # 需求 7：标志物列表增加 备注1 / 备注2 列。
        note1 = note2 = "—"
        full = self._get_detail_cached(mid)
        notes = []
        notes2 = []
        for child in full.children:
            text = child.association_info or ""
            if "备注:" in text:
                part = text.split("备注:", 1)[-1].split(" • ")[0].strip()
                notes.append(part)
            if "备注2:" in text:
                part = text.split("备注2:", 1)[-1].split(" • ")[0].strip()
                notes2.append(part)
        if notes:
            note1 = notes[0]
        if notes2:
            note2 = notes2[0]

        row = ft.Container(
            content=ft.Row([
                ft.Text(str(seq), size=13, color=ft.Colors.GREY_600, expand=1),
                ft.Text(detail.name, size=14, weight=ft.FontWeight.W_500, expand=2),
                ft.Text(detail.name_en or "—", size=13, color=ft.Colors.GREY_700, expand=2),
                ft.Text(formula, size=13,
                        style=ft.TextStyle(font_family="Consolas"), expand=3),
                ft.Text(note1, size=12, expand=2, max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        color=ft.Colors.GREY_700),
                ft.Text(note2, size=12, expand=2, max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        color=ft.Colors.GREY_700),
                ft.Text(
                    f"{n} 个" if n else "未关联", size=13, expand=1,
                    color=ft.Colors.GREEN_700 if n else ft.Colors.GREY_500,
                ),
                ft.Row([
                    ft.IconButton(
                        ft.Icons.EDIT_OUTLINED, icon_size=16, tooltip="编辑",
                        on_click=lambda e, x=mid: self._edit_marker(x),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE, icon_size=16,
                        icon_color=ft.Colors.RED, tooltip="删除",
                        on_click=lambda e, x=mid: self._delete_marker(x),
                    ),
                ], spacing=0, width=90),
            ]),
            padding=pad_sym(horizontal=12, vertical=6),
            bgcolor=ft.Colors.BLUE_50 if is_selected else ft.Colors.WHITE,
            border=selected_border(is_selected),
            border_radius=4, ink=True,
            on_click=lambda e, x=mid: self._open_detail(x),
            data=mid,
            width=float("inf"),
        )
        row.key = ft.ScrollKey(str(mid))
        return row

    def _try_scroll(self, ids: list[int]):
        target_id = self._pending_scroll_id
        if target_id is None or target_id not in ids:
            return

        target = self.grid if self.view_mode == "grid" else self.list
        sk = ft.ScrollKey(str(target_id))

        async def do_scroll():
            await asyncio.sleep(0.35)
            await target.scroll_to(scroll_key=sk, duration=600)
            self._pending_scroll_id = None

        self._page.run_task(do_scroll)

    def _get_marker(self, marker_id: int) -> Optional[Any]:
        return next(
            (m for m in EntityService.get_children(EntityType.MARKER)
             if m.id == marker_id), None,
        )

    def _find_association(self, entity_type: str, entity_id: int, marker_id: int):
        assocs = MarkerService.get_associations_by_entity(
            EntityType(entity_type), entity_id)
        return next((a for a in assocs if a.marker_id == marker_id), None)

    def _create_marker(self):
        def on_submit(data: MarkerCreate):
            EntityService.create(EntityType.MARKER, data)
            self._detail_cache.clear()
            self.refresh()

        FormDialog(page=self._page, title="新建标志物",
                   model_class=MarkerCreate, on_submit=on_submit).show()

    def _edit_marker(self, marker_id: int):
        marker = self._get_marker(marker_id)
        if not marker:
            return

        def on_submit(data: MarkerUpdate):
            EntityService.update(EntityType.MARKER, marker_id, data)
            self._detail_cache.pop(marker_id, None)
            self.refresh()

        FormDialog(
            page=self._page, title="编辑标志物",
            model_class=MarkerUpdate, on_submit=on_submit,
            initial_data={
                'name': marker.name,
                'name_en': marker.name_en,
                'structure_formula': marker.structure_formula,
            },
        ).show()

    def _delete_marker(self, marker_id: int):
        confirmation = EntityService.get_delete_confirmation(
            EntityType.MARKER, marker_id)

        def on_confirm():
            EntityService.delete(EntityType.MARKER, marker_id)
            self._detail_cache.pop(marker_id, None)
            if self.selected_id == marker_id:
                self.selected_id = None
            self.refresh()

        ConfirmDialog(page=self._page, confirmation=confirmation,
                      on_confirm=on_confirm).show()

    def _open_detail(self, marker_id: int):
        self._detail_id = marker_id
        self._render_detail()

    def _render_detail(self):
        mid = self._detail_id
        detail = EntityService.get_detail(EntityType.MARKER, mid)
        marker = self._get_marker(mid)

        body = ft.Container(
            content=ft.Column([
                ft.Text(f"英文名: {detail.name_en or '—'}", size=14),
                ft.Text("结构式:", size=14, weight=ft.FontWeight.W_500),
                ft.Container(
                    content=ft.Text(
                        marker.structure_formula if marker else "—",
                        size=20, text_align=ft.TextAlign.CENTER,
                        style=ft.TextStyle(font_family="Consolas"),
                    ),
                    bgcolor=ft.Colors.GREY_100, padding=20,
                    border_radius=4, alignment=ft.Alignment.CENTER,
                ),
                ft.Divider(),
                ft.Row([
                    ft.Text(f"关联实体 ({len(detail.children)})",
                            weight=ft.FontWeight.W_500),
                    ft.OutlinedButton(
                        content="添加关联", icon=ft.Icons.ADD, height=32,
                        on_click=lambda e: self._add_association(),
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(
                    content=self._build_assoc_list(mid, detail.children),
                    border=bordered(1, ft.Colors.GREY_300),
                    border_radius=4,
                ),
            ], spacing=10),
            width=550,
        )

        if self._detail_dialog:
            self._page.pop_dialog()

        self._detail_dialog = ft.AlertDialog(
            title=ft.Text(detail.name),
            content=body,
            actions=[
                ft.TextButton(content="关闭", on_click=self._close_detail),
            ],
        )
        self._page.show_dialog(self._detail_dialog)

    def _close_detail(self, e):
        self._page.pop_dialog()
        self._detail_dialog = None

    def _build_assoc_list(self, marker_id: int, children: list) -> ft.Column:
        col = ft.Column(spacing=8, height=300, scroll=ft.ScrollMode.AUTO)
        if not children:
            col.controls.append(ft.Container(
                content=ft.Text("暂无关联", color=ft.Colors.GREY_500),
                padding=20, alignment=ft.Alignment.CENTER,
            ))
            return col
        for child in children:
            col.controls.append(self._assoc_item(marker_id, child))
        return col

    def _assoc_item(self, marker_id: int, child) -> ft.Container:
        info = getattr(child, 'association_info', None) or "暂无详细信息"
        # 需求 6：来源、筛选、途径、备注各占一行，字号与关联实体标题一致。
        info_keys = ['来源', '筛选', '途径', '文献', '备注2', '备注']
        info_lines: list[ft.Control] = [ft.Text(' > '.join(child.path),
                                               size=14,
                                               weight=ft.FontWeight.W_500)]
        for key in info_keys:
            if f"{key}:" in info:
                segment = info.split(f"{key}:", 1)[1]
                if " • " in segment:
                    segment = segment.split(" • ")[0]
                info_lines.append(ft.Text(
                    f"{key}: {segment.strip()}", size=14,
                    color=ft.Colors.GREY_700, expand=True,
                ))
        return ft.Container(
            content=ft.Row([
                ft.Column([
                    *info_lines,
                ], spacing=6, expand=True),
                ft.Row([
                    ft.IconButton(
                        ft.Icons.EDIT_OUTLINED, icon_size=18,
                        icon_color=ft.Colors.BLUE, tooltip="编辑关联",
                        on_click=lambda e, t=child.type, i=child.id:
                            self._edit_association(t, i),
                    ),
                    ft.IconButton(
                        ft.Icons.OPEN_IN_NEW, icon_size=18,
                        icon_color=ft.Colors.GREEN, tooltip="跳转到实体",
                        on_click=lambda e, t=child.type, i=child.id:
                            self._navigate_entity(t, i),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE, icon_size=18,
                        icon_color=ft.Colors.RED, tooltip="删除关联",
                        on_click=lambda e, t=child.type, i=child.id:
                            self._delete_association(marker_id, t, i),
                    ),
                ], spacing=0),
            ]),
            padding=10, border_radius=4, bgcolor=ft.Colors.GREY_100,
        )

    def _add_association(self):
        AssociationDialog.open_for_create(
            page=self._page,
            marker_id=self._detail_id,
            on_done=lambda: self._invalidate_detail(self._detail_id),
        )

    def _edit_association(self, entity_type: str, entity_id: int):
        association = self._find_association(entity_type, entity_id, self._detail_id)
        if not association:
            return
        AssociationDialog.open_for_edit(
            page=self._page,
            association=association,
            entity=(entity_type, entity_id),
            on_done=lambda: self._invalidate_detail(self._detail_id),
        )

    def _delete_association(self, marker_id: int, entity_type: str, entity_id: int):
        association = self._find_association(entity_type, entity_id, marker_id)
        if not association:
            return

        def on_confirm():
            EntityService.delete(EntityType.ASSOCIATION, association.id)
            self._invalidate_detail(marker_id)

        ConfirmDialog(
            page=self._page,
            confirmation=DeleteConfirmation(
                entity_type=EntityType.ASSOCIATION, entity_id=association.id,
                entity_name="标志物关联", impact={},
            ),
            on_confirm=on_confirm,
        ).show()

    def _invalidate_detail(self, marker_id: int):
        self._detail_cache.pop(marker_id, None)
        self._render_detail()

    def _navigate_entity(self, entity_type: str, entity_id: int):
        if self._detail_dialog:
            self._page.pop_dialog()
            self._detail_dialog = None
        EventBus().emit_navigate_to_entity(entity_type, entity_id)
