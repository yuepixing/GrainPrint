import re
import flet as ft
from typing import Optional, Set
from grainprint.domain.entities import (
    EntityType, CropCreate, CropUpdate,
    SubspeciesCreate, SubspeciesUpdate,
    VarietyCreate, VarietyUpdate,
    DeleteConfirmation,
)
from grainprint.domain.services import EntityService, MarkerService
from grainprint.domain.events import EventBus, EventType, Event
from grainprint.ui.components import (
    FormDialog, ConfirmDialog, EntityDetailCard, AssociationDialog,
    bottom_border, right_border, pad_only, pad_sym,
)


CHILD_TYPE_NAME = {EntityType.CROP: "品类", EntityType.SUBSPECIES: "品种"}

ENTITY_UPDATE_MODEL = {
    EntityType.CROP: CropUpdate,
    EntityType.SUBSPECIES: SubspeciesUpdate,
    EntityType.VARIETY: VarietyUpdate,
}

TREENODE_SELECTED_COLOR = {
    EntityType.CROP: ft.Colors.GREEN_50,
    EntityType.SUBSPECIES: ft.Colors.BLUE_50,
    EntityType.VARIETY: ft.Colors.PURPLE_50,
}


class TreeNode(ft.Container):

    def __init__(self, entity_id: int, entity_type: EntityType, name: str,
                 count: int = 0, level: int = 0,
                 is_expanded: bool = False, is_selected: bool = False,
                 on_click: Optional[callable] = None,
                 on_toggle: Optional[callable] = None,
                 trailing: Optional[ft.Control] = None):
        indent = level * 20
        icon = ft.Icons.ARROW_DROP_DOWN if is_expanded else ft.Icons.ARROW_RIGHT
        if entity_type == EntityType.VARIETY:
            icon = None

        row_items: list[ft.Control] = []
        if icon:
            row_items.append(ft.Icon(icon, size=20))
        row_items.append(ft.Text(name, size=14 - level, weight=ft.FontWeight.W_500))
        if count > 0:
            row_items.append(ft.Text(f"({count})", size=11, color=ft.Colors.GREY_600))
        if trailing:
            row_items.append(trailing)

        super().__init__(
            content=ft.Row(row_items, spacing=4),
            padding=pad_only(left=indent + 8, top=8 - level,
                             bottom=8 - level, right=8),
            bgcolor=TREENODE_SELECTED_COLOR.get(entity_type) if is_selected else None,
            on_click=lambda e: (
                on_click(entity_type, entity_id) if on_click else None,
                on_toggle(f"{entity_type}_{entity_id}") if on_toggle and icon else None,
            ),
            ink=True, width=float("inf"),
        )


