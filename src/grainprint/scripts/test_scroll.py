"""最小 scroll_to 测试 - 验证 key 机制是否有 bug"""
import flet as ft


def main(page: ft.Page):
    page.title = "Scroll Test"

    lv = ft.ListView(expand=True, spacing=4)
    for i in range(50):
        row = ft.Container(
            content=ft.Text(f"第 {i} 行"),
            padding=12,
            bgcolor=ft.Colors.GREY_100,
            border_radius=4,
        )
        row.key = str(i)
        lv.controls.append(row)

    def scroll_to(key: str, duration: int = 600):
        print(f"[TEST] 滚到 key={key}, duration={duration}")
        lv.scroll_to(key=key, duration=duration)
        page.update()

    buttons = ft.Row([
        ft.Button("滚到 5",  on_click=lambda e: scroll_to("5")),
        ft.Button("滚到 22", on_click=lambda e: scroll_to("22")),
        ft.Button("滚到 40", on_click=lambda e: scroll_to("40")),
        ft.Button("duration=300",
                          on_click=lambda e: scroll_to("22", 300)),
        ft.Button("duration=1000",
                          on_click=lambda e: scroll_to("22", 1000)),
    ])

    page.add(buttons, ft.Container(lv, expand=True))


if __name__ == "__main__":
    ft.run(main)