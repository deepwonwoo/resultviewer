import dash_mantine_components as dmc
from dash import Input, Output, ctx, no_update, callback
from utils.logging_utils import logger


class ColumnSizer:
    def layout(self):
        return dmc.Group(
            [
                dmc.Text("ColumnSize: ", fw=500, size="sm", c="gray"),
                self._create_tooltip("column-auto", "Fit content"),
                self._create_tooltip("column-fit", "Fit grid width"),
            ],
            gap=2,
        )

    def _create_tooltip(self, id, label):
        return dmc.Tooltip(
            dmc.ActionIcon(variant="outline", id=id, n_clicks=0, color="grey"),
            label=label,
            withArrow=True,
            position="bottom",
            color="grey",
        )

    def register_callbacks(self, app):
        @callback(
            Output("aggrid-table", "columnSize"),
            Output("notifications", "children", allow_duplicate=True),
            Input("column-auto", "n_clicks"),
            Input("column-fit", "n_clicks"),
            prevent_initial_call=True,
        )
        def column_sizing(n1: int, n2: int) -> tuple:
            try:
                icon_clicked = ctx.triggered_id
                if icon_clicked in ["column-auto", "column-fit"]:
                    size_type = (
                        "autoSize" if icon_clicked == "column-auto" else "sizeToFit"
                    )
                    logger.info(
                        f"{'Auto-sizing' if size_type == 'autoSize' else 'Fitting'} columns"
                    )
                    return size_type, None
            except Exception as e:
                logger.error(f"Error in column_sizing: {str(e)}")
                return no_update, create_notification(
                    f"Error: {str(e)}", "Column Sizing Error", "red"
                )
