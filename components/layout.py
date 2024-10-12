import time
import dash_flexlayout as dfl
import dash_mantine_components as dmc
from dash import Input, Output, html, dcc
from components.grid.data_grid import DataGrid
from components.menu.home.home import HomeMenu
# from components.menu.view.view import ViewMenu
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
        layout_config = {
            "global": {
                "enableSingleTabStretch": True,
                "tabEnableClose": False,
                "tabEnableFloat": False,
                "tabEnableDrag": False,
                "tabEnableRename": False,
            },
            "borders": [
                {
                    "type": "border",
                    "location": "top",
                    "selected": 0,
                    "size": 50,
                    "children": [
                        {
                            "type": "tab",
                            "name": "Home",
                            "component": "button",
                            "id": "home-item",
                        },
                        {
                            "type": "tab",
                            "name": "View",
                            "id": "view-item",
                        },
                        {
                            "type": "tab",
                            "name": "Edit",
                            "component": "text",
                            "id": "edit-item",
                        },
                        {
                            "type": "tab",
                            "name": "Script",
                            "component": "text",
                            "id": "script-item",
                        },
                    ],
                },
            ],
            "layout": {
                "type": "row",
                "weight": 100,
                "children": [
                    {
                        "type": "tabset",
                        "children": [
                            {
                                "type": "text",
                                "name": "DataGrid",
                                "component": "grid",
                                "id": "grid-tab",
                            }
                        ],
                    }
                ],
            },
        }
        nodes = [
            dfl.Tab(id="home-item", children=[self.home_menu.layout()]),
            #dfl.Tab(id="view-item", children=[self.view_menu.layout()]),
            dfl.Tab(id="edit-item", children=[self.edit_menu.layout()]),
            dfl.Tab(id="script-item", children=[self.script_menu.layout()]),
            dfl.Tab(id="grid-tab", children=[self.data_grid.layout()]),
            dfl.Tab(id="sub-info", children=[self.subInfo()]),
        ]
        return dmc.MantineProvider(
            [
                dmc.NotificationProvider(),
                html.Div(id="notifications"),
                dcc.Interval(id="check-update-interval", interval=5000),
                dfl.FlexLayout(
                    id="flex-layout",
                    model=layout_config,
                    children=nodes,
                    useStateForModel=False,
                ),
            ]
        )

    def subInfo(self):
        return dmc.Grid(
            children=[
                dmc.GridCol(
                    dmc.ScrollArea(id="footerLeft", scrollbarSize=6, type="auto"),
                    span=3,
                ),
                dmc.GridCol(id="footerRight", span="auto"),
            ]
        )

    def register_callbacks(self, app):
        self.home_menu.register_callbacks(app)
        # self.view_menu.register_callbacks(app)
        self.edit_menu.register_callbacks(app)
        self.script_menu.register_callbacks(app)
        self.data_grid.register_callbacks(app)

        @app.callback(Output("aggrid-table", "style"), Input("flex-layout", "model"))
        def flex_layout(layout_config):
            bottom_borders = [
                bl for bl in layout_config["borders"] if bl.get("location") == "bottom"
            ]
            bottom_size = (
                next(
                    (
                        bl.get("size", 50)
                        for bl in bottom_borders
                        if bl.get("selected", -1) == 0
                    ),
                    0,
                )
                if bottom_borders
                else -30
            )
            style = {
                "height": f"calc(100vh - 180px - 25px - {bottom_size}px)",
                "width": "100%",
                "overflow": "auto",
            }
            return style

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Input("notifications", "children"),
            prevent_initial_call=True,
        )
        def refresh_noti(n):
            time.sleep(0.1)
            return None
