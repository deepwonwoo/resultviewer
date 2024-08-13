import dash_mantine_components as dmc
from dash import html
from components.menu.home.item.saver import Saver
from components.menu.home.item.uploader import Uploader
from components.menu.home.item.columnSizer import ColumnSizer
from components.menu.home.item.groupRow import groupRow
from components.menu.home.item.filter import Filter
from components.menu.home.item.crossProber import CrossProber


class HomeMenu:

    def __init__(self) -> None:
        self.saver = Saver()
        self.uploader = Uploader()
        self.columnSizer = ColumnSizer()
        self.groupRow = groupRow()
        self.filter = Filter()
        self.crossProber = CrossProber()

    def layout(self):
        return html.Div(
            [
                self.uploader.layout(),
                self.saver.layout(),
                html.Div(id="file-mode"),
                dmc.Divider(orientation="vertical"),
                self.columnSizer.layout(),
                dmc.Divider(orientation="vertical"),
                self.groupRow.layout(),
                dmc.Divider(orientation="vertical"),
                self.filter.layout(),
                dmc.Divider(orientation="vertical"),
                self.crossProber.layout(),
            ],
            className="d-grid gap-2 d-md-flex justify-content-md-start m-2",
        )

    def register_callbacks(self, app):
        self.uploader.register_callbacks(app)
        self.saver.register_callbacks(app)
        self.columnSizer.register_callbacks(app)
        self.groupRow.register_callbacks(app)
        self.filter.register_callbacks(app)
        self.crossProber.register_callbacks(app)
