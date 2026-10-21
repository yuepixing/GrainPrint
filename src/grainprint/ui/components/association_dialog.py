import flet as ft
from typing import Optional, Callable, Any
from grainprint.core.database import get_session
from grainprint.core.repository import Repository
from grainprint.domain.entities import (
    EntityType, MarkerAssociationCreate, MarkerAssociationUpdate,
)
from grainprint.domain.services import EntityService, MarkerService
from grainprint.ui.components.styles import bordered, pad_only, pad_sym


ENTITY_LABELS = {'crop': '粮食', 'subspecies': '品类', 'variety': '品种'}

INFO_FIELDS = [
    ('source',            "来源",     False),
    ('screening_method',  "筛选方法", False),
    ('metabolic_pathway', "代谢途径", True),
    ('literature_source', "文献来源", True),
    ('notes',             "备注1",    True),
    ('notes2',            "备注2",    True),
]


class AssociationDialog:

    @classmethod
    def open_for_create(
        cls, page: ft.Page, on_done: Callable,
        marker_id: Optional[int] = None,
        entity: Optional[tuple[str, int]] = None,
    ):
        dlg = cls(page, on_done, multi=(entity is None))
        if marker_id is not None:
            dlg.marker_id = marker_id
            dlg.show_marker_section = False
            dlg.show_entity_section = True
        elif entity is not None:
            dlg.entities = {entity}
            dlg.show_marker_section = True
            dlg.show_entity_section = False
        dlg.marker_section_open = True
        dlg.entity_section_open = True
        dlg._show("新建关联")

    @classmethod
    def open_for_edit(cls, page: ft.Page, association, entity: tuple[str, int],
                      on_done: Callable):
        dlg = cls(page, on_done, multi=False)
        dlg.association_id = association.id
        dlg.marker_id = association.marker_id
        dlg.entities = {entity}
        dlg.show_marker_section = True
        dlg.show_entity_section = True
        dlg.marker_section_open = False
        dlg.entity_section_open = False
        dlg._info_values = {
            'source':            association.source or '',
            'screening_method':  association.screening_method or '',
            'metabolic_pathway': association.metabolic_pathway or '',
            'literature_source': association.literature_source or '',
            'notes':             association.notes or '',
            'notes2':            association.notes2 or '',
        }
        dlg._show("编辑关联")

    def __init__(self, page: ft.Page, on_done: Callable, multi: bool):
        self.page = page
        self.on_done = on_done
        self.multi = multi

        self.association_id: Optional[int] = None
        self.marker_id: Optional[int] = None
        self.entities: set[tuple[str, int]] = set()
        self.expanded: set[str] = set()
        self.marker_filter = ""

        self.show_marker_section = True
        self.show_entity_section = True
        self.marker_section_open = True
        self.entity_section_open = True

        self._markers: list[Any] = []
        self._tree: list[dict] = []
        self._info_values: dict[str, str] = {}

        self._marker_list: Optional[ft.Column] = None
        self._entity_tree: Optional[ft.Column] = None
        self._counter: Optional[ft.Text] = None
        self._marker_body: Optional[ft.Container] = None
        self._entity_body: Optional[ft.Container] = None
        self._marker_header: Optional[ft.Container] = None
        self._entity_header: Optional[ft.Container] = None
        self._info_fields: dict[str, ft.TextField] = {}
        self._dialog: Optional[ft.AlertDialog] = None

    def _show(self, title: str):
        self._preload()
        self._dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=self._build_body(),
            actions=[
                ft.TextButton(content="取消", on_click=lambda e: self._close()),
                ft.TextButton(content="保存", on_click=self._save),
            ],
        )
        self.page.show_dialog(self._dialog)

    def _preload(self):
        self._markers = EntityService.get_children(EntityType.MARKER)
        with get_session() as session:
            repo = Repository(session)
            self._tree = [
                {
                    'type': 'crop', 'id': c.id, 'name': c.name,
                    'children': [
                        {
                            'type': 'subspecies', 'id': s.id, 'name': s.name,
                            'children': [
                                {'type': 'variety', 'id': v.id, 'name': v.name, 'children': []}
                                for v in repo.get_children('variety', s.id)
                            ],
                        }
                        for s in repo.get_children('subspecies', c.id)
                    ],
                }
                for c in repo.get_children('crop')
            ]
        for c in self._tree:
            self.expanded.add(f"crop_{c['id']}")

    def _build_body(self) -> ft.Container:
        rows: list[ft.Control] = []
        if self.show_marker_section:
            rows.append(self._marker_section())
        if self.show_entity_section:
            rows.append(self._entity_section())
        rows.append(ft.Divider())
        rows.extend(self._info_section())

        return ft.Container(
            content=ft.Column(rows, spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
            width=640, height=680,
        )

    def _build_collapsible(
        self, title: str, subtitle_getter: Callable[[], str],
        is_open: bool, body: ft.Control, on_toggle: Callable,
    ) -> tuple[ft.Column, ft.Container, ft.Container]:
        icon = ft.Icon(
            ft.Icons.KEYBOARD_ARROW_DOWN if is_open else ft.Icons.KEYBOARD_ARROW_RIGHT,
            size=20,
        )
        subtitle = ft.Text(
            subtitle_getter(), size=12, color=ft.Colors.GREY_600,
            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
        )
        header = ft.Container(
            content=ft.Row([
                icon,
                ft.Text(title, weight=ft.FontWeight.W_500),
                ft.Container(width=8),
                ft.Container(content=subtitle, expand=True),
            ], spacing=4),
            padding=pad_sym(horizontal=8, vertical=10),
            bgcolor=ft.Colors.GREY_50,
            border_radius=4,
            on_click=lambda e: on_toggle(),
            ink=True,
            data={'icon': icon, 'subtitle': subtitle},
        )
        body_container = ft.Container(
            content=body, visible=is_open,
            padding=pad_only(top=8),
        )
        return ft.Column([header, body_container], spacing=0), body_container, header

    @staticmethod
    def _update_header_icon(header: ft.Container, is_open: bool):
        header.data['icon'].name = (
            ft.Icons.KEYBOARD_ARROW_DOWN if is_open else ft.Icons.KEYBOARD_ARROW_RIGHT
        )

    @staticmethod
    def _refresh_header_subtitle(header: ft.Container, text: str):
        header.data['subtitle'].value = text

    def _marker_section(self) -> ft.Control:
        self._marker_list = ft.Column(height=150, spacing=2, scroll=ft.ScrollMode.AUTO)
        self._refresh_markers()

        body = ft.Column([
            ft.TextField(
                label="搜索", prefix_icon=ft.Icons.SEARCH, dense=True,
                on_change=self._on_marker_search,
                width=float("inf"),
            ),
            ft.Container(
                content=self._marker_list,
                border=bordered(1, ft.Colors.GREY_300),
                border_radius=4,
            ),
        ], spacing=6)

        section, self._marker_body, self._marker_header = self._build_collapsible(
            title="标志物",
            subtitle_getter=self._marker_subtitle,
            is_open=self.marker_section_open,
            body=body,
            on_toggle=self._toggle_marker_section,
        )
        return section

    def _marker_subtitle(self) -> str:
        if self.marker_id is None:
            return "未选择"
        m = next((x for x in self._markers if x.id == self.marker_id), None)
        return f"当前: {m.name}" if m else "未选择"

    def _toggle_marker_section(self):
        self.marker_section_open = not self.marker_section_open
        self._marker_body.visible = self.marker_section_open
        self._update_header_icon(self._marker_header, self.marker_section_open)
        self.page.update()

    def _on_marker_search(self, e):
        self.marker_filter = (e.control.value or "").lower().strip()
        self._refresh_markers()
        self.page.update()

    def _refresh_markers(self):
        self._marker_list.controls.clear()
        kw = self.marker_filter
        for m in self._markers:
            if kw and not self._marker_matches(m, kw):
                continue
            self._marker_list.controls.append(self._marker_item(m))
        if not self._marker_list.controls:
            self._marker_list.controls.append(self._empty("未找到匹配的标志物"))

    @staticmethod
    def _marker_matches(m, kw: str) -> bool:
        return (
            kw in m.name.lower()
            or (m.name_en and kw in m.name_en.lower())
            or (m.structure_formula and kw in m.structure_formula.lower())
        )

    def _marker_item(self, marker) -> ft.Container:
        selected = self.marker_id == marker.id
        return ft.Container(
            content=ft.Row([
                ft.Text(marker.name, weight=ft.FontWeight.W_500, expand=2),
                ft.Text(
                    marker.structure_formula or "—",
                    size=12, color=ft.Colors.GREY_600,
                    style=ft.TextStyle(font_family="Consolas"),
                    expand=3,
                ),
            ]),
            padding=8,
            bgcolor=ft.Colors.BLUE_50 if selected else None,
            on_click=lambda e, mid=marker.id: self._select_marker(mid),
            ink=True,
            data=marker.id,
        )

    def _select_marker(self, marker_id: int):
        self.marker_id = marker_id
        for item in self._marker_list.controls:
            if hasattr(item, 'data') and isinstance(item.data, int):
                item.bgcolor = ft.Colors.BLUE_50 if item.data == marker_id else None
        if self._marker_header:
            self._refresh_header_subtitle(self._marker_header, self._marker_subtitle())
        self.page.update()

    def _entity_section(self) -> ft.Control:
        self._counter = ft.Text(self._counter_text(), size=12, color=ft.Colors.GREY_700)
        self._entity_tree = ft.Column(height=200, spacing=2, scroll=ft.ScrollMode.AUTO)
        self._refresh_tree()

        hint = "可跨层级多选" if self.multi else "单选"
        body = ft.Column([
            ft.Row([
                ft.Text(hint, size=12, color=ft.Colors.GREY_600, expand=True),
                self._counter,
            ]),
            ft.Container(
                content=self._entity_tree,
                border=bordered(1, ft.Colors.GREY_300),
                border_radius=4,
            ),
        ], spacing=6)

        section, self._entity_body, self._entity_header = self._build_collapsible(
            title="关联实体",
            subtitle_getter=self._entity_subtitle,
            is_open=self.entity_section_open,
            body=body,
            on_toggle=self._toggle_entity_section,
        )
        return section

    def _entity_subtitle(self) -> str:
        if not self.entities:
            return "未选择"
        if len(self.entities) == 1:
            et, eid = next(iter(self.entities))
            name = self._find_entity_name(et, eid)
            return f"当前: {name}" if name else "未选择"
        return f"当前: 已选 {len(self.entities)} 项"

    def _find_entity_name(self, etype: str, eid: int) -> Optional[str]:
        for c in self._tree:
            if c['type'] == etype and c['id'] == eid:
                return c['name']
            for s in c['children']:
                if s['type'] == etype and s['id'] == eid:
                    return f"{c['name']} > {s['name']}"
                for v in s['children']:
                    if v['type'] == etype and v['id'] == eid:
                        return f"{c['name']} > {s['name']} > {v['name']}"
        return None

    def _toggle_entity_section(self):
        self.entity_section_open = not self.entity_section_open
        self._entity_body.visible = self.entity_section_open
        self._update_header_icon(self._entity_header, self.entity_section_open)
        self.page.update()

    def _counter_text(self) -> str:
        return f"已选 {len(self.entities)} 项"

    def _refresh_tree(self):
        self._entity_tree.controls.clear()
        if not self._tree:
            self._entity_tree.controls.append(self._empty("暂无数据"))
            return
        for crop in self._tree:
            self._append_node(crop, level=0)

    def _append_node(self, node: dict, level: int):
        ntype, nid = node['type'], node['id']
        key = f"{ntype}_{nid}"
        has_children = bool(node['children'])
        expanded = key in self.expanded
        checked = (ntype, nid) in self.entities

        toggle = ft.IconButton(
            icon=ft.Icons.ARROW_DROP_DOWN if expanded else ft.Icons.ARROW_RIGHT,
            icon_size=18,
            on_click=lambda e, k=key: self._toggle_expand(k),
        ) if has_children else ft.Container(width=32)

        self._entity_tree.controls.append(ft.Container(
            content=ft.Row([
                toggle,
                ft.Checkbox(
                    value=checked,
                    on_change=lambda e, t=ntype, i=nid: self._toggle_entity(t, i),
                ),
                ft.Text(node['name'], expand=True),
                ft.Text(ENTITY_LABELS[ntype], size=11, color=ft.Colors.GREY_500),
            ], spacing=4),
            padding=pad_only(left=level * 20 + 4, top=2, bottom=2, right=8),
            bgcolor=ft.Colors.BLUE_50 if checked else None,
            border_radius=4,
        ))

        if expanded:
            for child in node['children']:
                self._append_node(child, level + 1)

    def _toggle_expand(self, key: str):
        (self.expanded.discard if key in self.expanded else self.expanded.add)(key)
        self._refresh_tree()
        self.page.update()

    def _toggle_entity(self, entity_type: str, entity_id: int):
        k = (entity_type, entity_id)
        if k in self.entities:
            self.entities.discard(k)
        else:
            if not self.multi:
                self.entities.clear()
            self.entities.add(k)
        self._counter.value = self._counter_text()
        self._refresh_tree()
        if self._entity_header:
            self._refresh_header_subtitle(self._entity_header, self._entity_subtitle())
        self.page.update()

    def _info_section(self) -> list[ft.Control]:
        self._info_fields.clear()
        controls: list[ft.Control] = [ft.Text("关联信息", weight=ft.FontWeight.W_500)]
        for key, label, multiline in INFO_FIELDS:
            field = ft.TextField(
                label=label,
                value=self._info_values.get(key, ''),
                multiline=multiline,
                min_lines=2 if multiline else None,
                max_lines=3 if multiline else None,
                height=None if multiline else 60,
                width=float("inf"),
            )
            self._info_fields[key] = field
            controls.append(field)
        return controls

    def _collect_info(self) -> dict:
        return {k: (f.value or '').strip() or None for k, f in self._info_fields.items()}

    def _save(self, e):
        if not self.marker_id:
            return self._warn("请选择标志物")
        if not self.entities:
            return self._warn("请至少选择一个实体")

        info = self._collect_info()
        if self.association_id is None:
            self._create_many(info)
        else:
            self._update_one(info)

        self._close()
        if self.on_done:
            self.on_done()

    def _create_many(self, info: dict):
        for etype_str, eid in self.entities:
            etype = EntityType(etype_str)
            if self._already_linked(etype, eid, self.marker_id):
                continue
            MarkerService.create_association(MarkerAssociationCreate(
                marker_id=self.marker_id,
                entity_type=etype, entity_id=eid,
                **info,
            ))

    def _update_one(self, info: dict):
        etype_str, eid = next(iter(self.entities))
        etype = EntityType(etype_str)
        unchanged = any(
            a.id == self.association_id and a.marker_id == self.marker_id
            for a in MarkerService.get_associations_by_entity(etype, eid)
        )
        if unchanged:
            MarkerService.update_association(
                self.association_id, MarkerAssociationUpdate(**info))
        else:
            EntityService.delete(EntityType.ASSOCIATION, self.association_id)
            MarkerService.create_association(MarkerAssociationCreate(
                marker_id=self.marker_id,
                entity_type=etype, entity_id=eid,
                **info,
            ))

    @staticmethod
    def _already_linked(etype: EntityType, eid: int, marker_id: int) -> bool:
        return any(
            a.marker_id == marker_id
            for a in MarkerService.get_associations_by_entity(etype, eid)
        )

    def _warn(self, msg: str):
        snack = ft.SnackBar(content=ft.Text(msg), bgcolor=ft.Colors.ORANGE)
        self.page.show_dialog(snack)

    def _close(self):
        self.page.pop_dialog()

    @staticmethod
    def _empty(text: str) -> ft.Container:
        return ft.Container(
            content=ft.Text(text, color=ft.Colors.GREY_500),
            padding=20, alignment=ft.Alignment.CENTER,
        )
