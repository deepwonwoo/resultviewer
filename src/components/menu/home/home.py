import dash_mantine_components as dmc
from dash import html
from components.menu.home.item.save import Saver
from components.menu.home.item.upload import Uploader
from components.menu.home.item.column_sizing import ColumnSizer
from components.menu.home.item.group_row import groupRow
from components.menu.home.item.filtering import Filter
from components.menu.home.item.cross_probing import CrossProber


class HomeMenu:

    def __init__(self) -> None:
        self.saver = Saver()
        self.uploader = Uploader()
        self.columnSizer = ColumnSizer()
        self.groupRow = groupRow()
        self.filter = Filter()
        self.crossProber = CrossProber()

    def layout(self):
        return dmc.Group(
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
            justify='flex-start',
            gap='xs'
        )

    def register_callbacks(self, app):
        self.uploader.register_callbacks(app)
        self.saver.register_callbacks(app)
        self.columnSizer.register_callbacks(app)
        self.groupRow.register_callbacks(app)
        # self.filter.register_callbacks(app)
        self.crossProber.register_callbacks(app)
