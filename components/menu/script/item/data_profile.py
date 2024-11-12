import os
import dash_mantine_components as dmc
from dash import Input, Output, html, exceptions
from utils.data_processing import displaying_df
from utils.component_template import get_icon, create_notification


class PandasProfile:

    def __init__(self) -> None:
        pass

    def layout(self):
        return html.Div(
            [
                dmc.Button(
                    "Profile",
                    id="profile-btn",
                    leftSection=get_icon("bxs-analyse"),
                    variant="outline",
                    color="indigo",
                    size="xs",
                ),
                dmc.Modal(html.Div(id="profile-body"), id="profile-modal", size="85%", zIndex=1000, opened=False),
            ]
        )

    def register_callbacks(self, app):

        app.clientside_callback(
            """
            function updateLoadingState(n_clicks) {
                return true
            }
            """,
            Output("profile-btn", "loading", allow_duplicate=True),
            Input("profile-btn", "n_clicks"),
            prevent_initial_call=True,
        )

        @app.callback(
            Output("profile-modal", "opened"),
            Output("profile-body", "children"),
            Output("profile-btn", "loading"),
            Output("notifications", "children", allow_duplicate=True),
            Input("profile-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def profile_editor(n_clicks):
            if n_clicks is None:
                raise exceptions.PreventUpdate
            try:
                dff = displaying_df(filtred_apply=True)
                if dff is None:
                    return (False, None, False, create_notification(message="No Dataframe loaded", position="center"))

                import pandas as pd
                import matplotlib

                matplotlib.use("svg")
                import ydata_profiling as yp

                profile = yp.ProfileReport(pd.DataFrame(dff), progress_bar=False)
                file_path = os.path.dirname(os.path.realpath(__file__))
                assets_dir = os.path.join(file_path, "../../../../assets")
                profile.to_file(f"{assets_dir}/profile.html")
                profile = html.Iframe(src=f"/assets/profile.html", style={"height": "1067px", "width": "100%"})
                return True, profile, False, None
            except Exception as e:
                False, None, False, create_notification(message=str(e))
