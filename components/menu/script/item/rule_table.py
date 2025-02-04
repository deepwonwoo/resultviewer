import pandas as pd
import os
import re
import shutil
import subprocess
import dash_mantine_components as dmc
import dash_ag_grid as dag

from components.grid.dag.column_definitions import generate_column_definitions
from utils.config import CONFIG
from utils.component_template import create_notification, get_icon
from dash import html, Input, Output, State, no_update, exceptions, dcc, Patch


class RuleTable:

    def __init__(self) -> None:
        self.top_cell_names = []

    def layout(self):
        return html.Div(
            [
                dmc.Button("Create Rule Table", id="create-ruletable-btn", variant="outline", color="indigo", size="xs"),
                self.modal(),
            ]
        )

    def modal(self):
        return dmc.Modal(
            title="Create Rule Table",
            id="create-ruletable-modal",
            size="90%",
            opened=False,
            closeOnClickOutside=False,
            children=[
                dmc.Card(
                    children=[
                        dmc.Paper(
                            children=[
                                dmc.TextInput(
                                    value="",
                                    label="Upload CKT File to find Full Master Name",
                                    leftSection=dmc.ActionIcon(
                                        get_icon("bx-file-find"),
                                        id="ruletable-upload-ckt-file-search",
                                        variant="subtle",
                                        n_clicks=0,
                                    ),
                                    rightSection=dmc.Button("Upload", id="ruletable-upload-ckt-file-btn", style={"width": 100}, n_clicks=0),
                                    rightSectionWidth=100,
                                    required=True,
                                    id="ruletable-ckt-file-path-input",
                                ),
                                dmc.Group(
                                    children=[
                                        dmc.TextInput(
                                            value="",
                                            label="TOP CELL NAME:",
                                            w=400,
                                            id="ruletable-ckt-top-subckt-textinput",
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
                        dmc.Button("Run PERC", id="ruletable-run-perc-btn"),
                    ]
                ),
                html.Div(id="ruletable-perc-log"),
                dag.AgGrid(
                    columnDefs=[{"field": "Part", "editable": True}],
                    defaultColDef={
                        "flex": 1,
                        "resizable": True,
                        "sortable": True,
                        "filter": True,
                        "floatingFilter": True,
                    },
                    dashGridOptions={
                        "rowHeight": 24,
                        "headerHeight": 30,
                        "autoGroupColumnDef": {
                            "minWidth": 300,
                            "headerName": "FullMasterName Hierarchy",
                            "cellRendererParams": {"suppressCount": True},
                        },
                        "groupDefaultExpanded": 0,
                        "getDataPath": {"function": "getDataPath(params)"},
                        "treeData": True,
                    },
                    rowData=[],
                    id="rule-table-ag-grid",
                    enableEnterpriseModules=True,
                ),
                dmc.Button("Download Rule Table", id="download-ruletable-btn", variant="outline", size="sm"),
                dmc.Button("Upload Rule Table", id="upload-ruletable-btn", variant="outline", size="sm"),
                dcc.Download(id="download-ruletable-csv"),
                dcc.Store("upload-ruletable-path"),
            ],
        )

    def parse_hierarchy(self, mastername_data):
        rowData = []
        with open(mastername_data, "r") as f:
            lines = f.readlines()
        for line in lines:
            if line.strip() == "master_name":
                continue
            hierarchy = line.strip().split("/")
            rowData.append({"masterHierarchy": hierarchy, "Part": ""})
        return rowData

    def parse_upload_ruletable(self, ruletable_path):
        rowData = []
        with open(ruletable_path, "r") as f:
            lines = f.readlines()
        for line in lines:
            if line.strip().startswith("Pattern"):
                continue
            hierarchy, part = line.strip().split(",")
            hierarchy = hierarchy.split("/")
            rowData.append({"masterHierarchy": hierarchy, "Part": part})
        return rowData

    def register_callbacks(self, app):

        @app.callback(
            Output("create-ruletable-modal", "opened"),
            Input("create-ruletable-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def open_modal(n_clicks):
            return True if n_clicks else no_update

        @app.callback(
            Output("ruletable-ckt-top-subckt-textinput", "value"),
            Output("ruletable-ckt-top-subckt-textinput", "disabled"),
            Output("notifications", "children", allow_duplicate=True),
            Input("ruletable-upload-ckt-file-btn", "n_clicks"),
            State("ruletable-ckt-file-path-input", "value"),
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
            Output("ruletable-ckt-top-subckt-textinput", "error"),
            Input("ruletable-ckt-top-subckt-textinput", "value"),
            prevent_initial_call=True,
        )
        def select_value(value):
            return "" if value in self.top_cell_names else "No subckt name in CKT file"

        @app.callback(
            Output("run-perc-rule-btn", "disabled", allow_duplicate=True),
            Input("ruletable-ckt-file-path-input", "value"),
            Input("ruletable-ckt-top-subckt-textinput", "value"),
            prevent_initial_call=True,
        )
        def activate_run_perc_btn(type, delimiter, column, ckt_file_path, top_cell_name):
            return False if type and delimiter and column and ckt_file_path and top_cell_name else True

        @app.callback(
            Output("rule-table-ag-grid", "rowData", allow_duplicate=True),
            Output("notifications", "children", allow_duplicate=True),
            Input("ruletable-run-perc-btn", "n_clicks"),
            State("ruletable-ckt-file-path-input", "value"),
            State("ruletable-ckt-top-subckt-textinput", "value"),
            prevent_initial_call=True,
        )
        def run_perc_script(n_clicks, ckt_file_path, top_cell_name):

            if not n_clicks or not ckt_file_path or not top_cell_name:
                raise exceptions.PreventUpdate

            PERC_WORKSPACE = os.path.join(CONFIG.USER_RV_DIR, "PERC")
            if not os.path.exists(PERC_WORKSPACE):
                os.makedirs(PERC_WORKSPACE)

            for perc_file in ["run_extract_full_master", "master.rules"]:
                shutil.copy(f"{CONFIG.SCRIPT}/perc/{perc_file}", PERC_WORKSPACE)
            perc_script = os.path.join(PERC_WORKSPACE, "run_extract_full_master")
            os.chmod(perc_script, 0o755)
            try:
                result = subprocess.run([f"./run_extract_full_master {ckt_file_path} {top_cell_name}"], shell=True, cwd=PERC_WORKSPACE)
                row_data = self.parse_hierarchy(f"{PERC_WORKSPACE}/results/full_master.csv")
                noti = create_notification(title="FullMasterNames Extracted", message="PERC script executed successfully", icon_name="bx-smile")
            except Exception as e:
                row_data = []
                noti = create_notification(f"PERC script execution failed: {e}")
            return row_data, noti

        @app.callback(
            Output("rule-table-ag-grid", "rowData"),
            Input("rule-table-ag-grid", "cellValueChanged"),
            State("rule-table-ag-grid", "rowData"),
            prevent_initial_call=True,
        )
        def update_rows(changed_cell, rows):
            if not changed_cell:
                return no_update
            changed_row = changed_cell[0]["data"]
            changed_field = changed_cell[0]["colId"]
            new_value = changed_cell[0]["value"]
            if changed_field == "Part":
                changed_hierarchy = changed_row["masterHierarchy"]
                patched_rows = Patch()
                for i, row in enumerate(rows):
                    if row["masterHierarchy"][: len(changed_hierarchy)] == changed_hierarchy:
                        patched_rows[i].Part = new_value
                return patched_rows
            return no_update

        @app.callback(
            Output("download-ruletable-csv", "data"),
            Input("download-ruletable-btn", "n_clicks"),
            State("rule-table-ag-grid", "virtualRowData"),
            prevent_initial_call=True,
        )
        def func(n_clicks, virtual_row_data):
            if n_clicks is None:
                return no_update
            df = pd.DataFrame(virtual_row_data)
            df["masterHierarchy"] = df["masterHierarchy"].apply("/".join)
            df.rename(columns={"masterHierarchy": "Pattern"}, inplace=True)
            return dcc.send_data_frame(df.to_csv, "ruletable.csv", index=False)

        @app.callback(
            Output("upload-ruletable-path", "data", allow_duplicate=True),
            Input("upload-ruletable-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def func(n_clicks):
            if n_clicks is None:
                return no_update
            cmd = f"{CONFIG.SCRIPT}/QFileDialog/file_dialog"
            result = subprocess.run([cmd], capture_output=True, text=True)
            file_path = result.stdout.strip()
            return file_path

        @app.callback(
            Output("rule-table-ag-grid", "rowData", allow_duplicate=True),
            Input("upload-ruletable-path", "data"),
            prevent_initial_call=True,
        )
        def func(file_path):
            rowData = self.parse_upload_ruletable(file_path)
            return rowData
