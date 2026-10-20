import flet as ft


def bordered(width: int = 1, color: str | None = None) -> ft.Border:
    return ft.Border.all(width, color or ft.Colors.GREY_200)


def selected_border(is_selected: bool,
                    selected_color: str = ft.Colors.BLUE,
                    normal_color: str | None = None) -> ft.Border:
    nc = normal_color or ft.Colors.GREY_200
    if is_selected:
        return ft.Border(
            left=ft.BorderSide(3, selected_color),
            right=ft.BorderSide(1, nc),
            top=ft.BorderSide(1, nc),
            bottom=ft.BorderSide(1, nc),
        )
    return ft.Border.all(1, nc)


def bottom_border(color: str | None = None) -> ft.Border:
    return ft.Border(bottom=ft.BorderSide(1, color or ft.Colors.GREY_200))


def right_border(color: str | None = None) -> ft.Border:
    return ft.Border(right=ft.BorderSide(1, color or ft.Colors.GREY_300))


def pad_only(left: int = 0, top: int = 0, right: int = 0, bottom: int = 0) -> ft.Padding:
    return ft.Padding.only(left=left, top=top, right=right, bottom=bottom)


def pad_sym(horizontal: int = 0, vertical: int = 0) -> ft.Padding:
    return ft.Padding.symmetric(horizontal=horizontal, vertical=vertical)