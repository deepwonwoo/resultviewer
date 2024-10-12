from dash import Input, Output, State, no_update
from utils.db_management import SSDF
from utils.logging_utils import logger


class ColumnOrder:
    def register_callbacks(self, app):
        @app.callback(
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("aggrid-table", "columnState"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True,
        )
        def move_column_order(column_state, col_defs):
            if SSDF.dataframe is None:
                return no_update

            state_order = [
                col["colId"]
                for col in column_state
                if col["colId"] != "ag-Grid-AutoColumn"
            ]
            def_order = [col["field"] for col in col_defs]

            if state_order == def_order:
                return no_update

            try:
                SSDF.dataframe = SSDF.dataframe.select(["uniqid"] + state_order)
            except Exception as e:
                logger.error(f"컬럼 상태(순서) 변경 실패: {e}")
            return no_update
