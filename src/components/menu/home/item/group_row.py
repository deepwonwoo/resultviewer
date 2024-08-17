import dash_mantine_components as dmc
from dash import Input, Output, State, html, exceptions, ctx, no_update, ALL, Patch
from components.dag.column_definitions import generate_column_definitions
from utils.db_management import WORKSPACE, USERNAME, SCRIPT, CACHE, DATAFRAME
from utils.noti_helpers import get_icon
from utils.logging_utils import logger
from components.menu.home.item.workspace_explore import FileExplorer


class groupRow:
    def layout(self):
        return dmc.Group(
            [
                dmc.Text(f"GroupRows: ", fw=500, size="sm", c="gray"),
                dmc.Tooltip(
                    dmc.ActionIcon(
                        get_icon("unfold"),
                        variant="outline",
                        id="expand-rowGroup",
                        n_clicks=0,
                        color="grey",
                    ),
                    label="Expand all groupRows",
                    withArrow=True,
                    position="bottom",
                    color="grey",
                ),
                dmc.Tooltip(
                    dmc.ActionIcon(
                        get_icon("fold"),
                        variant="outline",
                        id="collapse-rowGroup",
                        n_clicks=0,
                        color="grey",
                    ),
                    label="Collapse all groupRows",
                    withArrow=True,
                    position="bottom",
                    color="grey",
                ),
            ],
            gap=2,
        )

    def register_callbacks(self, app):

        app.clientside_callback(
            """
        function (n_clicks, grid_id) {
            if (n_clicks > 0) {
                var grid = dash_ag_grid.getApi(grid_id);
                if (grid) {
                    grid.expandAll();
                } else {
                    console.error("Grid with ID " + grid_id + " not found.");
                }
            }
            return window.dash_clientside.no_update;
        }
        """,
            Output("expand-rowGroup", "children"),
            Input("expand-rowGroup", "n_clicks"),
            State("aggrid-table", "id"),
            prevent_initial_call=True,
        )

        app.clientside_callback(
            """
        function (n_clicks, grid_id) {
            if (n_clicks > 0) {
                var grid = dash_ag_grid.getApi(grid_id);
                if (grid) {
                    grid.collapseAll();
                } else {
                    console.error("Grid with ID " + grid_id + " not found.");
                }
            }
            return window.dash_clientside.no_update;
        }
        """,
            Output("collapse-rowGroup", "children"),
            Input("collapse-rowGroup", "n_clicks"),
            State("aggrid-table", "id"),
            prevent_initial_call=True,
        )
