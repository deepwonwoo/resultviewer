import os
import subprocess
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import html, Output, Input, State, Patch, no_update, exceptions
from components.grid.dag.column_definitions import generate_column_definitions
from components.menu.home.item.workspace_explore import FileExplorer
from utils.config import CONFIG
from utils.db_management import SSDF
from utils.data_processing import file2df


class Opener:
    def __init__(self) -> None:
        self.init_csv = SSDF.init_csv

    def layout(self):
        return html.Div([self.open_menu(), self.local_modal()])

    def open_menu(self):
        return dmc.Menu(
            [
                dmc.MenuTarget(dbpc.Button("Open", icon="folder-open", minimal=True, outlined=True)),
                dmc.MenuDropdown(
                    [
                        dmc.MenuItem(dbpc.Button("Open from Local", icon="document-open", minimal=True, small=True), n_clicks=0, id="open-local-btn"),
                        dmc.MenuItem(
                            dbpc.Button("Open from Workspace", icon="cloud-download", minimal=True, small=True), id="open-workspace-btn", n_clicks=0
                        ),
                    ]
                ),
            ],
            trigger="hover",
        )

    def local_modal(self):
        return dbpc.Dialog(
            title="파일 열기",
            icon="document-open",
            id="local-file-open-modal",
            isCloseButtonShown=True,
            usePortal=True,
            canOutsideClickClose=False,
            canEscapeKeyClose=False,
            lazy=True,
            isOpen=True if self.init_csv else False,
            style={"width": "50%"},
            children=[
                dbpc.DialogBody(
                    [
                        dmc.TextInput(
                            value=self.init_csv,
                            label="Open하려는 파일 경로를 입력하세요.",
                            leftSection=dbpc.Button(id="open-csv-file-search", icon="search", minimal=True, n_clicks=0),
                            required=True,
                            id="open-csv-path-input",
                        )
                    ]
                ),
                dbpc.DialogFooter(
                    actions=[dbpc.Button("Open", id="open-csv-local-btn", disabled=True, n_clicks=0, intent="primary")],
                    id="open-dialog-file-check-msg",
                ),
            ],
        )

    def register_callbacks(self, app):
        self._register_local_upload_callback(app)
        self._register_workspace_upload_callback(app)

    def _register_workspace_upload_callback(self, app):

        @app.callback(
            Output("flex-layout", "model", allow_duplicate=True),
            Output("cwd-breadcrum", "items", allow_duplicate=True),
            Input("open-workspace-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True,
        )
        def open_workspace_tab(n_clicks, current_model):
            if n_clicks is None:
                raise exceptions.PreventUpdate

            left_border_index = next((i for i, b in enumerate(current_model["borders"]) if b["location"] == "left"), None)
            # 이미 workspace-tab 탭이 있는지 확인
            if left_border_index is not None:
                existing_tabs = current_model["borders"][left_border_index].get("children", [])
                tab_exists = any(tab.get("id") == "workspace-tab" for tab in existing_tabs)
                if tab_exists:
                    # 이미 탭이 있다면 해당 탭을 선택하도록 함
                    patched_model = Patch()
                    tab_index = next(i for i, tab in enumerate(existing_tabs) if tab.get("id") == "workspace-tab")
                    patched_model["borders"][left_border_index]["selected"] = tab_index
                    return patched_model, [{"icon": "database", "text": "WORKSPACE", "current": "true"}]

            # 새로운 탭 정의
            new_tab = {"type": "tab", "name": "Workspace", "component": "button", "enableClose": True, "id": "workspace-tab"}

            patched_model = Patch()

            if left_border_index is not None:
                # 기존 left border 수정
                patched_model["borders"][left_border_index]["children"].append(new_tab)
                patched_model["borders"][left_border_index]["selected"] = len(current_model["borders"][left_border_index]["children"])
            else:
                # left border가 없으면 새로 추가
                patched_model["borders"].append({"type": "border", "location": "left", "size": 800, "selected": 0, "children": [new_tab]})
            return patched_model, [{"icon": "database", "text": "WORKSPACE", "current": "true"}]

    def _register_local_upload_callback(self, app):

        @app.callback(
            Output("open-csv-local-btn", "disabled"), Output("open-dialog-file-check-msg", "children"), Input("open-csv-path-input", "value")
        )
        def update_open_button_state(file_path):
            if not file_path:
                return True, ""

            file_path = file_path.strip()
            if file_path.startswith("WORKSPACE"):
                file_path = file_path.replace("WORKSPACE", CONFIG.WORKSPACE)
            try:
                if os.path.isfile(file_path):
                    return False, ""
                else:
                    return True, "No File Exists"
            except Exception as e:
                return True, f"{e}"

        @app.callback(
            Output("open-csv-path-input", "value", allow_duplicate=True), Input("open-csv-file-search", "n_clicks"), prevent_initial_call=True
        )
        def get_open_file_path(n):
            cmd = f"{CONFIG.SCRIPT}/QFileDialog/file_dialog"
            result = subprocess.run([cmd], capture_output=True, text=True, env=CONFIG.get_QtFileDialog_env())
            file_path = result.stdout.strip()
            return file_path if file_path else no_update

        @app.callback(Output("local-file-open-modal", "isOpen", allow_duplicate=True), Input("open-local-btn", "n_clicks"), prevent_initial_call=True)
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
            Output("refresh-waiver-counter-btn", "n_clicks", allow_duplicate=True),
            Output("flex-layout", "model", allow_duplicate=True),
            Output("csv-mod-time", "data", allow_duplicate=True),
            Output("toaster", "toasts", allow_duplicate=True),
            Output("local-file-open-modal", "isOpen", allow_duplicate=True),
            Output("open-csv-local-btn", "loading"),
            Output("file-mode-control", "disabled", allow_duplicate=True),
            Output("file-mode-control", "value", allow_duplicate=True),
            Output("pre-defined-view", "data", allow_duplicate=True),
            Input("open-csv-local-btn", "n_clicks"),
            State("open-csv-path-input", "value"),
            prevent_initial_call=True,
        )
        def open_local_file(n_clicks, file_path):
            if not n_clicks or not file_path:
                raise exceptions.PreventUpdate

            ret_pre_defined_value = no_update
            file_path = file_path.strip()
            if file_path.startswith("WORKSPACE"):
                file_path = file_path.replace("WORKSPACE", CONFIG.WORKSPACE)
                disable_fileMode_control = False
                value_fileMode_control = "init"
                if "STDCELL_CHK" in file_path:
                    ret_pre_defined_value = "stdcell"
            else:
                disable_fileMode_control = True
                value_fileMode_control = no_update
            try:
                df = file2df(file_path)

                patched_dashGridOptions = Patch()
                patched_dashGridOptions["treeData"] = False
                SSDF.tree_mode = False
                SSDF.tree_col = None
                SSDF.viewmode = None
                SSDF.propa_rule = None
                mod_time = os.path.getmtime(file_path)

                patched_fl_config = Patch()
                patched_fl_config["layout"]["children"][0]["children"][0]["name"] = file_path.replace(CONFIG.WORKSPACE, "WORKSPACE")

                return (
                    generate_column_definitions(df),
                    patched_dashGridOptions,
                    f"Total Rows: {len(df):,}",
                    1,
                    patched_fl_config,
                    mod_time,
                    [dbpc.Toast(message=f"Local File '{os.path.basename(file_path)}' Opened", intent="primary", icon="endorsed")],
                    False,
                    False,
                    disable_fileMode_control,
                    value_fileMode_control,
                    ret_pre_defined_value,
                )

            except Exception as e:
                return (
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    [dbpc.Toast(message=f"Error: {str(e)}", intent="danger", icon="error")],
                    no_update,
                    False,
                    no_update,
                    no_update,
                    no_update,
                )
