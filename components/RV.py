import dash_flexlayout as dfl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Input, Output, html
from components.grid.data_grid import DataGrid
from components.menu.home.home import HomeMenu

from components.menu.edit.edit import EditMenu
from components.menu.analyze.analyze import AnalyzeMenu

from utils.logging_utils import logger

class ResultViewer:

    def __init__(self, app):
        self.home_menu = HomeMenu()
        # self.view_menu = ViewMenu()
        self.edit_menu = EditMenu()
        self.analyze_menu = AnalyzeMenu()
        # self.waive_menu = WaiveMenu()
        # self.script_menu = ScriptMenu()
        # self.crossprobe_menu = CrossProbeMenu()
        self.data_grid = DataGrid()
        self.register_callbacks(app)

    def layout(self):

        fl_config = {
            "global": {
                "enableSingleTabStretch": True,
                "tabEnableClose": False,
                "tabEnableFloat": False,
                "tabEnableDrag": False,
                "tabSetEnableDrop": False,
                "tabEnableRename": False,
            },
            "borders": [
                {
                    "type": "border",
                    "location": "top",
                    "selected": 0,
                    "size": 38,
                    "children": [
                        {
                            "type": "tab",
                            "name": "Home",
                            "component": "button",
                            "id": "home-item",
                        },
                        {"type": "tab", "name": "View", "id": "view-item"},
                        {
                            "type": "tab",
                            "name": "Edit",
                            "component": "text",
                            "id": "edit-item",
                        },
                        {
                            "type": "tab",
                            "name": "Waive",
                            "component": "text",
                            "id": "waive-item",
                        },
                        {
                            "type": "tab",
                            "name": "Script",
                            "component": "text",
                            "id": "script-item",
                        },
                        {
                            "type": "tab",
                            "name": "Crossprobe",
                            "component": "text",
                            "id": "crossprobe-item",
                        },
                        {
                            "type": "tab",
                            "name": "Analyze",
                            "id": "analyze-item",
                            "enableDrop": False,
                            "enableDrag": False,
                            "enableClose": False,
                            "enableFloating": False
                        },

                    ],
                }
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

        fl_nodes = [
            dfl.Tab(id="home-item", children=[self.home_menu.layout()]),
            
            dfl.Tab(id="edit-item", children=[self.edit_menu.layout()]),
            
            dfl.Tab(id="grid-tab", children=[self.data_grid.layout()]),
            
            dfl.Tab(id="col-add-tab", children=[self.edit_menu.add_column.tab_layout()]),
            dfl.Tab(id="col-del-tab", children=[self.edit_menu.del_column.tab_layout()]),
            dfl.Tab(id="row-add-tab", children=[self.edit_menu.add_row.tab_layout()]),
            dfl.Tab(id="type-changes-tab", children=[self.edit_menu.type_changes.tab_layout()]),
            dfl.Tab(id="formula-tab", children=[self.edit_menu.formula.tab_layout()]), 
            dfl.Tab(id="combine-dataframes-tab", children=[self.edit_menu.combining_dataframes.tab_layout()]),
            dfl.Tab(id="split-column-tab", children=[self.edit_menu.split_column.tab_layout()]),
            dfl.Tab(id="rename-headers-tab", children=[self.edit_menu.rename_headers.tab_layout()]),

        ]

        return dmc.MantineProvider(
            [
                dbpc.OverlayToaster(id="toaster", position="top-right", usePortal=True),
                dfl.FlexLayout(
                    id="flex-layout",
                    model=fl_config,
                    children=fl_nodes,
                    useStateForModel=False
                ),
            ]
        )

    def register_callbacks(self, app):
        """컴포넌트별 콜백 함수 등록."""
        self.home_menu.register_callbacks(app)
        self.edit_menu.register_callbacks(app)
        self.data_grid.register_callbacks(app)

        @app.callback(Output("aggrid-table", "style"), Input("flex-layout", "model"))
        def AgGrid_height(layout_config):

            if layout_config["borders"][0].get("selected", None) is None:
                top_size = 0
            else:
                top_borders = [bl for bl in layout_config["borders"] if bl.get("location") == "top"]
                top_size = top_borders[0].get("size", 0)

            bottom_borders = [bl for bl in layout_config["borders"] if bl.get("location") == "bottom"]
            bottom_size = next((bl.get("size", 50) for bl in bottom_borders if bl.get("selected", -1) == 0), 0) if bottom_borders else -30

            return {
                "height": f"calc(100vh - 150px - {top_size}px - {bottom_size}px)",
                "width": "100%",
                "overflow": "auto"
            }

        @app.callback(Input("toaster", "toasts"), prevent_initial_call=True)
        def log_toasts(toast):
            try:
                logger.info(f"SORV Alert: {toast[0]['props']['message']}")
            except:
                logger.info(f"SORV Alert: {toast}")
