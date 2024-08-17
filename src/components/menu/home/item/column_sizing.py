import dash_mantine_components as dmc
from dash import Input, Output, State, html, exceptions, ctx, no_update, ALL, Patch
from components.dag.column_definitions import generate_column_definitions
from utils.db_management import WORKSPACE, USERNAME, SCRIPT, CACHE, DATAFRAME
from utils.logging_utils import logger
from components.menu.home.item.workspace_explore import FileExplorer


class ColumnSizer:
    def layout(self):
        return dmc.Group(
            [
                dmc.Text(f"ColumnSize: ", fw=500, size="sm", c="gray"),
                dmc.Tooltip(
                    dmc.ActionIcon(variant="outline", id="column-auto", n_clicks=0, color="grey"),
                    label="columnSize fit content",
                    withArrow=True,
                    position="bottom",
                    color="grey",
                ),
                dmc.Tooltip(
                    dmc.ActionIcon(variant="outline", id="column-fit", n_clicks=0, color="grey"),
                    label="columnSize fit width of the grid",
                    withArrow=True,
                    position="bottom",
                    color="grey",
                ),
            ],
            gap=2,
        )

    def register_callbacks(self, app):
        @app.callback(
            Output("aggrid-table", "columnSize"),
            Input("column-auto", "n_clicks"),
            Input("column-fit", "n_clicks"),
            prevent_initial_call=True,
        )
        def column_sizing(n1, n2):
            icon_clicked = ctx.triggered_id
            if icon_clicked == "column-auto":
                return "autoSize"
            elif icon_clicked == "column-fit":
                return "sizeToFit"
