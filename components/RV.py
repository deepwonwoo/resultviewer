import dash_mantine_components as dmc
from dash import html, dcc
from components.grid.data_grid import DataGrid
from components.menu.home.home import HomeMenu
from components.menu.view.view import ViewMenu
from components.menu.edit.edit import EditMenu
from components.menu.script.script import ScriptMenu


class ResultViewer:
    def __init__(self, app):
        self.home_menu = HomeMenu()
        self.view_menu = ViewMenu()
        self.edit_menu = EditMenu()
        self.script_menu = ScriptMenu()
        self.data_grid = DataGrid()
        self.register_callbacks(app)

    def layout(self):
        header = html.Div(
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
                        dmc.TabsPanel(self.view_menu.layout(), value="view"),
                        dmc.TabsPanel(self.edit_menu.layout(), value="edit"),
                        dmc.TabsPanel(self.script_menu.layout(), value="script"),
                    ],
                    id="app-menu-tabs",
                    value="home",
                ),
                html.Div(id="app-menu-content"),
            ]
        )

        status = html.Div(
            [
                dcc.Store("csv-mod-time"),
                dcc.Store("refresh-route"),
                dcc.Store("purge-refresh"),
                dmc.Group(
                    [
                        dmc.Group(
                            [
                                dmc.Text(id="csv-file-path", c="gray", size="sm", ml=5),
                                dmc.ActionIcon(
                                    html.Img(
                                        src=f"assets/icons/bx-refresh.png",
                                        height="5px",
                                        width="5px",
                                        hidden=True,
                                        id="refresh-icon-img",
                                    ),
                                    id="refresh-icon",
                                    size="xs",
                                    color="green",
                                    variant="outline",
                                    disabled=True,
                                    radius=10,
                                ),
                                html.Div(id="file-mode"),
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

        return dmc.MantineProvider(
            [
                dmc.NotificationProvider(),
                html.Div(id="notifications"),
                dmc.AppShell(
                    [
                        dmc.AppShellHeader(header),
                        dmc.AppShellMain(self.data_grid.layout()),
                        dmc.AppShellFooter(
                            status,
                            mt=0,
                            pt=0,
                        ),
                    ],
                    header={"height": 80},
                ),
            ]
        )

    def register_callbacks(self, app):
        """컴포넌트별 콜백 함수 등록."""
        self.home_menu.register_callbacks(app)
        self.view_menu.register_callbacks(app)
        self.edit_menu.register_callbacks(app)
        self.script_menu.register_callbacks(app)
        self.data_grid.register_callbacks(app)
