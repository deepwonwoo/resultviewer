import re
import os
import shutil
import subprocess
import polars as pl
import dash_mantine_components as dmc
from dash import Input, Output, State, html, no_update, ctx, exceptions
from components.grid.dag.column_definitions import generate_column_definitions
from utils.db_management import SSDF
from utils.config import CONFIG
from utils.component_template import create_notification, get_icon


class MasterName:
    def __init__(self) -> None:
        self.top_cell_names = []

    def layout(self):
        return html.Div(
            [
                dmc.Button(
                    "Extract Full Master Name",
                    id="masterName-modal-open-btn",
                    variant="outline",
                    leftSection=get_icon("bx-code"),
                    color="indigo",
                    size="xs",
                ),
                self.modal(),
            ]
        )

    def modal(self):
        return dmc.Modal(
            title=dmc.Title(f"Extract Full Master Name using PERC", order=3),
            id="masterName-modal",
            size="xl",
            opened=False,
            closeOnClickOutside=False,
            children=[
                dmc.Card(
                    children=[
                        dmc.LoadingOverlay(
                            visible=False,
                            id="masterNameloading-overlay",
                            zIndex=1000,
                            overlayProps={"radius": "sm", "blur": 2},
                        ),
                        dmc.Paper(
                            children=[
                                dmc.TextInput(
                                    label="Upload CKT file to find Full Master Name",
                                    leftSection=dmc.ActionIcon(
                                        get_icon("bx-file-find"),
                                        id="upload-ckt-file-search",
                                        variant="subtle",
                                        n_clicks=0,
                                    ),
                                    rightSection=dmc.Button(
                                        "Upload", id="upload-ckt-file-btn", style={"width": 100}, n_clicks=0
                                    ),
                                    rightSectionWidth=100,
                                    required=True,
                                    id="masterName-ckt-file-path",
                                ),
                                dmc.Group(
                                    children=[
                                        dmc.TextInput(
                                            value="",
                                            label="TOP Cell Name:",
                                            w=200,
                                            id="ckt-top-subckt-textinput",
                                            disabled=True,
                                            required=True,
                                            error=False,
                                        )
                                    ]
                                ),
                            ],
                            shadow="sm",
                            p="xl",
                            withBorder=True,
                        ),
                        dmc.Paper(
                            children=[
                                dmc.Select(
                                    label="Net or Inst. Column",
                                    id="masterName-df-column-select",
                                    data=[],
                                    required=True,
                                ),
                                dmc.Group(
                                    children=[
                                        dmc.RadioGroup(
                                            children=dmc.Group([dmc.Radio(i, value=i) for i in ["net", "instance"]]),
                                            id="masterName-df-type-radioGroup",
                                            label="Select column type",
                                            size="xs",
                                            value="",
                                            required=True,
                                        ),
                                        dmc.RadioGroup(
                                            children=dmc.Group([dmc.Radio(i, value=i) for i in [".", "/"]]),
                                            id="masterName-delimiter-radioGroup",
                                            label="Select delimiter",
                                            size="xs",
                                            value="",
                                            required=True,
                                        ),
                                    ],
                                    mt=5,
                                ),
                            ],
                            shadow="sm",
                            p="xl",
                            withBorder=True,
                        ),
                        dmc.Button(
                            "Run PERC", id="run-perc-btn", variant="outline", fullWidth=True, disabled=True, mt=15
                        ),
                    ],
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                ),
                html.Div(id="run-perc-log", children=""),
            ],
        )

    def register_callbacks(self, app):

        @app.callback(
            Output("masterName-modal", "opened", allow_duplicate=True),
            Output("masterName-df-column-select", "data"),
            Output("masterNameloading-overlay", "visible", allow_duplicate=True),
            Input("masterName-modal-open-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def masterName_modal_open(nc):
            columns = SSDF.dataframe.columns
            return True, columns, False

        @app.callback(
            Output("ckt-top-subckt-textinput", "value"),
            Output("ckt-top-subckt-textinput", "disabled"),
            Output("notifications", "children", allow_duplicate=True),
            Input("upload-ckt-file-btn", "n_clicks"),
            State("masterName-ckt-file-path", "value"),
            prevent_initial_call=True,
        )
        def check_compare_columns(n, ckt_file_path):
            def extract_subckt_names(filename):
                with open(filename, "r") as f:
                    content = f.read()
                pattern = r"\.SUBCKT (\w+)"
                subckt_names = re.findall(pattern, content)
                if len(subckt_names) == 0:
                    raise Exception("No subckt name found in the CKT file.")
                subckt_names.reverse()
                return subckt_names

            try:
                self.top_cell_names = extract_subckt_names(ckt_file_path)
            except Exception as e:
                noti = create_notification(message=f"Error loading {ckt_file_path}: {e}", position="center")
                return no_update, True, noti

            return self.top_cell_names[0], False, None

        @app.callback(
            Output("ckt-top-subckt-textinput", "error"),
            Input("ckt-top-subckt-textinput", "value"),
            prevent_initial_call=True,
        )
        def select_value(value):
            return "" if value in self.top_cell_names else "No subckt name in CKT file"

        @app.callback(
            Output("masterName-delimiter-radioGroup", "value"),
            Output("masterName-df-column-select", "error"),
            Input("masterName-df-column-select", "value"),
            prevent_initial_call=True,
        )
        def validate_and_predict_delimiter(selected_column):

            def check_hierarchy_column(column):
                sample_values = SSDF.dataframe[column].head(100).to_list()
                delimiters = [".", "/"]
                delimiter_counts = {delimiter: 0 for delimiter in delimiters}
                for value in sample_values:
                    # Check if the value is not a string and convert it to string
                    if not isinstance(value, str):
                        value = str(value)
                    for delimiter in delimiters:
                        if delimiter in value:
                            delimiter_counts[delimiter] += 1

                if all(count == 0 for count in delimiter_counts.values()):
                    return False, None

                predicted_delimiter = max(delimiter_counts, key=delimiter_counts.get)
                return True, predicted_delimiter

            if selected_column:
                is_hierarchy, predicted_delimiter = check_hierarchy_column(selected_column)
                if is_hierarchy:
                    return predicted_delimiter, ""
                else:
                    return (no_update, "Selected column is not a hierarchy path. Please select another column.")

            raise exceptions.PreventUpdate

        @app.callback(
            Output("run-perc-btn", "disabled", allow_duplicate=True),
            Input("masterName-df-type-radioGroup", "value"),
            Input("masterName-delimiter-radioGroup", "value"),
            Input("masterName-df-column-select", "value"),
            Input("masterName-ckt-file-path", "value"),
            Input("ckt-top-subckt-textinput", "value"),
            prevent_initial_call=True,
        )
        def activate_run_perc_btn(type, delimiter, column, ckt_file_path, top_cell_name):
            return False if type and delimiter and column and ckt_file_path and top_cell_name else True

        app.clientside_callback(
            """
            function updateLoadingState(n_clicks) {
                return true
            }
            """,
            Output("masterNameloading-overlay", "visible", allow_duplicate=True),
            Input("run-perc-btn", "n_clicks"),
            prevent_initial_call=True,
        )

        @app.callback(
            Output("run-perc-log", "children", allow_duplicate=True),
            Input("run-perc-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def check_perc_log(n):
            PERC_log = os.path.join(CONFIG.USER_RV_DIR, "PERC", "logs", "perc.log")
            return dmc.Alert(dmc.Text(os.path.abspath(PERC_log), fw=700), title="Check PERC Log:")

        @app.callback(
            Output("masterName-modal", "opened", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("masterNameloading-overlay", "visible"),
            Output("run-perc-log", "children"),
            Input("run-perc-btn", "n_clicks"),
            State("masterName-df-type-radioGroup", "value"),
            State("masterName-delimiter-radioGroup", "value"),
            State("masterName-df-column-select", "value"),
            State("masterName-ckt-file-path", "value"),
            State("ckt-top-subckt-textinput", "value"),
            prevent_initial_call=True,
        )
        def run_perc(n, type, delimiter, column, ckt_file_path, top_cell_name):
            dff = SSDF.dataframe
            PERC_WORKSPACE = os.path.join(CONFIG.USER_RV_DIR, "PERC")
            if not os.path.exists(PERC_WORKSPACE):
                os.makedirs(PERC_WORKSPACE)

            for perc_file in ["run_block_xr", "latch.rules"]:
                shutil.copy(f"{CONFIG.SCRIPT}/perc/{perc_file}", PERC_WORKSPACE)

            perc_script = os.path.join(PERC_WORKSPACE, "run_block_xr")
            os.chmod(perc_script, 0o755)

            # Writing to the file
            with open(os.path.join(PERC_WORKSPACE, "Input.list"), "w") as f:
                f.write(f"{type}\n")  # First line: type
                f.write(f"{delimiter}\n")  # Second line: delimiter
                for entry in dff[column]:
                    f.write(f"{entry}\n")

            proc = subprocess.run([f"./run_block_xr {ckt_file_path} {top_cell_name}"], shell=True, cwd=PERC_WORKSPACE)

            if proc.returncode == 0:
                df_perc = pl.read_csv(f"{PERC_WORKSPACE}/results/instance_master_names.csv", has_header=False)
                df_perc = df_perc.rename({"column_2": "Full Master Name"})
                dff = dff.with_columns(pl.col(column).str.to_uppercase().alias("join_column"))
                dff = dff.join(df_perc, left_on="join_column", right_on="column_1")
                SSDF.dataframe = dff.drop("join_column")
                updated_columnDefs = generate_column_definitions(SSDF.dataframe)
                return False, updated_columnDefs, False, None
            else:
                return True, no_update, False, None
