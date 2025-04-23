import dash_flexlayout as dfl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Input, Output, html
from components.grid.data_grid import DataGrid
from components.menu.home.home import HomeMenu

from components.menu.edit.edit import EditMenu

from utils.logging_utils import logger


class ResultViewer:

    def __init__(self, app):
        self.home_menu = HomeMenu()
        # self.view_menu = ViewMenu()
        self.edit_menu = EditMenu()
        # self.waive_menu = WaiveMenu()
        # self.script_menu = ScriptMenu()
        # self.crossprobe_menu = CrossProbeMenu()
        self.data_grid = DataGrid()
        self.register_callbacks(app)

    def layout(self):

        fl_config = {
            "global": {
                "enableSingleTabStretch": True,
                "tabEnableClose": True,      # 탭 닫기 기능 전역 활성화
                "tabEnableFloat": False,      # 탭 플로팅 기능 전역 활성화
                "tabEnableDrag": True,       # 탭 드래그 기능 전역 활성화
                "tabSetEnableDrop": True,    # 탭 드롭 기능 전역 활성화
                "tabEnableRename": False,    # 탭 이름 변경 비활성화
                "splitterSize": 4,           # 스플리터 크기 설정
                "tabSetHeaderHeight": 32     # 탭 헤더 높이 설정
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
                            "id": "home-item",
                            "enableDrop": False,
                            "enableDrag": False,
                            "enableClose": False,
                            "enableFloating": False
                        },
                        {
                            "type": "tab", 
                            "name": "View", 
                            "id": "view-item",
                            "enableDrop": False,
                            "enableDrag": False,
                            "enableClose": False,
                            "enableFloating": False
                         },
                        {
                            "type": "tab",
                            "name": "Edit",
                            "id": "edit-item",
                            "enableDrop": False,
                            "enableDrag": False,
                            "enableClose": False,
                            "enableFloating": False
                        },
                        {
                            "type": "tab",
                            "name": "Waive",
                            "id": "waive-item",
                            "enableDrop": False,
                            "enableDrag": False,
                            "enableClose": False,
                            "enableFloating": False
                        },
                        {
                            "type": "tab",
                            "name": "Script",
                            "id": "script-item",
                            "enableDrop": False,
                            "enableDrag": False,
                            "enableClose": False,
                            "enableFloating": False
                        },
                        {
                            "type": "tab",
                            "name": "Crossprobe",
                            "id": "crossprobe-item",
                            "enableDrop": False,
                            "enableDrag": False,
                            "enableClose": False,
                            "enableFloating": False
                        },
                    ],
                    
                },
                {
                    "type": "border",
                    "location": "left",
                    # "location": "bottom",
                    "selected": 0,
                    "size": 200,
                    "children": [
                        {"type": "tab", "name": "Console", "component": "text", "id": "console-tab"},
                        {"type": "tab", "name": "Log", "component": "text", "id": "log-tab"}
                    ],
                    "show": False  # 초기에는 숨김 상태
                }

            ],
            "layout": {
                "type": "row",
                "weight": 100,
                "children": [
                {
                    "type": "tabset",
                    "weight": 80,
                    "children": [
                        {"type": "tab", "name": "DataGrid", "component": "grid", "id": "grid-tab",
                         "enableClose": False, "enableDrag": False, "enableFloat": False}
                    ],
                    "enableDrop": False,     # 메인 그리드 탭셋에 드롭 불가능
                    "enableSplit": False,    # 메인 그리드 탭셋 분할 불가능
                    "enableMaximize": True   # 최대화는 가능
                    
                },
                # {
                #     "type": "tabset",
                #     "weight": 20,
                #     "children": [
                #     {"type": "tab", "name": "Formula", "component": "text", "id": "formula-tab"},
                #     {"type": "tab", "name": "Statistics", "component": "text", "id": "statistics-tab"}
                #     ],
                #     # "show": False  # 초기에는 숨김 상태
                # }
                ]
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







