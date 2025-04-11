import flask
import dash_ag_grid as dag
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Input, Output, State, html, dcc, no_update
from components.grid.dag.column_definitions import DEFAULT_COL_DEF
from components.grid.dag.server_side_operations import extract_rows_from_data
from dash_extensions import EventListener

# from utils.component_template import get_icon
from utils.db_management import SSDF
from utils.logging_utils import logger


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

    @staticmethod
    def _generate_counter_info() -> str:
        counter_names = ["filtered", "groupby"]
        counter_info = ""
        for name in counter_names:
            row_count = SSDF.get_row_count(name)
            if row_count:
                counter_info += f"{name.capitalize()}: {row_count}    "
        return counter_info.rstrip()
