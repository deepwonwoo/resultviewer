import time
import dash_mantine_components as dmc
from dash import html, dcc, Input, Output, State, no_update

from utils.dataframe_operations import validate_df
from utils.db_management import WORKSPACE, set_dataframe

from components.grid import DataGrid
from components.dag.column_definitions import generate_column_definitions
from components.menu.home.home import HomeMenu
from components.menu.edit.edit import EditMenu
from components.menu.script.script import ScriptMenu

class ResultViewer:
    def __init__(self, app):
        self.home_menu = HomeMenu()
        # self.view_menu = ViewMenu()
        self.edit_menu = EditMenu()
        self.script_menu = ScriptMenu()
        self.data_grid = DataGrid()
        self.register_callbacks(app)

    def layout(self):
        return dmc.MantineProvider([
            dmc.NotificationProvider(),
            html.Div(id="notifications"),
            dmc.AppShell([
                dmc.AppShellHeader(self._create_header()),
                dmc.AppShellMain(self.data_grid.layout()),
                dmc.AppShellFooter(self._create_footer())
            ], header={"height": 80})
        ])

    def _create_header(self) -> html.Div:
        """Create the header section of the layout."""
        return html.Div(
            [
                dmc.Tabs(
                    [
                        dmc.TabsList(
                            [
                                dmc.TabsTab("Home", value="home"),
                                dmc.TabsTab("View", value="view"),
                                dmc.TabsTab("Edit", value="edit"),
                                dmc.TabsTab("Script", value="script"),
                            ]
                        ),
                        dmc.TabsPanel(self.home_menu.layout(), value="home"),
                        # dmc.TabsPanel(self.view_menu.layout(), value="view"),
                        dmc.TabsPanel(self.edit_menu.layout(), value="edit"),
                        dmc.TabsPanel(self.script_menu.layout(), value="script"),
                    ],
                    id="app-menu-tabs",
                    value="home",
                ),
                html.Div(id="app-menu-content"),
            ]
        )
    def _create_footer(self) -> dmc.Group:
        """Create the footer section of the layout."""
        return html.Div(
            [
                dmc.Group(
                    [
                        dmc.Group(
                            [
                                dmc.Text(id="csv-file-path", c="gray", size="sm", ml=5),
                            ],
                            pt=0,
                        ),
                        dmc.Group(
                            [
                                html.Div(id="total-row-count"),
                                html.Div(id="row-counter"),
                            ],
                            justify="flex-end",
                            pt=0,
                        ),
                    ],
                    grow=True,
                    justify="space-around",
                ),
            ],
            className="bg-light border border-secondary border-top-0",
        )
    

    def register_callbacks(self, app):
        """컴포넌트별 콜백 함수 등록."""
        self.home_menu.register_callbacks(app)
        # self.view_menu.register_callbacks(app)
        self.edit_menu.register_callbacks(app)
        self.script_menu.register_callbacks(app)

        self.data_grid.register_callbacks(app)


        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Input("notifications", "children"),
            prevent_initial_call=True
        )
        def refresh_noti(n):
            time.sleep(1)
            return None

        @app.callback(
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("file-reload-btn", "n_clicks"),
            State("csv-file-path", "children"),
            prevent_initial_call=True
        )
        def reload_file(n, file_path):
            if not file_path:
                return no_update
            if file_path.startswith("WORKSPACE/"):
                file_path = file_path.replace("WORKSPACE", WORKSPACE)
            df = validate_df(file_path)
            set_dataframe("df", df)
            return generate_column_definitions(df)
