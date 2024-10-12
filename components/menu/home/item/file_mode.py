import os
import dash_mantine_components as dmc
from dash import Input, Output, State, html, exceptions, ctx, no_update
from components.grid.dag.column_definitions import *
from utils.db_management import SSDF
from utils.config import CONFIG
from utils.data_processing import *
from utils.file_operations import get_lock_status, add_viewer_to_lock_file
from utils.component_template import create_notification


def enter_edit_mode(file_path):
    logger.debug("enter_edit_mode")
    SSDF.release_lock()
    return SSDF.acquire_lock(file_path)


def exit_edit_mode(file_path):
    SSDF.release_lock()


class FileMode:
    ENTER_TEXT = (
        "Read Mode에서 수정한 내용은 사라집니다. WorkSpace 원본에 접근하시겠습니까?"
    )
    EXIT_TEXT = "수정한 내용을 WorkSpace 에 직접 저장 후 이용해주세요. 정말 Read Mode 로 전환하시겠습니까?"

    def layout(self):
        return html.Div(
            [
                dmc.SegmentedControl(
                    id="file-mode-control",
                    data=[
                        {"value": "read", "label": "Read Mode"},
                        {"value": "edit", "label": "Edit Mode"},
                    ],
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
                        dmc.Checkbox(
                            id="remain-edited-waiver",
                            label="Read Mode 에서 수행한 waiver 정보를 가져가기(개발 중)",
                            checked=False,
                            color="red",
                            disabled=True,
                        ),
                        dmc.Group(
                            [dmc.Button("Yes", id="enter-edit-btn")], justify="flex-end"
                        ),
                    ],
                    size="45%",
                    centered=True,
                ),
                dmc.Modal(
                    title="Exiting Edit Mode",
                    id="exit-edit-modal",
                    zIndex=10000,
                    children=[
                        dmc.Text(children=[], id="exit-edit-text"),
                        dmc.Space(h=10),
                        dmc.Group(
                            [dmc.Button("Yes", id="exit-edit-btn")], justify="flex-end"
                        ),
                    ],
                    size="45%",
                    centered=True,
                ),
            ]
        )

    def register_callbacks(self, app):

        @app.callback(
            Output("file-mode-control", "value", allow_duplicate=True),
            Output("notifications", "children", allow_duplicate=True),
            Output("enter-edit-modal", "opened", allow_duplicate=True),
            Output("exit-edit-modal", "opened", allow_duplicate=True),
            Output("enter-edit-text", "children", allow_duplicate=True),
            Output("exit-edit-text", "children", allow_duplicate=True),
            Input("file-mode-control", "value"),
            State("flex-layout", "model"),
            State("enter-edit-modal", "opened"),
            State("exit-edit-modal", "opened"),
            prevent_initial_call=True,
        )
        def handle_mode_change(new_mode, model_layout, o1, o2):
            if o1 or o2:
                return no_update, None, False, False, no_update, no_update
            file_path = model_layout["layout"]["children"][0]["children"][0]["name"]
            if not file_path or not file_path.startswith(
                "WORKSPACE"
            ):  # if local file open
                return "read", None, False, False, no_update, no_update
            if new_mode == "init":  # read moad
                return "read", None, False, False, no_update, no_update
            if ctx.triggered_id == "file-mode-control":
                if new_mode == "edit":
                    file_path = file_path.replace("WORKSPACE", CONFIG.WORKSPACE)
                    lock, locked_by = get_lock_status(file_path)
                    if lock:
                        current_user = os.getenv("USER")
                        return "read", None, no_update, no_update, no_update, no_update
                    return "read", None, True, False, self.ENTER_TEXT, no_update
                else:
                    return "edit", None, False, True, no_update, self.EXIT_TEXT

        @app.callback(
            Output("file-mode-control", "value", allow_duplicate=True),
            Output("notifications", "children", allow_duplicate=True),
            Output("enter-edit-modal", "opened", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("remain-edited-waiver", "checked"),
            Input("enter-edit-btn", "n_clicks"),
            State("flex-layout", "model"),
            State("remain-edited-waiver", "checked"),
            prevent_initial_call=True,
        )
        def enter_edit(n, model_layout, checked):

            file_path = model_layout["layout"]["children"][0]["children"][0]["name"]
            file_path = file_path.replace("WORKSPACE", CONFIG.WORKSPACE)
            lock, locked_by = get_lock_status(file_path)
            if lock:
                return no_update, None, False, no_update, False

            if enter_edit_mode(file_path):
                try:
                    df_workspace = validate_df(file_path)
                except:
                    return no_update, None, False, no_update, False
                if checked and ("waiver" in df_workspace.columns):
                    df_local = SSDF.dataframe
                    df_local = df_local.select("waiver", "user").rename(
                        {"waiver": "waiver_local", "user": "user_local"}
                    )
                    dff = pl.concat([df_workspace, df_local], how="horizontal")
                    conditions_expr = (
                        (pl.col("waiver") != pl.col("waiver_local"))
                        & (pl.col("user_local").str.starts_with(CONFIG.USERNAME))
                        & (
                            (pl.col("user") == CONFIG.USERNAME)
                            | (
                                (pl.col("waiver_local") != "Result")
                                & (pl.col("waiver") != "Fixed")
                            )
                        )
                    )
                    update_waiver_column = (
                        pl.when(conditions_expr)
                        .then(pl.col("waiver_local"))
                        .otherwise(pl.col("waiver"))
                        .alias("waiver")
                    )
                    update_user_column = (
                        pl.when(conditions_expr)
                        .then(pl.col("user_local"))
                        .otherwise(pl.col("user"))
                        .alias("user")
                    )
                    dff = dff.with_columns(update_waiver_column, update_user_column)
                    df_workspace = dff.select(
                        pl.exclude(["waiver_local", "user_local"])
                    )

                SSDF.dataframe = df_workspace
                updated_columnDefs = generate_column_definitions(df_workspace)
                return "edit", None, no_update, updated_columnDefs, False
            else:
                return no_update, None, False, no_update, False

        @app.callback(
            Output("file-mode-control", "value", allow_duplicate=True),
            Output("notifications", "children", allow_duplicate=True),
            Output("exit-edit-modal", "opened", allow_duplicate=True),
            Input("exit-edit-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True,
        )
        def exit_edit(n, model_layout):
            file_path = model_layout["layout"]["children"][0]["children"][0]["name"]
            if n is None:
                raise exceptions.PreventUpdate
            exit_edit_mode(file_path)
            return "read", None, no_update
