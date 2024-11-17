import dash_mantine_components as dmc
from components.menu.home.item.save import Saver
from components.menu.home.item.upload import Uploader
from components.menu.home.item.column_sizing import ColumnSizer
from components.menu.home.item.group_row import GroupRow
from components.menu.home.item.filtering import Filter
from components.menu.home.item.file_mode import FileMode


class HomeMenu:

    def __init__(self):
        self.filemode = FileMode()
        self.saver = Saver()
        self.uploader = Uploader()
        self.column_sizer = ColumnSizer()
        self.group_row = GroupRow()
        self.filter = Filter()

    def layout(self):
        return dmc.Group(
            [
                self.filemode.layout(),
                dmc.Divider(orientation="vertical"),
                self.uploader.layout(),
                self.saver.layout(),
                dmc.Divider(orientation="vertical"),
                self.column_sizer.layout(),
                dmc.Divider(orientation="vertical"),
                self.group_row.layout(),
                dmc.Divider(orientation="vertical"),
                self.filter.layout(),
                dmc.Divider(orientation="vertical"),
            ],
            justify="flex-start",
            gap="xs",
        )

    def register_callbacks(self, app):
        self.filter.register_callbacks(app)
        self.filemode.register_callbacks(app)
        self.uploader.register_callbacks(app)
        self.saver.register_callbacks(app)
        self.column_sizer.register_callbacks(app)
        self.group_row.register_callbacks(app)
