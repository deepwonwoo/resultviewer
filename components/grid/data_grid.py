import flask
import polars as pl
import dash_ag_grid as dag
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Input, Output, State, html, dcc, no_update, exceptions
from components.grid.dag.column_definitions import DEFAULT_COL_DEF
from components.grid.dag.server_side_operations import extract_rows_from_data
from components.grid.dag.column_definitions import determine_column_type
from dash_extensions import EventListener

from utils.db_management import SSDF
from utils.logging_utils import logger
from utils.config import CONFIG

class DataGrid:

    DASH_GRID_OPTIONS = {
        "rowHeight": 24,
        "headerHeight": 30,
        "cacheBlockSize": 1000,
        "maxBlocksInCache": 3,
        "blockLoadDebounceMillis": 100,
        "enableCharts": True,
        "undoRedoCellEditing": True,
        "enableRangeSelection": True,
        "enableAdvancedFilter": True,
        "rowGroupPanelShow": "always",
        "groupAllowUnbalanced": True,
        "suppressMultiRangeSelection": False,
        "groupLockGroupColumns": 0,
        "getChildCount": {"function": "getChildCount(params)"},
        "treeData": False,
        "rowSelection": "multiple",
        "suppressRowClickSelection": True,
        "purgeClosedRowNodes": True,
        "includeHiddenColumnsInAdvancedFilter": True,
        "isServerSideGroup": {"function": "params ? params.group : null"},
        "getServerSideGroupKey": {"function": "params ? params.tree_group : null"},
        "autoGroupColumnDef": {"field": "tree_group"},
        "sideBar": {
            "toolPanels": [
                {
                    "id": "columns",
                    "labelDefault": "Columns",
                    "labelKey": "columns",
                    "iconKey": "columns",
                    "toolPanel": "agColumnsToolPanel",
                }
            ],
            "defaultToolPanel": None,
        },
        "statusBar": {"statusPanels": [{"statusPanel": "agAggregationComponent"}]},
    }

    def layout(self) -> EventListener:
        events = [
            {
                "event": "mousedown",
                "props": [
                    "altKey",
                    "ctrlKey",
                    "shiftKey",
                    "srcElement.innerText",
                    "srcElement.attributes.col-id.nodeValue",
                    "button",
                ],
            }
        ]

        return html.Div(
            [
                dcc.Store("pre-defined-view"),
                dcc.Store("csv-mod-time"),
                dcc.Store("refresh-route"),
                dcc.Store("purge-refresh"),
                dcc.Store("cp_selected_rows"),
                dcc.Store("waiver_selected_rows"),
                dcc.Store("sub_info_selected_rows"),

                # CSS 파일 로드
                html.Link(rel='stylesheet', href='/assets/custom.css'),

                EventListener(
                    id="el",
                    children=dag.AgGrid(
                        id="aggrid-table",
                        selectedRows=[],
                        columnDefs=[],
                        defaultColDef=DEFAULT_COL_DEF,
                        enableEnterpriseModules=True,
                        rowModelType="serverSide",
                        dashGridOptions=self.DASH_GRID_OPTIONS,
                        style={
                            "height": "calc(100vh - 180px - 25px)",
                            "width": "100%",
                            "overflow": "auto",
                        },
                    ),
                    events=events,
                    logging=False,
                ),
                dmc.Group(
                    [
                        html.Div("Total Rows:", id="total-row-count"),
                        html.Div(id="row-counter"),
                        html.Div(id="waiver-counter"),
                        dmc.Tooltip(
                            dbpc.Button(
                                id="refresh-waiver-counter-btn",
                                icon="refresh",
                                small=True,
                                minimal=True,
                                outlined=True,
                                style={"display": "none"},
                            ),
                            label="Refresh Waiver Counter",
                            position="top",
                            color="grey",
                        ),
                    ],
                    justify="flex-end",
                    py=0,
                    my=0,
                    style={
                        "backgroundColor": "#fcfcfc",
                        "borderBottom": "3px solid #aaaaaa",
                    },
                ),
            ]
        )

    def register_callbacks(self, app):
        @app.server.route("/api/serverData", methods=["POST"])
        def serverData():
            data = flask.request.json
            response = extract_rows_from_data(data["request"])
            counter_info = self._generate_counter_info()
            return flask.jsonify({"response": response, "counter_info": counter_info})

        app.clientside_callback(
            """
            async function initializeGrid(id, columnDefs) {
                const MAX_ATTEMPTS = 20;
                const DELAY_DURATION = 100;

                async function delay(ms) {
                    return new Promise(resolve => setTimeout(resolve, ms));
                }

                async function getGrid(id) {
                    for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
                        try {
                            const grid = dash_ag_grid.getApi(id);
                            if (grid) return grid;
                        } catch (error) {
                            console.warn(`Attempt ${attempt + 1}: Error fetching grid API:`, error);
                        }
                        await delay(DELAY_DURATION);
                    }
                    throw new Error("Failed to initialize grid API after multiple attempts.");
                }

                try {
                    const grid = await getGrid(id);
                    const datasource = createServerSideDatasource();
                    grid.updateGridOptions({ serverSideDatasource: datasource });
                    console.log("Grid initialized successfully");
                } catch (error) {
                    console.error(error.message);
                }

                return window.dash_clientside.no_update;
            }
            """,
            Output("row-counter", "children"),
            [Input("aggrid-table", "id"), Input("aggrid-table", "columnDefs")],
            prevent_initial_call=True,
        )

        # middel click
        app.clientside_callback(
            """
            function(gridId) {
                dash_ag_grid.getApiAsync(gridId).then((grid) => {
                    grid.addEventListener('cellMouseDown', (e) => {
                        if (e.event.button == 1) {
                            e.api.setNodesSelected({nodes: [e.node], newValue: true})
                        } 
                    })
                })
                return dash_clientside.no_update
            }
            """,
            Output("aggrid-table", "id", allow_duplicate=True),
            Input("aggrid-table", "id"),
        )

        @app.callback(
            Output("aggrid-table", "selectedRows", allow_duplicate=True),
            Output("cp_selected_rows", "data", allow_duplicate=True),
            Output("waiver_selected_rows", "data", allow_duplicate=True),
            Output("sub_info_selected_rows", "data", allow_duplicate=True),
            Input("aggrid-table", "selectedRows"),
            prevent_initial_call=True,
        )
        def get_selected_row(selected_rows):
            print("get_selected_row", selected_rows)
            return [], selected_rows, selected_rows, selected_rows

        @app.callback(
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("aggrid-table", "columnState"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True,
        )
        def move_column_order(column_state, col_defs):
            if SSDF.dataframe is None:
                return no_update

            state_order = [col["colId"] for col in column_state if col["colId"] != "ag-Grid-AutoColumn"]
            def_order = [col["field"] for col in col_defs]

            if state_order == def_order:
                return no_update

            try:
                SSDF.dataframe = SSDF.dataframe.select(["uniqid"] + state_order)
            except Exception as e:
                logger.error(f"컬럼 상태(순서) 변경 실패: {e}")
            return no_update




        # 컬럼 editable 속성 변경 처리를 위한 콜백 추가
        @app.callback(
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("aggrid-table", "cellRendererData"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True
        )
        def update_column_editable(cell_data, column_defs):
            """cellRendererData를 통해 headerComponent에서 전송된 editable 변경 처리"""
            if not cell_data or "action" not in cell_data or cell_data["action"] != "toggle_editable":
                return no_update
            
            col_id = cell_data.get("colId")
            editable = cell_data.get("value", False)
            
            if not col_id:
                return no_update
            
            # 해당 컬럼 정의 찾기 및 업데이트
            for col in column_defs:
                if col["field"] == col_id:
                    col["editable"] = editable
                    col["cellClass"] = "text-dark editable-column" if editable else "text-secondary"
                    break
                
            return column_defs


        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("refresh-route", "data", allow_duplicate=True),
            Output("refresh-waiver-counter-btn", "n_clicks", allow_duplicate=True),
            Input("aggrid-table", "cellValueChanged"),
            prevent_initial_call=True,
        )
        def apply_edit(cell_changed):
            if not cell_changed:
                raise exceptions.PreventUpdate
            dff = SSDF.dataframe
            route = []
            propagate_same_columns = ["uniqid"] if SSDF.propa_rule is None else SSDF.propa_rule

            count = 0
            for cell in cell_changed:
                target_col = cell["colId"]
                new_value = cell["value"]
                uid = cell["data"]["uniqid"]
                propa_rule = ["uniqid"] if target_col != "waiver" else propagate_same_columns

                if not cell["data"].get("group"):
                    if count == 0:
                        for rule in propa_rule:
                            if not rule in dff.columns:
                                return [dbpc.Toast(message=f"No '{rule}' in data. Please re-define propagation rule.",intent="warning",icon="warning-sign")],[],no_update
                        request = SSDF.request
                        if SSDF.tree_mode:
                            route = cell["data"].get(SSDF.tree_col).split(".")
                        elif request.get("rowGroupCols"):
                            groupBy = [col["id"] for col in request.get("rowGroupCols", [])]
                            route = [cell["data"].get(group) for group in groupBy]
                        else:
                            route = []
                        count = 1

                    conditions_expr = pl.lit(True)
                    for col in propa_rule:
                        colType = determine_column_type(dff[col])
                        if colType == "numeric":
                            conditions_expr = conditions_expr & (dff[col].round(3) == round(cell["data"][col] + 0.0000001, 3))
                        else:
                            conditions_expr = conditions_expr & (dff[col] == cell["data"][col])

                    update_target_column = (pl.when(conditions_expr).then(pl.lit(new_value)).otherwise(pl.col(target_col)).alias(target_col))
                    dff = dff.with_columns(update_target_column)
                    if (target_col == "waiver") and ("user" in dff.columns):
                        update_user_column = (pl.when(conditions_expr).then(pl.lit(CONFIG.USERNAME + "(propagated)")).otherwise(pl.col("user")).alias("user"))
                        dff = dff.with_columns(update_user_column)
                        dff = dff.with_columns((pl.when(pl.col("uniqid") == uid).then(pl.lit(CONFIG.USERNAME)).otherwise(pl.col("user"))).alias("user"))
                else:
                    continue

            SSDF.dataframe = dff

            return no_update, route, 1
            
            
            

        app.clientside_callback(
        """
        function (data, grid_id) {
            for (; data.length > 0; ) {
                dash_ag_grid.getApi(grid_id).refreshServerSide({route: data});
                data.pop();
            }
            dash_ag_grid.getApi(grid_id).refreshServerSide({route: data});
        }
        """,
        Input("refresh-route", "data"),
        State("aggrid-table", "id"),
        prevent_initial_call=True,
        )






    @staticmethod
    def _generate_counter_info() -> str:
        counter_names = ["filtered", "groupby"]
        counter_info = ""
        for name in counter_names:
            row_count = SSDF.get_row_count(name)
            if row_count:
                counter_info += f"{name.capitalize()}: {row_count}    "
        return counter_info.rstrip()








