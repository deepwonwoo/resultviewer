import polars as pl
import dash_mantine_components as dmc
from dash import *
from utils.process_helpers import create_notification
from utils.process_helpers import displaying_df
from utils.process_helpers import get_icon
from utils.db_management import DATAFRAME, CACHE, USERNAME
from components.dag.column_definitions import (
    generate_column_definitions,
    generate_column_definition,
)
from utils.logging_utils import logger


class columnOrder:

    def register_callbacks(self, app):

        @app.callback(
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("aggrid-table", "columnState"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True,
        )
        def move_column_order(columnState, colDefs):
            if DATAFRAME.get("df") is None:
                return no_update

            state_order = [col["colId"] for col in columnState if col["colId"] != "ag-Grid-AutoColumn"]
            def_order = [col["field"] for col in colDefs]

            if state_order == def_order:
                return no_update

            colDefs_dict = {}
            for col in colDefs:
                colDefs_dict[col["field"]] = col

            try:
                DATAFRAME["df"] = DATAFRAME["df"].select(
                    ["uniqid"] + [col.get("colId") for col in columnState if col.get("colId") != "ag-Grid-AutoColumn"]
                )
            except Exception as e:
                logger.error(f"Fail to change column state(order) : {e}")
            return no_update
