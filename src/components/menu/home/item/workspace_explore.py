import os
import datetime
import shutil
import pandas as pd
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
from pathlib import Path
from dash import (
    Input,
    Output,
    State,
    html,
    exceptions,
    ctx,
    no_update,
    ALL,
    Patch,
    dcc,
    MATCH,
)
from components.dag.column_definitions import generate_column_definitions
from utils.process_helpers import (
    file2df,
    create_notification,
    validate_df,
    get_lock_status,
    get_file_owner,
    get_icon,
    backup_file,
    create_directory,
    debugging_decorator,
)
from utils.logging_utils import logger
from utils.db_management import WORKSPACE, USERNAME, SCRIPT, CACHE, DATAFRAME


class FileExplorer:
    def __init__(self, id_prefix=""):
        self.id_prefix = id_prefix

    def nowtimestamp(self, timestamp, fmt="%b %d, %Y %H:%M"):
        return datetime.datetime.fromtimestamp(timestamp).strftime(fmt)

    def file_info(self, path):
        owner = get_file_owner(path)
        is_locked, locked_by = get_lock_status(path)
        file_stat = path.stat()
        size = file_stat.st_size
        units = ["B", "KB", "MB", "GB", "TB"]
        index = 0
        while size > 1024 and index < 4:
            size /= 1024
            index += 1
        size_str = f"{size:.2f} {units[index]}" if path.is_file() else ""

        d = {
            "icon": path.suffix if not path.name.startswith(".") else path.name,
            "filename": "",
            "option": "",
            "locked": locked_by if is_locked and not self.id_prefix else "",
            "size": size_str,
            "owner": owner,
            "created": self.nowtimestamp(file_stat.st_ctime),
            # "modified": nowtimestamp(file_stat.st_mtime)
        }
        return d

    def layout(self) -> html.Div:
        return html.Div(
            [
                dcc.Store(id=f"{self.id_prefix}stored_cwd", data=WORKSPACE),
                dmc.Group(
                    [
                        dmc.Button(
                            "Parent directory",
                            id=f"{self.id_prefix}parent_dir",
                            leftSection="⬆️",
                            size="xs",
                            variant="gradient",
                        ),
                        dmc.Text(
                            WORKSPACE.replace(WORKSPACE, "WORKSPACE"),
                            c="blue",
                            id=f"{self.id_prefix}cwd",
                            size="xs",
                        ),
                    ],
                    justify="flex-start",
                    gap="sm",
                ),
                html.Br(),
                html.Div(
                    id=f"{self.id_prefix}cwd_files",
                    style={
                        "height": "auto" if self.id_prefix else 500,
                        "overflow": "scroll",
                    },
                ),
            ]
        )

    def register_callbacks(self, app):

        @app.callback(
            Output(f"{self.id_prefix}cwd", "children", allow_duplicate=True),
            Input(f"{self.id_prefix}stored_cwd", "data"),
            Input(f"{self.id_prefix}parent_dir", "n_clicks"),
            Input(f"{self.id_prefix}cwd", "children"),
            prevent_initial_call=True,
        )
        def get_parent_directory(stored_cwd, n_clicks, currentdir):

            triggered_id = ctx.triggered_id
            if triggered_id == f"{self.id_prefix}stored_cwd" and stored_cwd:

                return stored_cwd.replace(WORKSPACE, "WORKSPACE")
            if currentdir == "WORKSPACE":
                return "WORKSPACE"
            if currentdir.startswith("WORKSPACE"):
                currentdir = currentdir.replace("WORKSPACE", WORKSPACE)
            parent = Path(currentdir).parent.as_posix()
            return parent.replace(WORKSPACE, "WORKSPACE")

        @app.callback(
            Output(f"{self.id_prefix}cwd_files", "children"),
            Input(f"{self.id_prefix}cwd", "children"),
            Input({"type": f"{self.id_prefix}refresh-flag", "index": ALL}, "data"),
            prevent_initial_call=True,
        )
        def list_cwd_files(cwd, refresh_ns):

            if (
                ctx.triggered_id
                and isinstance(ctx.triggered_id, dict)
                and ctx.triggered_id.get("type") == f"{self.id_prefix}refresh-flag"
                and sum(refresh_ns) == 0
            ):
                return no_update

            if cwd and cwd.startswith("WORKSPACE"):
                cwd = cwd.replace("WORKSPACE", WORKSPACE)
            else:
                cwd = ""
            path = Path(cwd)
            all_file_details = []
            if path.is_dir():
                files = sorted(os.listdir(path), key=str.lower)
                for i, file in enumerate(files):
                    if file.endswith(".lock"):
                        continue
                    filepath = Path(file)
                    full_path = os.path.join(cwd, filepath.as_posix())
                    is_dir = Path(full_path).is_dir()

                    details = self.file_info(Path(full_path))

                    if is_dir:
                        details["filename"] = html.A(
                            file,
                            href="#",
                            id={"type": f"{self.id_prefix}listed_file", "index": i},
                            title=full_path.replace(WORKSPACE, "WORKSPACE"),
                            style={"fontWeight": "bold", "fontSize": 15},
                        )
                        details["icon"] = get_icon("bx-folder")
                    else:
                        details["filename"] = html.A(
                            file,
                            href="#",
                            id={
                                "type": f"{self.id_prefix}open-workspace-file",
                                "index": full_path,
                            },
                            title=full_path.replace(WORKSPACE, "WORKSPACE"),
                            n_clicks=0,
                        )

                        if not self.id_prefix:
                            details["option"] = dmc.ButtonGroup(
                                [
                                    dcc.Store(
                                        id={
                                            "type": f"{self.id_prefix}refresh-flag",
                                            "index": full_path,
                                        },
                                        data=False,
                                    ),
                                    dmc.Tooltip(
                                        dmc.ActionIcon(
                                            get_icon("copy"),
                                            variant="transparent",
                                            id={
                                                "type": f"{self.id_prefix}copy-workspace-file",
                                                "index": full_path,
                                            },
                                            n_clicks=0,
                                        ),
                                        label="Copy",
                                        openDelay=500,
                                    ),
                                    dmc.Menu(
                                        [
                                            dmc.MenuTarget(
                                                dmc.Tooltip(
                                                    dmc.ActionIcon(
                                                        get_icon("rename"),
                                                        variant="subtle",
                                                        id={
                                                            "type": f"{self.id_prefix}rename-workspace-file",
                                                            "index": full_path,
                                                        },
                                                        n_clicks=0,
                                                    ),
                                                    label="Rename",
                                                    openDelay=500,
                                                ),
                                            ),
                                            dmc.MenuDropdown(
                                                [
                                                    dmc.MenuLabel(
                                                        dmc.TextInput(
                                                            value=file,
                                                            id={
                                                                "type": f"{self.id_prefix}rename-workspace-file-newfilename",
                                                                "index": full_path,
                                                            },
                                                        )
                                                    ),
                                                    dmc.MenuItem(
                                                        "Confirm",
                                                        n_clicks=0,
                                                        id={
                                                            "type": f"{self.id_prefix}rename-workspace-file-confirm-btn",
                                                            "index": full_path,
                                                        },
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                    dmc.Tooltip(
                                        dmc.ActionIcon(
                                            get_icon("remove"),
                                            variant="subtle",
                                            id={
                                                "type": f"{self.id_prefix}remove-workspace-file",
                                                "index": full_path,
                                            },
                                            n_clicks=0,
                                        ),
                                        label="Remove",
                                        openDelay=500,
                                    ),
                                ],
                            )

                        details["icon"] = get_icon("bx-file")

                    all_file_details.append(details)

            df = pd.DataFrame(all_file_details)
            df = df.rename(columns={"icon": "", "option": ""})

            table = dbc.Table.from_dataframe(df, striped=False, bordered=False, hover=True, size="sm")
            return dbc.Spinner(
                html.Div(table),
                type="grow",
                spinner_style={"width": "3rem", "height": "3rem"},
                color="secondary",
            )

        @app.callback(
            Output(f"{self.id_prefix}stored_cwd", "data"),
            Input({"type": f"{self.id_prefix}listed_file", "index": ALL}, "n_clicks"),
            State({"type": f"{self.id_prefix}listed_file", "index": ALL}, "title"),
        )
        def store_clicked_file(n_clicks, title):
            if not n_clicks or set(n_clicks) == {None}:
                raise exceptions.PreventUpdate
            index = ctx.triggered_id["index"]
            return title[index]

        if not self.id_prefix:

            @app.callback(
                Output({"type": "refresh-flag", "index": ALL}, "data"),
                Output("workspace-drawer", "opened", allow_duplicate=True),
                Output("aggrid-table", "columnDefs", allow_duplicate=True),
                Output("aggrid-table", "dashGridOptions", allow_duplicate=True),
                Output("total-row-count", "children", allow_duplicate=True),
                Output("csv-file-path", "children", allow_duplicate=True),
                Output("csv-mod-time", "data", allow_duplicate=True),
                Output("notifications", "children", allow_duplicate=True),
                Output("file-mode", "children", allow_duplicate=True),
                Input({"type": "open-workspace-file", "index": ALL}, "n_clicks"),
                Input({"type": "copy-workspace-file", "index": ALL}, "n_clicks"),
                Input(
                    {"type": "rename-workspace-file-confirm-btn", "index": ALL},
                    "n_clicks",
                ),
                Input({"type": "remove-workspace-file", "index": ALL}, "n_clicks"),
                State({"type": "rename-workspace-file-newfilename", "index": ALL}, "value"),
                prevent_initial_call=True,
            )
            def handel_file_operations(open_ns, copy_ns, rename_ns, remove_ns, new_filenames):
                if not ctx.triggered_id or sum(open_ns + copy_ns + rename_ns + remove_ns) == 0:
                    raise exceptions.PreventUpdate

                triggered_btn = ctx.triggered_id["type"]
                file_path = ctx.triggered_id["index"]

                file_owner = get_file_owner(file_path)
                lock, locked_by = get_lock_status(file_path)

                ret_refresh_flags = [False] * len(open_ns)
                ret_drawer_open = no_update
                ret_columnDefs = no_update
                ret_dashGridOptions = no_update
                ret_total_row_count = no_update
                ret_display_file_path = no_update
                ret_csv_mod_time = no_update
                ret_noti = None
                ret_mode = no_update

                try:
                    if triggered_btn == "open-workspace-file":
                        df = file2df(file_path, workspace=not lock)
                        patched_dashGridOptions = Patch()
                        CACHE.set("TreeMode", False)
                        CACHE.set("TreeCol", None)
                        CACHE.set("viewmode", None)
                        CACHE.set("PropaRule", None)
                        CACHE.set("waiver_def", None)
                        patched_dashGridOptions["treeData"] = False
                        if lock:
                            ret_noti = create_notification(
                                title="ReadOnly",
                                message=f"file is locked by {locked_by}, this is ReadOnly mode",
                                position="center",
                                icon_name="bx-info-circle",
                            )
                            ret_mode = dmc.Badge("Read Only", radius="sm", size="xs", color="orange")
                        else:
                            ret_mode = ""
                        ret_drawer_open = False
                        ret_columnDefs = generate_column_definitions(df)
                        ret_dashGridOptions = patched_dashGridOptions
                        ret_total_row_count = f"Total Rows: {len(df)}"
                        ret_display_file_path = file_path.replace(WORKSPACE, "WORKSPACE")
                        ret_csv_mod_time = os.path.getmtime(file_path)

                    elif triggered_btn == "copy-workspace-file":
                        index = copy_ns.index(1)
                        ret_refresh_flags[index] = True
                        current_time = datetime.datetime.now().time().strftime("%m%d_%H:%M")
                        name, ext = os.path.splitext(file_path)
                        new_file_path = f"{name}_{USERNAME}_{current_time}{ext}"
                        shutil.copy(file_path, new_file_path)
                        os.chmod(new_file_path, 0o777)

                    elif triggered_btn == "rename-workspace-file-confirm-btn":
                        index = rename_ns.index(1)
                        new_filename = new_filenames[index]
                        dir_path, old_file_name = os.path.split(file_path)
                        new_path = os.path.join(dir_path, new_filename)

                        if os.path.exists(new_path):
                            ret_noti = ret_noti = create_notification(
                                message=f"file '{file_path.replace(WORKSPACE, 'WORKSPACE')}' already exists",
                                position="center",
                                icon_name="bx-info-circle",
                            )
                        elif not file_owner == USERNAME:
                            ret_noti = ret_noti = create_notification(
                                message=f"No permission to rename: file is owned by {file_owner}, ",
                                position="center",
                                icon_name="bx-info-circle",
                            )
                        elif lock:
                            ret_noti = ret_noti = create_notification(
                                message=f"file is locked by {locked_by}, can not renamed",
                                position="center",
                                icon_name="bx-info-circle",
                            )
                        else:
                            ret_refresh_flags[index] = True
                            os.rename(file_path, new_path)

                    elif triggered_btn == "remove-workspace-file":
                        if lock:
                            ret_noti = ret_noti = create_notification(
                                message=f"file is locked by {locked_by}, can not renamed",
                                position="center",
                                icon_name="bx-info-circle",
                            )
                        elif not file_owner == USERNAME:
                            ret_noti = ret_noti = create_notification(
                                message=f"No permission to remove: file is owned by {file_owner}, ",
                                position="center",
                                icon_name="bx-info-circle",
                            )
                        else:
                            index = remove_ns.index(1)
                            ret_refresh_flags[index] = True
                            os.remove(file_path)

                except Exception as e:
                    logger.debug(f"Error: {e}")
                    ret_noti = create_notification(
                        message=f"Error: {e}",
                        position="center",
                        icon_name="bx-info-circle",
                    )

                return (
                    ret_refresh_flags,
                    ret_drawer_open,
                    ret_columnDefs,
                    ret_dashGridOptions,
                    ret_total_row_count,
                    ret_display_file_path,
                    ret_csv_mod_time,
                    ret_noti,
                    ret_mode,
                )
