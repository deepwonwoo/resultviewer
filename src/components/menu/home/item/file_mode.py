import polars as pl
import dash_mantine_components as dmc
from dash import html, Output, Input, State, Patch, no_update, exceptions, ctx
from components.dag.column_definitions import generate_column_definitions
from utils.db_management import WORKSPACE, USERNAME, SCRIPT, get_cache, set_cache, get_dataframe, set_dataframe
from utils.component_template import create_notification, get_icon
from utils.dataframe_operations import file2df, validate_df, create_directory
from utils.logging_utils import logger, debugging_decorator
from utils.dataframe_operations import exit_edit_mode, get_lock_status, enter_edit_mode
from components.menu.home.item.workspace_explore import FileExplorer


class FileMode:
    ENTER_TEXT = "Read Mode에서 수정한 내용은 사라집니다. WorkSpace 원본에 접근하시겠습니까?"
    EXIT_TEXT = "수정한 내용을 WorkSpace 에 직접 저장 후 이용해주세요. 정말 Read Mode 로 전환하시겠습니까?"

    def layout(self):
        return html.Div(
            [
                dmc.SegmentedControl(
                    id="file-mode-control",
                    data=[{"value": "read", "label": "Read Mode"}, {"value": "edit", "label": "Edit Mode"}],
                    value="",
                    size="xs",
                    disabled=True,
                ),
                dmc.Modal(
                    title="Entering Edit Mode",
                    id="enter-edit-modal",
                    zIndex=10000,
                    children=[
                        dmc.Text(children=[], id="enter-edit-text"),
                        dmc.Space(h=10),
                        dmc.Checkbox(id="remain-edited-waiver", label="Read Mode 에서 수행한 waiver 정보를 가져가기(개발 중)", checked=False, color="red", disabled=True),
                        dmc.Group([dmc.Button("Yes", id="enter-edit-btn")], justify="flex-end"),
                    ],
                    size="45%",
                    centered=True,
                ),
                dmc.Modal(
                    title="Exiting Edit Mode",
                    id="exit-edit-modal",
                    zIndex=10000,
                    children=[dmc.Text(children=[], id="exit-edit-text"), dmc.Space(h=10), dmc.Group([dmc.Button("Yes", id="exit-edit-btn")], justify="flex-end")],
                    size="45%",
                    centered=True,
                ),
            ]
        )

    def register_callbacks(self, app):

        @app.callback(
            Output("file-mode-control", "value", allow_duplicate=True),
            Output("file-mode-control", "disabled", allow_duplicate=True),
            Output("notifications", "children", allow_duplicate=True),
            Output("enter-edit-modal", "opened", allow_duplicate=True),
            Output("exit-edit-modal", "opened", allow_duplicate=True),
            Output("enter-edit-text", "children", allow_duplicate=True),
            Output("exit-edit-text", "children", allow_duplicate=True),
            Input("file-mode-control", "value"),
            Input("csv-file-path", "children"),
            State("enter-edit-modal", "opened"),
            State("exit-edit-modal", "opened"),
            prevent_initial_call=True,
        )
        def handle_mode_change(new_mode, file_path, o1, o2):
            print("handle_mode_change start")
            if o1 or o2:
                return no_update, False, None, False, False, no_update, no_update
            if not file_path or not file_path.startswith("WORKSPACE"):
                return "", True, None, False, False, no_update, no_update

            if (ctx.triggered_id == "csv-file-path") or (new_mode == ""):
                return "read", False, None, False, False, no_update, no_update

            if new_mode == "edit":
                file_path = file_path.replace("WORKSPACE", WORKSPACE)
                lock, locked_by = get_lock_status(file_path)
                if lock:
                    return (
                        "read",
                        no_update,
                        create_notification(title="Cannot enter Edit Mode", message=f"File is locked by {locked_by}.", position="center"),
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                    )
                return "read", False, None, True, False, self.ENTER_TEXT, no_update
            else:
                return "edit", False, None, False, True, no_update, self.EXIT_TEXT

        @app.callback(
            Output("file-mode-control", "value", allow_duplicate=True),
            Output("file-mode-control", "disabled", allow_duplicate=True),
            Output("notifications", "children", allow_duplicate=True),
            Output("enter-edit-modal", "opened", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("remain-edited-waiver", "checked"),
            Input("enter-edit-btn", "n_clicks"),
            State("csv-file-path", "children"),
            State("remain-edited-waiver", "checked"),
            prevent_initial_call=True,
        )
        def enter_edit(n, file_path, checked):
            if n is None:
                raise exceptions.PreventUpdate

            file_path = file_path.replace("WORKSPACE", WORKSPACE)
            lock, locked_by = get_lock_status(file_path)

            if lock:
                return (no_update, no_update, create_notification(title="Cannot enter Edit Mode", message=f"File is locked by {locked_by}.", position="center"), False, no_update, False)

            success = enter_edit_mode(file_path)
            if not success:
                return no_update, False, create_notification(f"Failed to enter Edit Mode."), False, no_update, False

            try:
                df_workspace = validate_df(file_path)
            except:
                return no_update, False, create_notification(f"Failed to read a file from WorkSpace."), False, no_update, False
            if checked and ("waiver" in df_workspace.columns):
                df_local = get_dataframe("df")
                df_local = df_local.select("waiver", "user").rename({"waiver": "waiver_local", "user": "user_local"})
                dff = pl.concat([df_workspace, df_local], how="horizontal")
                conditions_expr = (
                    (pl.col("waiver") != pl.col("waiver_local"))
                    & (pl.col("user_local").str.starts_with(USERNAME))
                    & ((pl.col("user") == USERNAME) | ((pl.col("waiver_local") != "Result") & (pl.col("waiver") != "Fixed")))
                )
                update_waiver_column = pl.when(conditions_expr).then(pl.col("waiver_local")).otherwise(pl.col("waiver")).alias("waiver")
                update_user_column = pl.when(conditions_expr).then(pl.col("user_local")).otherwise(pl.col("user")).alias("user")
                dff = dff.with_columns(update_waiver_column, update_user_column)
                df_workspace = dff.select(pl.exclude(["waiver_local", "user_local"]))

            set_dataframe("df", df_workspace)
            updated_columnDefs = generate_column_definitions(df_workspace)
            return ("edit", no_update, create_notification(title="Entering Edit Mode", message="Success to enter Edit Mode", icon_name="bx-smile"), no_update, updated_columnDefs, False)

        @app.callback(
            Output("file-mode-control", "value", allow_duplicate=True),
            Output("file-mode-control", "disabled", allow_duplicate=True),
            Output("notifications", "children", allow_duplicate=True),
            Output("exit-edit-modal", "opened", allow_duplicate=True),
            Input("exit-edit-btn", "n_clicks"),
            State("csv-file-path", "children"),
            prevent_initial_call=True,
        )
        def enter_edit(n, file_path):
            if n is None:
                raise exceptions.PreventUpdate
            exit_edit_mode(file_path)

            return "read", no_update, create_notification(title="Entering Read Mode", message="Success to enter Read Mode", icon_name="bx-smile"), no_update
