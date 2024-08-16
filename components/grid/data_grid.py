import flask
import dash_ag_grid as dag
from dash import Input, Output, no_update
from components.grid.DAG.columnDef import defaultColDef
from components.grid.DAG.serverSide import extract_rows_from_data
from utils.db_management import ROW_COUNTER, DATAFRAME
from utils.logging_config import logger
from dash_extensions import EventListener


class DataGrid:
    def layout(self):
        dash_grid_options = {
            "rowHeight": 24,
            "headerHeight": 30,
            "cacheBlockSize": 1000,  # This sets the block size to 1000
            "maxBlocksInCache": 3,  # This means the grid will keep two blocks in memory only
            "blockLoadDebounceMillis": 100,  # loading of blocks is delayed by 100ms
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
            "autoGroupColumnDef": {
                "field": "tree_group",
            },
            "sideBar": {
                "toolPanels": [
                    {
                        "id": "columns",
                        "labelDefault": "Columns",
                        "labelKey": "columns",
                        "iconKey": "columns",
                        "toolPanel": "agColumnsToolPanel",
                    },
                ],
                "defaultToolPanel": None,
            },
            "statusBar": {
                "statusPanels": [
                    {
                        "statusPanel": "agAggregationComponent",
                    }
                ]
            },
        }
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

        return EventListener(
            id="el",
            children=dag.AgGrid(
                id="aggrid-table",
                selectedRows=[],
                columnDefs=[],
                defaultColDef=defaultColDef,
                enableEnterpriseModules=True,
                rowModelType="serverSide",
                persisted_props=["filterModel"],
                dashGridOptions=dash_grid_options,
                style={"height": "88vh", "width": "100%", "overflow": "auto"},
            ),
            events=events,
            logging=False,
        )

    def register_callbacks(self, app):

        @app.server.route("/api/serverData", methods=["POST"])
        def serverData():
            data = flask.request.json
            request = data["request"]
            response = extract_rows_from_data(request)
            counter_info = ""
            if ROW_COUNTER.get("filtered"):
                counter_info += f"Filterd: {ROW_COUNTER['filtered']}"
            if ROW_COUNTER.get("groupby"):
                counter_info += f"   GroupRows: {ROW_COUNTER['groupby']}"
            if ROW_COUNTER.get("waived"):
                counter_info += f"   Waived: {ROW_COUNTER['waived']}"

            return flask.jsonify({"response": response, "counter_info": counter_info})

        app.clientside_callback(
            """
            async function (id, columnDefs) {
                const delay = ms => new Promise(res => setTimeout(res, ms));
                

                const getGrid = async (id) => {
                    let grid;
                    let count = 0;
                    const maxAttempts = 20;
                    const delayDuration = 200; // milliseconds

                    while (!grid && count < maxAttempts) {
                        await delay(delayDuration);
                        try {
                            grid = dash_ag_grid.getApi(id);
                        } catch (error) {
                            // Optionally log the error
                            console.error("Error fetching grid API:", error);
                        }
                        count++;
                    }
                    return grid;
                };

                const grid = await getGrid(id);
                if (grid) {
                    const datasource = createServerSideDatasource();
                    grid.updateGridOptions({ serverSideDatasource: datasource });
                } else {
                    console.error("Failed to initialize grid API after multiple attempts.");
                }

                return window.dash_clientside.no_update;
            }
            """,
            Output("row-counter", "children"),
            [
                Input("aggrid-table", "id"),
                Input("aggrid-table", "columnDefs"),
            ],
            prevent_initial_call=True,
        )

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Input("notifications", "children"),
            prevent_initial_call=True,
        )
        def refresh_noti(n):
            return None
