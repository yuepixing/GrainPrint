import flet as ft
from typing import Callable, Union, Optional, Dict, Any, get_origin, get_args
from pydantic import BaseModel
from grainprint.domain.entities import DeleteConfirmation


class BaseDialog:

    def __init__(self, page: ft.Page):
        self.page = page
        self.dialog: Optional[ft.AlertDialog] = None

    def show(self):
        if self.dialog:
            self.page.show_dialog(self.dialog)

    def close(self):
        self.page.pop_dialog()


class ConfirmDialog(BaseDialog):

    def __init__(self, page: ft.Page, confirmation: DeleteConfirmation,
                 on_confirm: Callable[[], None]):
        super().__init__(page)
        self._on_confirm = on_confirm
        self.dialog = ft.AlertDialog(
            title=ft.Text("确认删除"),
            content=ft.Text(confirmation.warning_message),
            actions=[
                ft.TextButton(content="取消", on_click=lambda e: self.close()),
                ft.TextButton(
                    content="删除",
                    on_click=self._do_confirm,
                    style=ft.ButtonStyle(color=ft.Colors.RED),
                ),
            ],
        )

    def _do_confirm(self, e):
        self.close()
        self._on_confirm()


def _unwrap_optional(field_type):
    if get_origin(field_type) is Union:
        args = [a for a in get_args(field_type) if a is not type(None)]
        if args:
            return args[0]
    return field_type


class FormDialog(BaseDialog):

    def __init__(self, page: ft.Page, title: str,
                 model_class: type[BaseModel],
                 on_submit: Callable[[BaseModel], None],
                 initial_data: Optional[Dict[str, Any]] = None):
        super().__init__(page)
        self.model_class = model_class
        self.on_submit = on_submit
        self.fields: Dict[str, ft.TextField] = {}

        self.dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=self._build_form(initial_data),
            actions=[
                ft.TextButton(content="取消", on_click=lambda e: self.close()),
                ft.TextButton(content="保存", on_click=self._handle_submit),
            ],
        )

    def _build_form(self, initial_data: Optional[Dict[str, Any]] = None) -> ft.Container:
        controls: list[ft.Control] = []
        initial_data = initial_data or {}

        for field_name, field_info in self.model_class.model_fields.items():
            if field_name == 'id':
                continue
            field_type = _unwrap_optional(field_info.annotation)
            if field_type not in (str, int):
                continue

            label = field_info.description or field_name.replace('_', ' ').title()
            is_required = field_info.is_required()
            is_multiline = field_type == str and any(
                kw in label for kw in ["备注", "途径", "文献"])

            initial_value = initial_data.get(field_name)
            field = ft.TextField(
                label=f"{label} *" if is_required else label,
                value=str(initial_value) if initial_value else "",
                keyboard_type=ft.KeyboardType.NUMBER if field_type == int else None,
                multiline=is_multiline,
                min_lines=3 if is_multiline else None,
                max_lines=3 if is_multiline else None,
                autofocus=len(controls) == 0,
            )
            self.fields[field_name] = field
            controls.append(field)

        return ft.Container(
            content=ft.Column(
                controls, spacing=10, tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            width=500,
        )

    def _handle_submit(self, e):
        for f in self.fields.values():
            f.error_text = None

        data = {}
        for name, field in self.fields.items():
            value = (field.value or "").strip()
            field_info = self.model_class.model_fields.get(name)
            if not field_info:
                continue

            is_required = field_info.is_required()
            field_type = _unwrap_optional(field_info.annotation)

            if value:
                if field_type == int:
                    if not value.lstrip('-').isdigit():
                        field.error_text = "请输入有效的数字"
                        self.page.update()
                        return
                    data[name] = int(value)
                else:
                    data[name] = value
            elif is_required:
                field.error_text = "此字段必填"
                self.page.update()
                return

        try:
            model_instance = self.model_class(**data)
            self.on_submit(model_instance)
        except Exception as exc:
            # Preserve the form and make a failed database write explicit.
            for field in self.fields.values():
                field.error_text = None
            first_field = next(iter(self.fields.values()), None)
            if first_field:
                first_field.error_text = f"未保存：{exc}"
            self.page.update()
            return
        self.close()


class MessageDialog(BaseDialog):

    def __init__(self, page: ft.Page, title: str, message: str, is_error: bool = False):
        super().__init__(page)
        self.dialog = ft.AlertDialog(
            title=ft.Text(title, color=ft.Colors.RED if is_error else None),
            content=ft.Text(message),
            actions=[ft.TextButton(content="确定", on_click=lambda e: self.close())],
        )

    @classmethod
    def show_info(cls, page: ft.Page, title: str, message: str):
        cls(page, title, message, is_error=False).show()

    @classmethod
    def show_error(cls, page: ft.Page, title: str, message: str):
        cls(page, title, message, is_error=True).show()