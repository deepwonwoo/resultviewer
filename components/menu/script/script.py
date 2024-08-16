import dash_mantine_components as dmc
from dash import html
from components.menu.home.item.saver import Saver
from components.menu.home.item.uploader import Uploader

from components.menu.home.item.groupRow import groupRow


class ScriptMenu:

    def __init__(self) -> None:
        self.chart = ChartEditor()
        self.profile = PandasProfile()
        self.compare = Compare()
        self.masterName = MasterName()
        self.categorizePart = CategorizePart()
        self.diffUpdate = DiffUpdate()
        self.migrateWaiver = MigrateWaiver()

    def layout(self):
        return html.Div(
            [
                self.chart.layout(),
                dmc.Divider(orientation="vertical"),
                self.profile.layout(),
                dmc.Divider(orientation="vertical"),
                self.compare.layout(),
                dmc.Divider(orientation="vertical"),
                self.masterName.layout(),
                dmc.Divider(orientation="vertical"),
                self.categorizePart.layout(),
                dmc.Divider(orientation="vertical"),
                self.diffUpdate.layout(),
                dmc.Divider(orientation="vertical"),
                self.migrateWaiver.layout(),
                dmc.Divider(orientation="vertical"),
            ],
            className="d-grid gap-2 d-md-flex justify-content-md-start m-2",
        )

    def register_callbacks(self, app):
        self.chart.register_callbacks(app)
        self.profile.register_callbacks(app)
        self.compare.register_callbacks(app)
        self.masterName.register_callbacks(app)
        self.categorizePart.register_callbacks(app)
        self.diffUpdate.register_callbacks(app)
        self.migrateWaiver.register_callbacks(app)
