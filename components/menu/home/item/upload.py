import os
import subprocess
import dash_mantine_components as dmc
from dash import html, Output, Input, State, Patch, no_update, exceptions
from components.grid.dag.column_definitions import generate_column_definitions

from utils.config import CONFIG
from utils.db_management import SSDF
from utils.component_template import create_notification, get_icon
from utils.data_processing import file2df, validate_df
from utils.file_operations import make_dirs_with_permissions
from utils.logging_utils import debugging_decorator


class Uploader:
    def __init__(self) -> None:
        self.init_csv = SSDF.init_csv

    def layout(self):
        return html.Div([self.open_menu(), self.local_modal()])

    def open_menu(self):
        return dmc.Menu(
            [
                dmc.MenuTarget(dmc.Button("Open", variant="outline", color="indigo", size="xs", id="open-data-btn")),
                dmc.MenuDropdown([dmc.MenuItem("Local", id="open-local-btn", n_clicks=0, leftSection=get_icon("bx-folder-open"))]),
            ],
            trigger="hover",
        )

    def local_modal(self):
        return dmc.Modal(
            title="File Open from Local",
            id="local-file-open-modal",
            centered=True,
            opened=True if self.init_csv else False,
            size="60%",
            children=[
                dmc.TextInput(
                    value=self.init_csv,
                    label="type in the path of CSV file to Open",
                    leftSection=dmc.ActionIcon(get_icon("bx-file-find"), id="open-csv-file-search", variant="subtle", n_clicks=0),
                    rightSection=dmc.Button("Open", id="open-csv-local-btn", style={"width": 100}, n_clicks=0),
                    rightSectionWidth=100,
                    required=True,
                    id="open-csv-path-input",
                )
            ],
        )

    def register_callbacks(self, app):
        self._register_local_save_callback(app)

    def _register_local_save_callback(self, app):

        @app.callback(
            Output("open-csv-path-input", "value", allow_duplicate=True),
            Input("open-csv-file-search", "n_clicks"),
            prevent_initial_call=True,
        )
        def get_open_file_path(n):
            cmd = f"{CONFIG.SCRIPT}/QFileDialog/file_dialog"
            result = subprocess.run([cmd], capture_output=True, text=True)
            file_path = result.stdout.strip()
            return file_path if file_path else no_update

        @app.callback(
            Output("local-file-open-modal", "opened", allow_duplicate=True),
            Input("open-local-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def open_local_modal(open_n):
            return True

        app.clientside_callback(
            """
            function updateLoadingState(n_clicks) {
                return true
            }
            """,
            Output("open-csv-local-btn", "loading", allow_duplicate=True),
            Input("open-csv-local-btn", "n_clicks"),
            prevent_initial_call=True,
        )

        @app.callback(
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("aggrid-table", "dashGridOptions", allow_duplicate=True),
            Output("total-row-count", "children", allow_duplicate=True),
            Output("flex-layout", "model", allow_duplicate=True),
            Output("csv-mod-time", "data", allow_duplicate=True),
            Output("notifications", "children", allow_duplicate=True),
            Output("local-file-open-modal", "opened", allow_duplicate=True),
            Output("open-csv-local-btn", "loading"),
            Input("open-csv-local-btn", "n_clicks"),
            State("open-csv-path-input", "value"),
            prevent_initial_call=True,
        )
        def local_modal(open_n, open_file_path):
            file_path = ""
            if open_n == 0 and self.init_csv:
                file_path = self.init_csv

            elif open_n > 0 and open_file_path:
                file_path = open_file_path.strip()

            if file_path:
                try:
                    df = file2df(file_path)
                    patched_dashGridOptions = Patch()
                    patched_dashGridOptions["treeData"] = False

                except Exception as e:
                    noti = create_notification(message=f"Read Data Error: {e}", position="center")
                    return (no_update, no_update, no_update, no_update, no_update, noti, False, False)
                mod_time = os.path.getmtime(file_path)
                patched_layout_model = Patch()
                patched_layout_model["layout"]["children"][0]["children"][0]["name"] = file_path

                return (
                    generate_column_definitions(df),
                    patched_dashGridOptions,
                    f"Total Rows: {len(df)}",
                    patched_layout_model,
                    mod_time,
                    None,
                    False,
                    False,
                )

            return (no_update, no_update, no_update, no_update, no_update, None, no_update, False)
