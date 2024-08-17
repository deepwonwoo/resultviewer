import os
import datetime
import shutil
import subprocess
import dash_mantine_components as dmc
from dash import Input, Output, State, html, exceptions, ctx, no_update, ALL, Patch
from components.dag.column_definitions import generate_column_definitions
from utils.db_management import WORKSPACE, USERNAME, SCRIPT, CACHE, DATAFRAME
from utils.noti_helpers import create_notification, get_icon
from utils.file_operations import backup_file
from utils.dataframe_operations import file2df
from utils.logging_utils import logger, debugging_decorator
from components.menu.home.item.workspace_explore import FileExplorer


class Uploader:
    def __init__(self) -> None:
        self.explorer = FileExplorer()
        self.cp_info = CACHE.get("CP")
        self.init_csv = CACHE.get("init_csv", "")

    def layout(self):
        return html.Div(
            [
                dmc.Menu(
                    [
                        dmc.MenuTarget(
                            dmc.Button(
                                "Open",
                                variant="outline",
                                color="indigo",
                                size="xs",
                                id="open-data-btn",
                            )
                        ),
                        dmc.MenuDropdown(
                            [
                                dmc.MenuItem(
                                    "Local",
                                    id="open-local-btn",
                                    n_clicks=0,
                                    leftSection=get_icon("bx-folder-open"),
                                ),
                                dmc.MenuItem(
                                    "WORKSPACE",
                                    id="open-workspace-btn",
                                    n_clicks=0,
                                    leftSection=get_icon("bx-cloud-download"),
                                ),
                            ]
                        ),
                    ],
                    trigger="hover",
                ),
                self.local_modal(),
                self.drawer(),
            ]
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
                    leftSection=dmc.ActionIcon(
                        get_icon("bx-file-find"),
                        id="open-csv-file-search",
                        variant="subtle",
                        n_clicks=0,
                    ),
                    rightSection=dmc.Button(
                        "Open",
                        id="open-csv-local-btn",
                        style={"width": 100},
                        n_clicks=0,
                    ),
                    rightSectionWidth=100,
                    required=True,
                    id="open-csv-path-input",
                )
            ],
        )

    def drawer(self):

        workspace_upload_layout = dmc.Accordion(
            children=[
                dmc.AccordionItem(
                    [
                        dmc.AccordionControl(
                            "Upload Data to Workspace",
                            icon=get_icon("bx-cloud-upload"),
                        ),
                        dmc.AccordionPanel(
                            [
                                dmc.Alert(
                                    [
                                        dmc.Group(
                                            [
                                                dmc.TextInput(
                                                    id="upload-library-name",
                                                    size="xs",
                                                    label="Folder #1",
                                                    placeholder="Library",
                                                    value=self.cp_info["lib"],
                                                ),
                                                dmc.TextInput(
                                                    id="upload-cell-name",
                                                    size="xs",
                                                    label="Folder #2",
                                                    placeholder="Cell",
                                                    value=self.cp_info["cell"],
                                                ),
                                                dmc.Select(
                                                    label=" ",
                                                    placeholder="Signoff App",
                                                    id="upload-signoff-app",
                                                    clearable=True,
                                                    data=[
                                                        "Cana-TR",
                                                        "CDA",
                                                        "DriverKeeper",
                                                        "DynamicDCPath",
                                                        "DSC",
                                                        "FANOUT",
                                                        "LatchStrengthCheck",
                                                        "LevelShifterCheck",
                                                        "PEC",
                                                        "PN_Ratio",
                                                        "etc",
                                                    ],
                                                    size="xs",
                                                ),
                                            ]
                                        ),
                                        dmc.TextInput(
                                            label="type in the path of CSV file to upload Workspace",
                                            leftSection=dmc.ActionIcon(
                                                get_icon("bx-file-find"),
                                                id="upload-csv-file-search",
                                                variant="subtle",
                                                n_clicks=0,
                                            ),
                                            rightSection=dmc.Button(
                                                "Upload",
                                                id="upload-csv-workspace-btn",
                                                style={"width": 100},
                                                n_clicks=0,
                                            ),
                                            rightSectionWidth=100,
                                            required=True,
                                            id="upload-csv-path-input",
                                        ),
                                    ],
                                    color="gray",
                                    variant="outline",
                                ),
                            ]
                        ),
                    ],
                    value="uploader",
                ),
            ],
        )

        return dmc.Drawer(
            title=dmc.Title(f"Open from Workspace", order=3),
            id="workspace-drawer",
            padding="md",
            size="70%",
            opened=False,
            children=[
                dmc.Stack(
                    [
                        self.explorer.layout(),
                        dmc.Divider(),
                        workspace_upload_layout,
                    ],
                    justify="space-around",
                    align="stretch",
                    gap="xl",
                )
            ],
        )

    def register_callbacks(self, app):
        self.explorer.register_callbacks(app)
        app.clientside_callback(
            """
            function updateLoadingState(n_clicks) {
                return true
            }
            """,
            Output("open-data-btn", "loading", allow_duplicate=True),
            Input("open-workspace-btn", "n_clicks"),
            prevent_initial_call=True,
        )

        @app.callback(
            Output("workspace-drawer", "opened", allow_duplicate=True),
            Output("cwd", "children", allow_duplicate=True),
            Output("open-data-btn", "loading"),
            Input("open-workspace-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        @debugging_decorator
        def open_workspace_drawer(open_n):
            if not open_n:
                raise exceptions.PreventUpdate
            return True, "WORKSPACE", False

        @app.callback(
            Output("open-csv-path-input", "value", allow_duplicate=True),
            Input("open-csv-file-search", "n_clicks"),
            prevent_initial_call=True,
        )
        def get_open_file_path(n):
            cmd = f"{SCRIPT}/QFileDialog/file_dialog"
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
            Output("csv-file-path", "children", allow_duplicate=True),
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

                    df = file2df(file_path, workspace=False)
                    patched_dashGridOptions = Patch()
                    CACHE.set("TreeMode", False)
                    CACHE.set("TreeCol", None)
                    CACHE.set("viewmode", None)
                    CACHE.set("PropaRule", None)
                    CACHE.set("waiver_def", None)
                    patched_dashGridOptions["treeData"] = False

                except Exception as e:
                    noti = create_notification(message=f"Read Data Error: {e}", position="center")
                    return (
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        noti,
                        False,
                        False,
                    )
                mod_time = os.path.getmtime(file_path)

                return (
                    generate_column_definitions(df),
                    patched_dashGridOptions,
                    f"Total Rows: {len(df)}",
                    file_path,
                    mod_time,
                    None,
                    False,
                    False,
                )

            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                None,
                no_update,
                False,
            )

        @app.callback(
            Output("cwd", "children", allow_duplicate=True),
            Output("notifications", "children"),
            Input("upload-csv-workspace-btn", "n_clicks"),
            State("upload-csv-path-input", "value"),
            State("upload-library-name", "value"),
            State("upload-cell-name", "value"),
            State("upload-signoff-app", "value"),
            State("cwd", "children"),
            prevent_initial_call=True,
        )
        def upload_data_to_workspace(n, csv_file_path, library_name, cell_name, so_app, cwd):
            if not n or not csv_file_path:
                raise exceptions.PreventUpdate
            try:
                dff = validate_df(csv_file_path).drop(["uniqid"])
                if "childCount" in dff.columns:
                    dff = dff.drop("childCount")
            except Exception as e:
                noti = create_notification(message=f"Error loading {csv_file_path}: {e}", position="center")
                return no_update, noti

            dir_path = (
                os.path.join(WORKSPACE, library_name, cell_name) if library_name else os.path.join(WORKSPACE, USERNAME)
            )
            create_directory(dir_path)

            if so_app is None:
                so_app = ""

            upload_dir = os.path.join(dir_path, so_app)
            create_directory(upload_dir)

            filename = os.path.basename(csv_file_path)
            if filename.endswith(".csv"):
                filename = filename.replace(".csv", ".parquet")

            new_file_path = os.path.join(upload_dir, filename)

            dff.write_parquet(new_file_path)
            os.chmod(new_file_path, 0o777)

            noti = create_notification(
                title="file uploaded to WORKSPACE",
                message=f"{csv_file_path} uploaded",
                icon_name="bx-smile",
                position="top-center",
            )
            return cwd, noti
