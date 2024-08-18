import dash_mantine_components as dmc
from dash import Input, Output, State, html, exceptions, ctx, no_update, ALL, Patch, callback
from components.dag.column_definitions import generate_column_definitions
from utils.db_management import WORKSPACE, USERNAME, SCRIPT, CACHE, DATAFRAME
from utils.logging_utils import logger
from components.menu.home.item.workspace_explore import FileExplorer
from utils.noti_helpers import get_icon, create_notification
from typing import Dict, Any, List
import json

class ColumnSizer:
    def layout(self):
        return dmc.Group(
            [
                dmc.Text(f"ColumnSize: ", fw=500, size="sm", c="gray"),
                dmc.Tooltip(
                    dmc.ActionIcon(variant="outline", id="column-auto", n_clicks=0, color="grey"),
                    label="Fit content",
                    withArrow=True,
                    position="bottom",
                    color="grey",
                ),
                dmc.Tooltip(
                    dmc.ActionIcon(variant="outline", id="column-fit", n_clicks=0, color="grey"),
                    label="Fit grid width",
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
            Output("notifications", "children", allow_duplicate=True),
            Input("column-auto", "n_clicks"),
            Input("column-fit", "n_clicks"),
            prevent_initial_call=True,
        )
        def column_sizing(n1: int, n2: int) -> tuple:
            try:
                icon_clicked = ctx.triggered_id
                if icon_clicked == "column-auto":
                    logger.info("Auto-sizing columns")
                    return "autoSize", None
                elif icon_clicked == "column-fit":
                    logger.info("Fitting columns to grid width")
                    return "sizeToFit", None
            except Exception as e:
                logger.error(f"Error in column_sizing: {str(e)}")
                return no_update, create_notification(f"Error: {str(e)}", "Column Sizing Error", "red")
