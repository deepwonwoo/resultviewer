import dash_mantine_components as dmc
from dash import Input, Output, State, html, exceptions, ctx, no_update, ALL, Patch
from components.dag.column_definitions import generate_column_definitions
from utils.process_helpers import *
from utils.db_management import WORKSPACE, USERNAME, SCRIPT, CACHE, DATAFRAME
from utils.process_helpers import create_notification, backup_file
from utils.logging_utils import logger
from components.menu.home.item.workspace_explore import FileExplorer
import subprocess


class Compare:
    def layout(self):
        return html.Div(
            [
                dmc.Button(
                    "Compare",
                    id="compare-btn",
                    variant="outline",
                    leftSection=get_icon("compare"),
                    color="indigo",
                    size="xs",
                ),
                self.modal(),
            ],
        )

    def modal(self):
        body = dmc.TableTbody(id="table_rows")
        head = dmc.TableThead(
            dmc.TableTr(
                [
                    dmc.TableTh("Keys"),
                    dmc.TableTh("Values"),
                    dmc.TableTh("Tolerences"),
                ]
            )
        )
        caption = dmc.TableCaption("Selected Columns to Compare")

        return dmc.Modal(
            title=dmc.Title(f"Compare", order=3),
            id="compare-modal",
            size="xl",
            opened=False,
            closeOnClickOutside=False,
            children=[
                dmc.Card(
                    children=[
                        dmc.TextInput(
                            label="Upload compare target file path",
                            leftSection=dmc.ActionIcon(
                                get_icon("bx-file-find"),
                                id="upload-compare-file-search",
                                variant="subtle",
                                n_clicks=0,
                            ),
                            rightSection=dmc.Button(
                                "Upload",
                                id="upload-compare-target-btn",
                                style={"width": 100},
                                n_clicks=0,
                            ),
                            rightSectionWidth=100,
                            required=True,
                            id="upload-compare-path-input",
                        ),
                        dmc.MultiSelect(
                            label="Select Columns",
                            placeholder="Select columns to compare!",
                            id="column-multi-select",
                            value=[],
                            # data=df1.columns,
                            mb=10,
                            disabled=True,
                        ),
                        dmc.Table([head, body, caption]),
                        dmc.Button(
                            "Compare",
                            id="run-compare-btn",
                            variant="outline",
                            fullWidth=True,
                            mt=15,
                        ),
                    ],
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                )
            ],
        )

    def register_callbacks(self, app):

        @app.callback(
            Output("compare-modal", "opened", allow_duplicate=True),
            Output("notifications", "children", allow_duplicate=True),
            Input("compare-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def compare_modal_open(nc):
            if displaying_df() is None:
                return no_update, create_notification(message="No Dataframe loaded", position="center")
            return True, None

        @app.callback(
            Output("upload-compare-path-input", "value", allow_duplicate=True),
            Input("upload-compare-file-search", "n_clicks"),
            prevent_initial_call=True,
        )
        def find_FileDialog(n):
            # result = subprocess.run(["python", f"{SCRIPT}/QFileDialog/OpenFileName.py"], capture_output=True, text=True)
            cmd = f"{SCRIPT}/QFileDialog/file_dialog"
            result = subprocess.run([cmd], capture_output=True, text=True)
            file_path = result.stdout.strip()
            return file_path if file_path else no_update

        @app.callback(
            Output("column-multi-select", "data"),
            Output("column-multi-select", "disabled"),
            Output("notifications", "children", allow_duplicate=True),
            Input("upload-compare-target-btn", "n_clicks"),
            State("upload-compare-path-input", "value"),
            prevent_initial_call=True,
        )
        def check_compare_columns(n, compare_target_path):
            try:
                target_df = validate_df(compare_target_path)
            except Exception as e:
                noti = create_notification(
                    message=f"Error loading {compare_target_path}: {e}",
                    position="center",
                )
                return no_update, True, noti

            df_columns = DATAFRAME["df"].columns
            df_columns.remove("uniqid")
            target_df_columns = target_df.columns
            common_columns = [col for col in df_columns if col in target_df_columns]

            if common_columns == []:
                noti = create_notification(
                    message="No common columns found between the two dataframes.",
                    position="center",
                )
                return no_update, True, noti

            return common_columns, False, None

        @app.callback(
            Output("table_rows", "children"),
            Input("column-multi-select", "value"),
            prevent_initial_call=True,
        )
        def select_value(selected_list):
            rows = []
            for i, selected in enumerate(selected_list):
                if DATAFRAME["df"][selected].dtype.is_numeric():
                    element = dmc.TableTr(
                        [
                            dmc.TableTd(""),
                            dmc.TableTd(
                                dmc.Text(
                                    selected,
                                    id={"type": "value", "index": i},
                                    size="sm",
                                )
                            ),
                            dmc.TableTd(
                                dmc.NumberInput(
                                    value=0,
                                    min=0,
                                    size="xs",
                                    id={"type": "tolerance", "index": i},
                                )
                            ),
                        ]
                    )
                else:
                    element = dmc.TableTr(
                        [
                            dmc.TableTd(dmc.Text(selected, id={"type": "key", "index": i}, size="sm")),
                            dmc.TableTd(""),
                            dmc.TableTd(""),
                        ]
                    )
                rows.append(element)
            return rows

        app.clientside_callback(
            """
            function updateLoadingState(n_clicks) {
                return true
            }
            """,
            Output("run-compare-btn", "loading", allow_duplicate=True),
            Input("run-compare-btn", "n_clicks"),
            prevent_initial_call=True,
        )
