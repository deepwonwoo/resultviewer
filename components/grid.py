import flask
import dash_ag_grid as dag
from dash import Input, Output, html, dcc
from typing import Dict, Any
from components.dag.column_definitions import DEFAULT_COL_DEF
from components.dag.server_side_operations import extract_rows_from_data
from utils.db_management import ROW_COUNTER
from dash_extensions import EventListener

class DataGrid:
    DASH_GRID_OPTIONS: Dict[str, Any] = {
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
            "toolPanels": [{"id": "columns", "labelDefault": "Columns", "labelKey": "columns", "iconKey": "columns", "toolPanel": "agColumnsToolPanel"}],
            "defaultToolPanel": None,
        },
        "statusBar": {"statusPanels": [{"statusPanel": "agAggregationComponent"}]}
    }

    def layout(self) -> EventListener:
        events = [{
            "event": "mousedown",
            "props": ["altKey", "ctrlKey", "shiftKey", "srcElement.innerText", "srcElement.attributes.col-id.nodeValue", "button"],
        }]

        return html.Div([
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
                    style={"height": "88vh", "width": "100%", "overflow": "auto"},
                ),
                events=events,
                logging=False,
            ),
        ])

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

    @staticmethod
    def _generate_counter_info() -> str:
        return " ".join([
            f"{key.capitalize()}: {value}" 
            for key, value in ROW_COUNTER.items() 
            if value
        ])
