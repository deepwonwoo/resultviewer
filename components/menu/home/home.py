import dash_mantine_components as dmc
from dash import html

from components.menu.home.item.save import Saver
from components.menu.home.item.upload import Uploader
from components.menu.home.item.column_sizing import ColumnSizer
from components.menu.home.item.group_row import GroupRow
from components.menu.home.item.filtering import Filter
from components.menu.home.item.cross_probing import CrossProber


class HomeMenu:

    def __init__(self):
        self.saver = Saver()
        self.uploader = Uploader()
        self.column_sizer = ColumnSizer()
        self.group_row = GroupRow()
        self.filter = Filter()
        self.cross_prober = CrossProber()

    def layout(self):
        return dmc.Group(
            [
                self.uploader.layout(),
                self.saver.layout(),
                html.Div(id="file-mode"),
                dmc.Divider(orientation="vertical"),
                self.column_sizer.layout(),
                dmc.Divider(orientation="vertical"),
                self.group_row.layout(),
                dmc.Divider(orientation="vertical"),
                self.filter.layout(),
                dmc.Divider(orientation="vertical"),
                self.cross_prober.layout(),
            ],
            justify='flex-start',
            gap='xs'
        )

    def register_callbacks(self, app):
        self.uploader.register_callbacks(app)
        self.saver.register_callbacks(app)
        self.column_sizer.register_callbacks(app)
        self.group_row.register_callbacks(app)
        # self.filter.register_callbacks(app)
        self.cross_prober.register_callbacks(app)
