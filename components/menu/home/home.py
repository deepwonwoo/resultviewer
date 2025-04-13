import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
# from components.menu.home.item.save import Saver
from components.menu.home.item.open import Opener
from components.menu.home.item.column_sizing import ColumnSizer
# from components.menu.home.item.file_mode import FileMode
from components.menu.home.item.group_row import GroupRow
# from components.menu.home.item.filtering import Filter
# from components.menu.home.item.workspace_explorer import WorkspaceExplorer


class HomeMenu:

    def __init__(self):
        # self.filemode = FileMode()
        # self.saver = Saver()
        self.opener = Opener()
        self.column_sizer = ColumnSizer()
        self.group_row = GroupRow()
        # self.filter = Filter()
        # self.workspaceExplorer = WorkspaceExplorer()

    def layout(self):
        return dbpc.ButtonGroup(
            [
                dbpc.Divider(),
                # self.filemode.layout(),
                dbpc.Divider(),
                self.opener.layout(),
                # self.saver.layout(),
                dbpc.Divider(),
                self.column_sizer.layout(),
                dbpc.Divider(),
                self.group_row.layout(),
                dbpc.Divider(),
                # self.filter.layout(),
                dbpc.Divider(),
            ],
            style={"height": 35},
        )

    def register_callbacks(self, app):
        # self.filemode.register_callbacks(app)
        self.opener.register_callbacks(app)
        # self.saver.register_callbacks(app)
        self.column_sizer.register_callbacks(app)
        self.group_row.register_callbacks(app)
        # self.filter.register_callbacks(app)
        # self.workspaceExplorer.register_callbacks(app)
