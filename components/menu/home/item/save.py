import os
import subprocess
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, no_update, html, exceptions
from utils.component_template import get_icon, create_notification
from utils.data_processing import displaying_df
from utils.file_operations import backup_file
from utils.config import CONFIG
from utils.db_management import SSDF
from utils.logging_utils import logger


class Saver:
    def layout(self):
        return html.Div([self.save_menu(), self.local_saver_modal(), self.workspace_saver_modal()])

    def save_menu(self):
        return dmc.Menu(
            [
                dmc.MenuTarget(dbpc.Button("Save", icon="floppy-disk", minimal=True, outlined=True)),
                dmc.MenuDropdown(
                    [
                        dmc.MenuItem(
                            dbpc.Button("Save to Local", icon="saved", minimal=True, small=True), id="open-save-local-modal-btn", n_clicks=0
                        ),
                        dmc.MenuItem(
                            dbpc.Button("Save to WORKSPACE", icon="cloud-upload", minimal=True, small=True),
                            id="open-save-workspace-modal-btn",
                            n_clicks=0,
                        ),
                    ]
                ),
            ],
            trigger="hover",
        )

    def local_saver_modal(self):
        return dbpc.Dialog(
            title="File Save as (@local)",
            icon="saved",
            id="local-file-save-modal",
            isCloseButtonShown=True,
            isOpen=False,
            lazy=True,
            usePortal=True,
            canOutsideClickClose=False,
            canEscapeKeyClose=False,
            style={"width": "50%"},
            children=[
                dbpc.DialogBody(
                    [
                        dmc.TextInput(
                            value="",
                            label="type in the path of CSV file to Save",
                            leftSection=dbpc.Button(id="save-csv-file-search", icon="search", minimal=True, n_clicks=0),
                            required=True,
                            id="save-csv-path-input",
                        )
                    ]
                ),
                dbpc.DialogFooter(
                    actions=[
                        dmc.Checkbox(label="filtred data only", checked=False, id="filtered-save-as"),
                        dbpc.Button("local Save (Download)", id="save-csv-local-btn", n_clicks=0, intent="primary"),
                    ],
                    id="save-local-file-check-msg",
                ),
            ],
        )

    def workspace_saver_modal(self):
        return dbpc.Dialog(
            title="File Save as (@Workspace)",
            icon="cloud-upload",
            id="workspace-file-save-modal",
            isCloseButtonShown=True,
            isOpen=False,
            style={"width": "50%"},
            children=[
                dbpc.DialogBody([dmc.TextInput(value="", label="path should start with WORKSPACE/", required=True, id="workspace-save-target-path")]),
                dbpc.DialogFooter(
                    actions=[dbpc.Button("Workspace Save", id="save-csv-workspace-btn", n_clicks=0, intent="primary")],
                    id="workspace-local-file-check-msg",
                ),
            ],
        )

    def register_callbacks(self, app):
        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("local-file-save-modal", "isOpen", allow_duplicate=True),
            Output("save-csv-path-input", "value", allow_duplicate=True),
            Input("open-save-local-modal-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True,
        )
        def open_local_save_modal(open_n, model_layout):
            df_to_save = displaying_df()
            if df_to_save is None:
                return ([dbpc.Toast(message=f"No Dataframe loaded", intent="warning", icon="warning-sign")], False, no_update)
            csv_file_path = model_layout["layout"]["children"][0]["children"][0]["name"]
            file_name = os.path.basename(csv_file_path)
            if file_name.endswith(".parquet"):
                file_name = file_name.replace(".parquet", ".csv")
            current_path = os.getcwd()
            return no_update, True, os.path.join(current_path, file_name)

        @app.callback(
            Output("save-csv-path-input", "value", allow_duplicate=True),
            Input("save-csv-file-search", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True,
        )
        def get_save_file_path(n, model_layout):
            cmd = f"{CONFIG.SCRIPT}/QFileDialog/save_dialog"
            csv_file_path = model_layout["layout"]["children"][0]["children"][0]["name"]
            result = subprocess.run([cmd, csv_file_path], capture_output=True, text=True, env=CONFIG.get_QtFileDialog_env())
            save_path = result.stdout.strip()
            return save_path if save_path else no_update

        @app.callback(
            Output("save-csv-local-btn", "disabled"),
            Output("save-local-file-check-msg", "children"),
            Input("save-csv-path-input", "value"),
            prevent_initial_call=True,
        )
        def update_local_save_button_state(save_path):
            if not save_path:
                return True, "Type local path to save the file"
            try:
                # 경로 정규화
                save_path = os.path.abspath(os.path.expanduser(save_path))
                save_dir = os.path.dirname(save_path)

                # 1. 디렉토리 존재 여부 확인
                if not os.path.exists(save_dir):
                    return True, f"저장하려는 디렉토리가 존재하지 않습니다: {save_dir}"

                # 2. 디렉토리 쓰기 권한 확인
                if not os.access(save_dir, os.W_OK):
                    return True, f"디렉토리에 쓰기 권한이 없습니다: {save_dir}"

                # 3. 파일 확장자 확인 (.csv 또는 .parquet)
                if not save_path.endswith((".csv", ".parquet")):
                    return True, "파일 확장자는 .csv 또는 .parquet이어야 합니다."

                # 4. 기존 파일 존재 여부 확인
                if os.path.exists(save_path):
                    return (True, f"이미 같은 이름의 파일이 존재합니다: {os.path.basename(save_path)}")

                # 5. 디스크 공간 확인 (옵션)
                try:
                    free_space = os.statvfs(save_dir).f_frsize * os.statvfs(save_dir).f_bavail
                    if free_space < 1024 * 1024 * 10:  # 10MB 이하면 경고
                        return True, f"디스크 공간이 부족합니다: {save_dir}"
                except:
                    pass  # statvfs를 지원하지 않는 경우 skip
                return False, ""

            except Exception as e:
                return True, f"경로 검증 중 오류가 발생했습니다: {str(e)}"

        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("local-file-save-modal", "isOpen", allow_duplicate=True),
            Input("save-csv-local-btn", "n_clicks"),
            State("save-csv-path-input", "value"),
            State("filtered-save-as", "checked"),
            prevent_initial_call=True,
        )
        def save_local(save_n, save_path, filtered_save_as):
            df_to_save = displaying_df(filtred_apply=filtered_save_as)
            if save_path:
                if save_path.endswith(".parquet"):
                    df_to_save.write_parquet(save_path)
                else:
                    df_to_save.write_csv(save_path)

                return ([dbpc.Toast(message=f"File saved to {save_path}", icon="endorsed")], False)
            return ([dbpc.Toast(message=f"No save path given", intent="warning", icon="warning-sign")], False)

        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("workspace-file-save-modal", "isOpen", allow_duplicate=True),
            Output("workspace-save-target-path", "value"),
            Input("open-save-workspace-modal-btn", "n_clicks"),
            State("flex-layout", "model"),
            State("file-mode-control", "value"),
            prevent_initial_call=True,
        )
        def show_workspace_save_dialog(n, model_layout, file_mode):
            if not n:
                raise exceptions.PreventUpdate

            csv_file_path = model_layout["layout"]["children"][0]["children"][0]["name"]
            toasts = None

            if displaying_df() is None:
                toasts = [dbpc.Toast(message=f"No Dataframe loaded", intent="warning", icon="warning-sign")]
            elif not csv_file_path.startswith("WORKSPACE"):
                toasts = [dbpc.Toast(message=f"Data is not from WORKSPACE", intent="warning", icon="warning-sign")]
            elif file_mode == "read":
                toasts = [dbpc.Toast(message=f"File is in READ mode", intent="warning", icon="warning-sign")]

            if toasts:
                return toasts, no_update, no_update
            else:
                return no_update, True, csv_file_path

        @app.callback(
            Output("save-csv-workspace-btn", "disabled"),
            Output("workspace-local-file-check-msg", "children"),
            Input("workspace-save-target-path", "value"),
            prevent_initial_call=True,
        )
        def update_workspace_save_button_state(save_path):
            if not save_path:
                return True, "Type local path to save the file"
            try:
                if not save_path.startswith("WORKSPACE"):
                    return True, "경로가 'WORKSPACE/'로 시작해야 합니다."

                if " " in save_path:
                    return True, "Should not contain spaces"

                # WORKSPACE 실제 경로로 변환
                real_path = save_path.replace("WORKSPACE", CONFIG.WORKSPACE)
                save_dir = os.path.dirname(real_path)

                # 확장자 처리 (.csv -> .parquet)
                if real_path.endswith(".csv"):
                    real_path = real_path.replace(".csv", ".parquet")
                elif not real_path.endswith(".parquet"):
                    real_path += ".parquet"

                # 디렉토리 존재 여부 확인
                if not os.path.exists(save_dir):
                    return (True, f"저장하려는 디렉토리가 존재하지 않습니다: {save_dir.replace(CONFIG.WORKSPACE, "WORKSPACE")}")

                # 파일 존재 여부 확인
                file_exists = os.path.exists(real_path)
                if file_exists:
                    return (
                        False,
                        f"기존 파일이 백업되고 새로운 파일이 저장됩니다.\n(백업 위치: {save_dir.replace(CONFIG.WORKSPACE, "WORKSPACE")}/backup/)",
                    )

                return False, ""

            except Exception as e:
                logger.error(f"Workspace path validation error: {str(e)}")
                return True, f"경로 검증 중 오류가 발생했습니다: {str(e)}"

        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("workspace-file-save-modal", "isOpen", allow_duplicate=True),
            Input("save-csv-workspace-btn", "n_clicks"),
            State("workspace-save-target-path", "value"),
            prevent_initial_call=True,
        )
        def save_csv_workspace(n, save_path):
            if not n:
                raise exceptions.PreventUpdate

            if not save_path.endswith(".parquet"):
                if save_path.endswith(".csv"):
                    save_path = save_path.replace(".csv", ".parquet")
                else:
                    save_path = save_path + ".parquet"

            save_target_path = save_path.replace("WORKSPACE", CONFIG.WORKSPACE)

            try:
                file_exists = os.path.isfile(save_target_path)
                if file_exists:
                    backup_file(os.path.dirname(save_target_path), save_target_path)

                df_to_save = displaying_df()
                df_to_save.write_parquet(save_target_path)
                # os.chmod(save_target_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

                return ([dbpc.Toast(message=f"Saved to Workspace {save_path.replace(CONFIG.WORKSPACE, "WORKSPACE")}", icon="endorsed")], False)

            except Exception as e:
                return ([dbpc.Toast(message=f"{str(e)}", intent="danger", icon="error")], False)