class CropView(ft.Row):

    def __init__(self, page: ft.Page):
        super().__init__(spacing=0, expand=True)
        self._page = page
        self.selected_id: Optional[int] = None
        self.selected_type: Optional[EntityType] = None
        self.expanded: Set[str] = set()

        self.tree = ft.ReorderableListView(
            controls=[],
            show_default_drag_handles=False,
            spacing=0,
            expand=True,
            width=float("inf"),
            on_reorder=self._on_reorder,
        )
        self.detail_panel = ft.Container(
            expand=True, padding=20,
            content=ft.Column(
                [ft.Text("选择一个项目查看详情", size=16,
                         color=ft.Colors.GREY_500)],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        )

        self.controls = [self._build_sidebar(), self.detail_panel]
        EventBus().subscribe(EventType.NAVIGATE_TO_ENTITY, self._on_navigate)

    def _build_sidebar(self) -> ft.Container:
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.FilledButton(
                        content="新建粮食", icon=ft.Icons.ADD,
                        width=float("inf"), height=40,
                        on_click=self._create_crop,
                    ),
                    padding=10, border=bottom_border(ft.Colors.GREY_300),
                ),
                self.tree,
            ], spacing=0, expand=True),
            width=250, bgcolor=ft.Colors.WHITE,
            border=right_border(ft.Colors.GREY_300),
        )

    def refresh(self):
        self._load_tree()
        if self.selected_id and self.selected_type:
            self._show_detail(self.selected_type, self.selected_id)

    def select_entity(self, entity_type: str, entity_id: int):
        self.selected_type = EntityType(entity_type)
        self.selected_id = entity_id
        self._ensure_expanded(entity_type, entity_id)
        self._load_tree()
        self._show_detail(self.selected_type, entity_id)

    def search(self, keyword: str):
        if not keyword:
            self._load_tree()
            return
        self.tree.controls.clear()
        for etype in (EntityType.CROP, EntityType.SUBSPECIES, EntityType.VARIETY):
            for result in EntityService.search(keyword, etype):
                self.tree.controls.append(self._search_item(result))
        self._update_page()

    def _update_page(self):
        if self._page:
            self._page.update()

    def _on_navigate(self, event: Event):
        etype = event.data['entity_type']
        if etype in ('crop', 'subspecies', 'variety'):
            self.select_entity(etype, event.data['entity_id'])

    def _search_item(self, result) -> ft.Container:
        is_selected = (self.selected_id == result.id
                       and self.selected_type == EntityType(result.type))
        return ft.Container(
            content=ft.Column([
                ft.Text(result.name, size=14, weight=ft.FontWeight.W_500),
                ft.Text(' > '.join(result.path), size=12, color=ft.Colors.GREY_600),
            ], spacing=2),
            padding=12,
            bgcolor=ft.Colors.BLUE_50 if is_selected else None,
            on_click=lambda e, r=result: self.select_entity(r.type, r.id),
            ink=True, width=float("inf"),
        )

    def _toggle_expand(self, key: str):
        (self.expanded.discard if key in self.expanded else self.expanded.add)(key)
        self._load_tree()

    def _ensure_expanded(self, entity_type: str, entity_id: int):
        if entity_type == 'variety':
            varieties = EntityService.get_children(EntityType.VARIETY)
            var = next((v for v in varieties if v.id == entity_id), None)
            if not var:
                return
            self.expanded.add(f"subspecies_{var.subspecies_id}")
            subs = EntityService.get_children(EntityType.SUBSPECIES)
            sub = next((s for s in subs if s.id == var.subspecies_id), None)
            if sub:
                self.expanded.add(f"crop_{sub.crop_id}")
        elif entity_type == 'subspecies':
            subs = EntityService.get_children(EntityType.SUBSPECIES)
            sub = next((s for s in subs if s.id == entity_id), None)
            if sub:
                self.expanded.add(f"crop_{sub.crop_id}")

    def _load_tree(self):
        self.tree.controls.clear()
        for crop in EntityService.get_children(EntityType.CROP):
            self._append_crop(crop)
        self._update_page()

    def _drag_handle(self) -> ft.Control:
        return ft.ReorderableDragHandle(
            content=ft.Icon(
                ft.Icons.DRAG_INDICATOR, size=18,
                color=ft.Colors.GREY_500,
            ),
            tooltip="拖动调整顺序",
        )

    def _on_reorder(self, e):
        ordered: dict[tuple[str, Optional[int]], list[int]] = {}
        for row in self.tree.controls:
            key = getattr(row, 'data', None)
            if not key or len(key) != 3:
                continue
            entity_type, entity_id, parent_id = key
            gkey = (entity_type, parent_id)
            ordered.setdefault(gkey, []).append(entity_id)

        for (entity_type, parent_id), ids in ordered.items():
            EntityService.reorder(
                EntityType(entity_type), ids, parent_id=parent_id,
            )
        self._update_page()

    def _append_crop(self, crop):
        key = f"crop_{crop.id}"
        expanded = key in self.expanded
        subs = EntityService.get_children(EntityType.SUBSPECIES, crop.id)

        self.tree.controls.append(TreeNode(
            entity_id=crop.id, entity_type=EntityType.CROP,
            name=crop.name, count=len(subs), is_expanded=expanded,
            is_selected=(self.selected_id == crop.id
                         and self.selected_type == EntityType.CROP),
            on_click=self._select_from_tree, on_toggle=self._toggle_expand,
            trailing=self._drag_handle(),
        ))
        self.tree.controls[-1].data = ('crop', crop.id, None)

        if expanded:
            for sub in subs:
                self._append_sub(sub)

    def _append_sub(self, sub):
        key = f"subspecies_{sub.id}"
        expanded = key in self.expanded
        varieties = EntityService.get_children(EntityType.VARIETY, sub.id)

        self.tree.controls.append(TreeNode(
            entity_id=sub.id, entity_type=EntityType.SUBSPECIES,
            name=sub.name, count=len(varieties), level=1, is_expanded=expanded,
            is_selected=(self.selected_id == sub.id
                         and self.selected_type == EntityType.SUBSPECIES),
            on_click=self._select_from_tree, on_toggle=self._toggle_expand,
            trailing=self._drag_handle(),
        ))
        self.tree.controls[-1].data = ('subspecies', sub.id, sub.crop_id)

        if expanded:
            for var in varieties:
                self.tree.controls.append(TreeNode(
                    entity_id=var.id, entity_type=EntityType.VARIETY,
                    name=var.name, level=2,
                    is_selected=(self.selected_id == var.id
                                 and self.selected_type == EntityType.VARIETY),
                    on_click=self._select_from_tree,
                ))

    def _select_from_tree(self, entity_type: EntityType, entity_id: int):
        self.selected_type = entity_type
        self.selected_id = entity_id
        self._load_tree()
        self._show_detail(entity_type, entity_id)

    def _show_detail(self, entity_type: EntityType, entity_id: int):
        detail = EntityService.get_detail(entity_type, entity_id)

        header = self._build_header(detail, entity_type, entity_id)
        marker_card = EntityDetailCard(
            title="关联标志物",
            count=len(detail.markers),
            children=[self._build_marker_item(m, entity_type, entity_id) for m in detail.markers],
            add_label="关联",
            on_add=lambda e: self._add_association(entity_type, entity_id),
        )

        if entity_type == EntityType.VARIETY:
            body = marker_card
        else:
            child_items = [self._build_child_item(c) for c in detail.children]
            children_card = EntityDetailCard(
                title=CHILD_TYPE_NAME.get(entity_type, "子项"),
                count=len(detail.children),
                children=child_items,
                add_label="新建",
                on_add=lambda e: self._create_child(entity_type, entity_id),
            )
            body = ft.Row([
                ft.Container(marker_card, expand=7),
                ft.Container(children_card, expand=3),
            ], spacing=20, expand=True)

        self.detail_panel.content = ft.Column(
            [header, ft.Divider(height=30), body], spacing=20, expand=True,
        )
        self._update_page()

    def _build_header(self, detail, entity_type, entity_id) -> ft.Row:
        return ft.Row([
            ft.Column([
                ft.Row([ft.Text(detail.path[0], size=14)]),
                ft.Text(detail.name, size=28, weight=ft.FontWeight.BOLD),
                ft.Text(detail.name_en or "", size=16, color=ft.Colors.GREY_600),
            ], spacing=5),
            ft.Row([
                ft.IconButton(ft.Icons.EDIT, tooltip="编辑",
                              on_click=lambda e: self._edit_entity(entity_type, entity_id)),
                ft.IconButton(ft.Icons.DELETE, tooltip="删除",
                              on_click=lambda e: self._delete_entity(entity_type, entity_id)),
            ]),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    def _build_marker_item(self, marker, entity_type, entity_id) -> ft.Container:
        # 需求 6：关联字段各占一行，字号与标题一致。
        info_lines: list[ft.Control] = []
        for label, value in [
            ("来源", marker.source),
            ("筛选", marker.screening_method),
            ("途径", marker.metabolic_pathway),
            ("文献", marker.literature_source),
            ("备注", marker.notes),
            ("备注2", marker.notes2),
        ]:
            if value:
                info_lines.append(ft.Text(
                    f"{label}: {value}", size=14, color=ft.Colors.GREY_700,
                    expand=True,
                ))
        if not info_lines:
            info_lines.append(ft.Text(
                "暂无详细信息", size=14, color=ft.Colors.GREY_500,
            ))

        title_row = ft.Row([
            ft.Text(marker.name, weight=ft.FontWeight.W_500),
            ft.Text(f"({marker.formula})", size=13,
                    style=ft.TextStyle(font_family="Consolas"))
            if marker.formula else ft.Container(),
        ], spacing=8)

        lines: list[ft.Control] = [
            title_row,
            *info_lines,
        ]

        actions: ft.Control
        if marker.level:
            actions = ft.Container(
                content=ft.Text(marker.level, size=12, color=ft.Colors.PURPLE),
                bgcolor=ft.Colors.PURPLE_50,
                padding=pad_sym(horizontal=8, vertical=4),
                border_radius=4,
            )
        else:
            actions = ft.Row([
                ft.IconButton(
                    ft.Icons.EDIT_OUTLINED, icon_size=18, icon_color=ft.Colors.BLUE,
                    tooltip="编辑关联",
                    on_click=lambda e, m=marker: self._edit_association(entity_type, entity_id, m),
                ),
                ft.IconButton(
                    ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=ft.Colors.RED,
                    tooltip="删除关联",
                    on_click=lambda e, mid=marker.id: self._delete_association(entity_type, entity_id, mid),
                ),
            ], spacing=0)

        return ft.Container(
            content=ft.Row([
                ft.Column(lines, spacing=4, expand=True),
                actions,
            ]),
            padding=12, border=bottom_border(),
            on_click=lambda e, mid=marker.id: EventBus().emit_navigate_to_marker(mid),
            ink=True,
        )

    def _build_literature(self, source: str) -> ft.Control:
        if re.match(r'https?://[^\s]+', source):
            text = source[:50] + "..." if len(source) > 50 else source
            return ft.TextButton(
                content=text, icon=ft.Icons.OPEN_IN_NEW,
                style=ft.ButtonStyle(padding=ft.Padding.all(4),
                                     text_style=ft.TextStyle(size=12)),
                on_click=lambda e, url=source: self._page.launch_url(url),
            )
        return ft.Row([
            ft.Icon(ft.Icons.ARTICLE, size=14, color=ft.Colors.GREY_600),
            ft.Text(f"文献: {source}", size=12, color=ft.Colors.GREY_600),
        ], spacing=4)

    def _build_child_item(self, child) -> ft.Container:
        return ft.Container(
            content=ft.Row([
                ft.Text(child.name, weight=ft.FontWeight.W_500, expand=True),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ft.Colors.GREY_400, size=20),
            ]),
            padding=12, border=bottom_border(),
            on_click=lambda e, c=child: self.select_entity(c.type, c.id),
            ink=True,
        )

    def _create_crop(self, e):
        def on_submit(data: CropCreate):
            crop_id = EntityService.create(EntityType.CROP, data)
            self.refresh()
            self.select_entity('crop', crop_id)

        FormDialog(page=self._page, title="新建粮食",
                   model_class=CropCreate, on_submit=on_submit).show()

    def _create_child(self, parent_type: EntityType, parent_id: int):
        if parent_type == EntityType.CROP:
            model_class, child_type = SubspeciesCreate, EntityType.SUBSPECIES
            initial = {'crop_id': parent_id}
        else:
            model_class, child_type = VarietyCreate, EntityType.VARIETY
            initial = {'subspecies_id': parent_id}

        def on_submit(data):
            new_id = EntityService.create(child_type, data)
            self.refresh()
            self.select_entity(child_type.value, new_id)

        FormDialog(
            page=self._page,
            title=f"新建{CHILD_TYPE_NAME.get(parent_type)}",
            model_class=model_class, on_submit=on_submit, initial_data=initial,
        ).show()

    def _edit_entity(self, entity_type: EntityType, entity_id: int):
        entities = EntityService.get_children(entity_type)
        entity = next((e for e in entities if e.id == entity_id), None)
        if not entity:
            return

        initial = {'name': entity.name, 'name_en': entity.name_en}
        if hasattr(entity, 'description'):
            initial['description'] = entity.description

        def on_submit(data):
            EntityService.update(entity_type, entity_id, data)
            self.refresh()

        FormDialog(
            page=self._page, title=f"编辑{entity_type.value}",
            model_class=ENTITY_UPDATE_MODEL[entity_type],
            on_submit=on_submit, initial_data=initial,
        ).show()

    def _delete_entity(self, entity_type: EntityType, entity_id: int):
        confirmation = EntityService.get_delete_confirmation(entity_type, entity_id)

        def on_confirm():
            EntityService.delete(entity_type, entity_id)
            self.selected_id = None
            self.selected_type = None
            self.refresh()

        ConfirmDialog(page=self._page, confirmation=confirmation,
                      on_confirm=on_confirm).show()

    def _add_association(self, entity_type: EntityType, entity_id: int):
        AssociationDialog.open_for_create(
            page=self._page,
            entity=(entity_type.value, entity_id),
            on_done=lambda: self._show_detail(entity_type, entity_id),
        )

    def _edit_association(self, entity_type: EntityType, entity_id: int, marker_info):
        assocs = MarkerService.get_associations_by_entity(entity_type, entity_id)
        association = next((a for a in assocs if a.marker_id == marker_info.id), None)
        if not association:
            return
        AssociationDialog.open_for_edit(
            page=self._page,
            association=association,
            entity=(entity_type.value, entity_id),
            on_done=lambda: self._show_detail(entity_type, entity_id),
        )

    def _delete_association(self, entity_type: EntityType, entity_id: int, marker_id: int):
        assocs = MarkerService.get_associations_by_entity(entity_type, entity_id)
        association = next((a for a in assocs if a.marker_id == marker_id), None)
        if not association:
            return

        def on_confirm():
            EntityService.delete(EntityType.ASSOCIATION, association.id)
            self._show_detail(entity_type, entity_id)

        ConfirmDialog(
            page=self._page,
            confirmation=DeleteConfirmation(
                entity_type=EntityType.ASSOCIATION, entity_id=association.id,
                entity_name="标志物关联", impact={},
            ),
            on_confirm=on_confirm,
        ).show()
