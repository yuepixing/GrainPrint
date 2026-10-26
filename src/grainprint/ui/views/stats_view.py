import flet as ft

from grainprint.core.database import get_session
from grainprint.core.repository import Repository
from grainprint.ui.components import StatCard, bordered, pad_sym


class StatsView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True, spacing=20)
        self._page = page
        self.title = ft.Text("数据统计", size=24, weight=ft.FontWeight.BOLD)
        self.stats_grid = ft.Container()
        self.distribution_chart = ft.Container()
        self.hierarchy_table = ft.Container()
        self.controls = [ft.Container(self.title, padding=20), self.stats_grid,
                         ft.Row([self.distribution_chart, self.hierarchy_table], expand=True)]
        self.load_stats()

    def refresh(self):
        self.load_stats()

    def load_stats(self):
        with get_session() as session:
            repo = Repository(session)
            stats, total = repo.get_stats(), repo.get_stats()['total']
            kinds = total['material_types']
            cards = ft.Row([
                StatCard("粮食", total['crops'], ft.Icons.GRASS, ft.Colors.GREEN_700, width=200),
                StatCard("品类", total['subspecies'], ft.Icons.PARK, ft.Colors.BLUE_700, width=200),
                StatCard("品种", total['varieties'], ft.Icons.LOCAL_FLORIST, ft.Colors.PURPLE_700, width=200),
                StatCard("标志物", kinds['标志物'], ft.Icons.SCIENCE, ft.Colors.ORANGE_700, width=200),
                StatCard("特征物质", kinds['特征物质'], ft.Icons.BIOTECH, ft.Colors.TEAL_700, width=200),
                StatCard("关联关系", total['associations'], ft.Icons.LINK, ft.Colors.RED_700, width=200),
            ], wrap=True, spacing=16, run_spacing=16)
            self.stats_grid.content = ft.Container(cards, padding=pad_sym(horizontal=20))
            self.distribution_chart.content = ft.Container(self._material_distribution(stats), padding=20, expand=True)
            self.hierarchy_table.content = ft.Container(self._hierarchy_stats(repo), padding=20, expand=True)
        self._page.update()

    def _material_distribution(self, stats):
        sources = stats['markers']['material_sources']
        title = ft.Text("标志物及特征物质分布", size=20, weight=ft.FontWeight.W_500)
        rows = []
        for source in ("自行筛选", "文献报道"):
            counts = sources[source]
            rows.append(ft.Container(ft.Column([
                ft.Text(source, size=16, weight=ft.FontWeight.W_500),
                ft.Text(f"标志物：{counts['标志物']}    特征物质：{counts['特征物质']}", size=14),
            ], spacing=4), padding=12, bgcolor=ft.Colors.GREY_50, border_radius=6))
        return self._panel([title, *rows, ft.Text("未填写备注1或备注2的物质不纳入上述分类统计。", size=12, color=ft.Colors.GREY_600)], width=430, spacing=12)

    def _hierarchy_stats(self, repo):
        title = ft.Text("数据层级分布", size=20, weight=ft.FontWeight.W_500)
        crops = repo.get_children('crop')
        if not crops:
            return self._panel([title, self._empty("暂无数据")], expand=True)
        rows = []
        for crop in crops[:10]:
            subspecies = repo.get_children('subspecies', crop.id)
            varieties = sum(len(repo.get_children('variety', sub.id)) for sub in subspecies)
            markers = repo.get_marker_count_by_crop_and_type(crop.id, "标志物")
            features = repo.get_marker_count_by_crop_and_type(crop.id, "特征物质")
            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(crop.name)), ft.DataCell(ft.Text(str(len(subspecies)))),
                ft.DataCell(ft.Text(str(varieties))), ft.DataCell(ft.Text(str(markers))),
                ft.DataCell(ft.Text(str(features))),
            ]))
        table = ft.DataTable(columns=[
            ft.DataColumn(ft.Text("粮食", weight=ft.FontWeight.W_500)),
            ft.DataColumn(ft.Text("品类数", weight=ft.FontWeight.W_500)),
            ft.DataColumn(ft.Text("品种数", weight=ft.FontWeight.W_500)),
            ft.DataColumn(ft.Text("标志物", weight=ft.FontWeight.W_500)),
            ft.DataColumn(ft.Text("特征物质", weight=ft.FontWeight.W_500)),
        ], rows=rows, border_radius=8, horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_200), column_spacing=25)
        return self._panel([title, ft.Container(table, border=bordered(1, ft.Colors.GREY_300), border_radius=8)], expand=True, spacing=10)

    @staticmethod
    def _empty(text):
        return ft.Container(ft.Text(text, color=ft.Colors.GREY_500), padding=40, alignment=ft.Alignment.CENTER)

    @staticmethod
    def _panel(children, width=None, expand=False, spacing=10):
        return ft.Container(ft.Column(children, spacing=spacing), bgcolor=ft.Colors.WHITE, padding=20,
                            border_radius=8, width=width, expand=expand, border=bordered())
