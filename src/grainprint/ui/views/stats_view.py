import flet as ft

from grainprint.core.database import get_session
from grainprint.core.repository import Repository
from grainprint.ui.components import StatCard, bordered, pad_sym


LEVEL_COLORS = {
    'crop': ft.Colors.GREEN_400,
    'subspecies': ft.Colors.BLUE_400,
    'variety': ft.Colors.PURPLE_400,
}
LEVEL_LABELS = {'crop': '粮食级', 'subspecies': '品类级', 'variety': '品种级'}


class StatsView(ft.Column):

    def __init__(self, page: ft.Page):
        super().__init__(expand=True, spacing=20)
        self._page = page

        self.title = ft.Text("数据统计", size=24, weight=ft.FontWeight.BOLD)
        self.stats_grid = ft.Container()
        self.distribution_chart = ft.Container()
        self.hierarchy_table = ft.Container()

        self.controls = [
            ft.Container(self.title, padding=20),
            self.stats_grid,
            ft.Row([self.distribution_chart, self.hierarchy_table], expand=True),
        ]

        self.load_stats()

    def refresh(self):
        self.load_stats()

    def load_stats(self):
        with get_session() as session:
            repo = Repository(session)
            stats = repo.get_stats()
            total = stats['total']

            stat_cards = ft.Row([
                StatCard("粮食",     total['crops'],        ft.Icons.GRASS,         ft.Colors.GREEN_700,  width=220),
                StatCard("品类",     total['subspecies'],   ft.Icons.PARK,          ft.Colors.BLUE_700,   width=220),
                StatCard("品种",     total['varieties'],    ft.Icons.LOCAL_FLORIST, ft.Colors.PURPLE_700, width=220),
                StatCard("标志物",   total['markers'],      ft.Icons.SCIENCE,       ft.Colors.ORANGE_700, width=220),
                StatCard("关联关系", total['associations'], ft.Icons.LINK,          ft.Colors.RED_700,    width=220),
            ], wrap=True, spacing=16, run_spacing=16)

            self.stats_grid.content = ft.Container(
                content=stat_cards, padding=pad_sym(horizontal=20),
            )

            self.distribution_chart.content = ft.Container(
                content=self._marker_distribution(stats),
                padding=20, expand=True,
            )

            self.hierarchy_table.content = ft.Container(
                content=self._hierarchy_stats(repo),
                padding=20, expand=True,
            )

        if self._page:
            self._page.update()

    def _marker_distribution(self, stats):
        distribution = stats['markers']['associations_by_level']
        total = sum(distribution.values())
        title = ft.Text("标志物分布", size=20, weight=ft.FontWeight.W_500)

        if total == 0:
            return self._panel([title, self._empty("暂无标志物关联数据")], width=400)

        items = []
        for level, count in distribution.items():
            percentage = count / total * 100
            items.append(ft.Column([
                ft.Row([
                    ft.Text(LEVEL_LABELS[level], size=14),
                    ft.Text(f"{count} ({percentage:.1f}%)", size=14, color=ft.Colors.GREY_600),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(
                    height=20, border_radius=10, bgcolor=ft.Colors.GREY_200,
                    content=ft.Container(
                        bgcolor=LEVEL_COLORS[level],
                        height=20, border_radius=10,
                        width=300 * (percentage / 100),
                    ),
                ),
            ], spacing=5))

        return self._panel([title] + items, width=400, spacing=15)

    def _hierarchy_stats(self, repo):
        title = ft.Text("数据层级分布", size=20, weight=ft.FontWeight.W_500)
        crops = repo.get_children('crop')

        if not crops:
            return self._panel([title, self._empty("暂无数据")], expand=True)

        rows = []
        for crop in crops[:10]:
            subspecies = repo.get_children('subspecies', crop.id)
            variety_count = sum(
                len(repo.get_children('variety', sub.id)) for sub in subspecies
            )
            marker_count = repo.get_marker_count_by_crop(crop.id)

            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(crop.name)),
                ft.DataCell(ft.Text(str(len(subspecies)))),
                ft.DataCell(ft.Text(str(variety_count))),
                ft.DataCell(ft.Text(str(marker_count))),
            ]))

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("粮食",   weight=ft.FontWeight.W_500)),
                ft.DataColumn(ft.Text("品类数", weight=ft.FontWeight.W_500)),
                ft.DataColumn(ft.Text("品种数", weight=ft.FontWeight.W_500)),
                ft.DataColumn(ft.Text("标志物", weight=ft.FontWeight.W_500)),
            ],
            rows=rows,
            border_radius=8,
            horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_200),
            column_spacing=30,
        )

        body = ft.Container(
            content=table,
            border=bordered(1, ft.Colors.GREY_300),
            border_radius=8,
        )
        return self._panel([title, body], expand=True, spacing=10)

    @staticmethod
    def _empty(text: str) -> ft.Container:
        return ft.Container(
            content=ft.Text(text, color=ft.Colors.GREY_500),
            padding=40, alignment=ft.Alignment.CENTER,
        )

    @staticmethod
    def _panel(children: list[ft.Control], width: int | None = None,
               expand: bool = False, spacing: int = 10) -> ft.Container:
        return ft.Container(
            content=ft.Column(children, spacing=spacing),
            bgcolor=ft.Colors.WHITE,
            padding=20,
            border_radius=8,
            width=width,
            expand=expand,
            border=bordered(),
        )