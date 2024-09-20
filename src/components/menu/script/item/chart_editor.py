import dash_chart_editor as dce
import dash_mantine_components as dmc
from dash import Input, Output, State, html, exceptions, ctx, no_update, ALL, Patch
from components.dag.column_definitions import generate_column_definitions
from utils.db_management import WORKSPACE, USERNAME, SCRIPT, CACHE, DATAFRAME
from utils.component_template import get_icon, create_notification
from utils.dataframe_operations import displaying_df
from utils.logging_utils import logger
from components.menu.home.item.workspace_explore import FileExplorer


class ChartEditor:
    def __init__(self) -> None:
        self.df_max_size = 100 * 1024 * 1024  # 100 MB

    def layout(self):
        return html.Div(
            [
                dmc.Button(
                    "ChartEditor",
                    id="chart-btn",
                    leftSection=get_icon("bx-chart"),
                    variant="outline",
                    color="indigo",
                    size="xs",
                ),
                dmc.Modal(
                    html.Div(id="chart-body"),
                    id="chart-modal",
                    size="85%",
                    zIndex=1000,
                    opened=False,
                ),
            ]
        )

    def register_callbacks(self, app):

        app.clientside_callback(
            """
            function updateLoadingState(n_clicks) {
                return true
            }
            """,
            Output("chart-btn", "loading", allow_duplicate=True),
            Input("chart-btn", "n_clicks"),
            prevent_initial_call=True,
        )

        @app.callback(
            Output("chart-modal", "opened"),
            Output("chart-body", "children"),
            Output("chart-btn", "loading"),
            Output("notifications", "children", allow_duplicate=True),
            Input("chart-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def chart_editor(n_clicks):
            if n_clicks is None:
                raise exceptions.PreventUpdate

            try:
                dff = displaying_df(filtred_apply=True)
                if dff is None:
                    return False, None, False, create_notification(message="No Dataframe loaded", position="center")

                df_size = dff.estimated_size()

                if df_size > self.df_max_size:
                    return (
                        False,
                        None,
                        False,
                        create_notification(message="Data is too big (should be less than 100 MB)", position="center"),
                    )

                dce_output = dce.DashChartEditor(dataSources=dff.to_dict(as_series=False))
                return True, dce_output, False, None

            except Exception as e:
                False, None, False, create_notification(str(e))
