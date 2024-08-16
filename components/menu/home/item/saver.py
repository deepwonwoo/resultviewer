import os
import subprocess
import dash_mantine_components as dmc
from utils.db_management import USERNAME, WORKSPACE, SCRIPT, DATAFRAME
from dash import Output, Input, State, no_update, html
from utils.process_helpers import (
    get_icon,
    displaying_df,
    create_notification,
    create_directory,
    get_file_owner,
    backup_file,
)
from utils.logging_config import logger


class Saver:
    def layout(self):
        return dmc.Menu(
            [
                dmc.MenuTarget(
                    dmc.Button(
                        "Save",
                        variant="outline",
                        color="indigo",
                        size="xs",
                    )
                ),
                dmc.MenuDropdown(
                    [
                        dmc.MenuItem(
                            "Save as",
                            id="save-local-btn",
                            n_clicks=0,
                            leftSection=get_icon("bx-save"),
                        ),
                        dmc.MenuItem(
                            "Save to WORKSPACE",
                            id="save-workspace-btn",
                            n_clicks=0,
                            leftSection=get_icon("bx-cloud-upload"),
                        ),
                    ]
                ),
                dmc.Modal(
                    title="File Save as",
                    id="local-file-save-modal",
                    centered=True,
                    opened=False,
                    size="55%",
                    children=[
                        dmc.Checkbox(
                            label="filtred data only",
                            size="xs",
                            checked=False,
                            id="filtered-save-as",
                        ),
                        dmc.TextInput(
                            value="",
                            label="type in the path of CSV file to Save",
                            leftSection=dmc.ActionIcon(
                                get_icon("bx-file-find"),
                                id="save-csv-file-search",
                                variant="subtle",
                                n_clicks=0,
                            ),
                            rightSection=dmc.Button(
                                "Save",
                                id="save-csv-local-btn",
                                style={"width": 100},
                                n_clicks=0,
                            ),
                            rightSectionWidth=100,
                            required=True,
                            id="save-csv-path-input",
                        ),
                    ],
                ),
                html.Div(id="saver-notification"),
            ],
            trigger="hover",
        )

    def register_callbacks(self, app):

        @app.callback(
            Output("saver-notification", "children", allow_duplicate=True),
            Input("save-workspace-btn", "n_clicks"),
            State("csv-file-path", "children"),
            prevent_initial_call=True,
        )
        def save_csv_workspace_noti(n, csv_file_path):
            if not n:
                return no_update

            print(f"save_csv_workspace_noti1, {displaying_df()}")
            if displaying_df() is None:
                print("save_csv_workspace_noti2")
                return create_notification(message="No Dataframe loaded", position="center")
            elif not csv_file_path.startswith("WORKSPACE"):
                print("save_csv_workspace_noti3")
                return create_notification(message="data is not from WORKSPACE", position="center")
            elif DATAFRAME.get("readonly"):
                print("save_csv_workspace_noti4")
                return create_notification(message="file is READ ONLY mode", position="center")
            print("save_csv_workspace_noti5")
            return dmc.Notification(
                id="save-workspace-noti",
                title="Save to Workspace",
                message=dmc.TextInput(
                    id="save-target-path",
                    value=csv_file_path,
                    size="xs",
                    rightSection=dmc.ActionIcon(
                        get_icon("bx-cloud-upload"),
                        id="save-csv-workspace",
                        size="xs",
                        variant="subtle",
                        n_clicks=0,
                    ),
                ),
                loading=True,
                color="orange",
                action="show",
                autoClose=False,
                style={
                    "position": "fixed",
                    "bottom": 20,
                    "left": "50%",
                    "transform": "translateX(-50%)",
                    "width": "50%",
                    "zIndex": 9999,
                },
            )

        @app.callback(
            Output("saver-notification", "children", allow_duplicate=True),
            Input("save-csv-workspace", "n_clicks"),
            State("save-target-path", "value"),
            prevent_initial_call=True,
        )
        def save_csv_workspace(n, save_target_path):
            if not n:
                return no_update

            if save_target_path.startswith("WORKSPACE"):
                save_target_path = save_target_path.replace("WORKSPACE", WORKSPACE)
            else:
                return dmc.Notification(
                    id="save-workspace-noti",
                    title="Saved to Workspace Error",
                    message="Path should be start with 'WORKSPACE/'",
                    loading=False,
                    color="red",
                    action="update",
                    autoClose=True,
                    icon=get_icon("bx-tired"),
                )
            if save_target_path.endswith(".csv"):
                save_target_path = save_target_path.replace(".csv", ".parquet")

            dir_path = os.path.dirname(save_target_path)
            if not os.path.exists(dir_path):
                return dmc.Notification(
                    id="save-workspace-noti",
                    title="Saved to Workspace Error",
                    message="The directory does not exists in WORKSPACE'",
                    loading=False,
                    color="red",
                    action="update",
                    autoClose=True,
                    icon=get_icon("bx-tired"),
                )

            file_exists = os.path.isfile(save_target_path)
            if file_exists:
                backup_file(dir_path, save_target_path)

            df_to_save = displaying_df()
            df_to_save.write_parquet(save_target_path)
            os.chmod(save_target_path, 0o777)

            message = "Updated!" if file_exists else "Created!"

            return dmc.Notification(
                id="save-workspace-noti",
                title="Saved to Workspace",
                message=message,
                loading=False,
                color="yellow",
                action="update",
                autoClose=True,
                icon=get_icon("bx-cool"),
            )

        @app.callback(
            Output("save-csv-path-input", "value", allow_duplicate=True),
            Input("save-csv-file-search", "n_clicks"),
            State("csv-file-path", "children"),
            prevent_initial_call=True,
        )
        def get_save_file_path(n, csv_file_path):
            cmd = f"{SCRIPT}/QFileDialog/save_dialog"
            result = subprocess.run([cmd, csv_file_path], capture_output=True, text=True)
            save_path = result.stdout.strip()
            return save_path if save_path else no_update

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Output("local-file-save-modal", "opened", allow_duplicate=True),
            Output("save-csv-path-input", "value", allow_duplicate=True),
            Input("save-local-btn", "n_clicks"),
            State("csv-file-path", "children"),
            prevent_initial_call=True,
        )
        def open_local_modal(open_n, csv_file_path):
            df_to_save = displaying_df()
            if df_to_save is None:
                return (
                    create_notification(message="No Dataframe loaded", position="center"),
                    False,
                    no_update,
                )

            file_name = os.path.basename(csv_file_path)
            if file_name.endswith(".parquet"):
                file_name = file_name.replace(".parquet", ".csv")
            current_path = os.getcwd()

            return None, True, os.path.join(current_path, file_name)

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Output("local-file-save-modal", "opened", allow_duplicate=True),
            Input("save-csv-local-btn", "n_clicks"),
            State("save-csv-path-input", "value"),
            State("filtered-save-as", "checked"),
            prevent_initial_call=True,
        )
        def open_local_saver(save_n, save_path, filtered_save_as):
            df_to_save = displaying_df(filtred_apply=filtered_save_as)
            if save_path:
                try:
                    if save_path.endswith(".parquet"):
                        df_to_save.write_parquet(save_path)
                    elif save_path.endswith(".csv"):
                        df_to_save.write_csv(save_path)
                except Exception as e:
                    return (
                        create_notification(message=f"File Save Error: {e}", position="center"),
                        False,
                    )
                return (
                    create_notification(
                        title="Saved",
                        message=f"file saved to {save_path}",
                        icon_name="bx-smile",
                    ),
                    False,
                )
            return (
                create_notification(message=f"no save path given", position="center"),
                False,
            )
