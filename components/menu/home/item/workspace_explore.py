import os
import shutil
import datetime
import dash_mantine_components as dmc
from pathlib import Path
from dash import html, Output, Input, State, no_update, ctx, ALL, Patch, dcc, exceptions
from components.grid.dag.column_definitions import generate_column_definitions

from utils.file_operations import get_file_owner, get_lock_status
from utils.data_processing import file2df
from utils.logging_utils import logger
from utils.db_management import SSDF
from utils.config import CONFIG


class FileExplorer:
    def __init__(self, id_prefix=""):
        self.id_prefix = id_prefix
        self.datetime_format = "%b %d, %Y %H:%M"
        self.files = []

    def layout(self) -> html.Div:
        return html.Div(
            [
                dcc.Store(id=f"{self.id_prefix}stored_cwd", data=CONFIG.WORKSPACE),
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
                            CONFIG.WORKSPACE.replace(CONFIG.WORKSPACE, "WORKSPACE"),
                            c="blue",
                            id=f"{self.id_prefix}cwd",
                            size="xs",
                        ),
                    ],
                    justify="flex-start",
                    gap="sm",
                ),
                dmc.Group(
                    [
                        dmc.TextInput(
                            placeholder="Search files...",
                            leftSection=get_icon("bx-file-find"),
                            id=f"{self.id_prefix}search_input",
                            style={"width": "80%"},
                        ),
                        dmc.Button("Search", id=f"{self.id_prefix}search_button"),
                    ],
                    mt=10,
                    mb=10,
                ),
                html.Div(
                    id=f"{self.id_prefix}cwd_files",
                    style={"height": "auto" if self.id_prefix else 500, "overflow": "scroll"},
                ),
                dmc.Pagination(id=f"{self.id_prefix}pagination", total=1, value=1, siblings=1, boundaries=1),
            ]
        )

    def search_files(self, root_dir, pattern):
        matched_files = []
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if pattern.lower() in file.lower():
                    full_path = os.path.join(root, file)
                    matched_files.append(self.get_file_details(full_path))
        return matched_files

    def get_file_details(self, file_path):
        path = Path(file_path)
        details = self.file_info(path)
        details["filename"] = html.A(
            path.name,
            href="#",
            id={"type": f"{self.id_prefix}open-workspace-file", "index": file_path},
            title=file_path.replace(CONFIG.WORKSPACE, "WORKSPACE"),
            n_clicks=0,
        )

        details["icon"] = get_icon("bx-file")

        if not self.id_prefix:
            details["option"] = self.create_file_options(file_path, path.name)

        return details

    def create_file_options(self, file_path, file_name):
        file_owner = get_file_owner(file_path)
        lock, locked_by = get_lock_status(file_path)
        has_permission = (file_owner == CONFIG.USERNAME) and not lock

        return dmc.ButtonGroup(
            [
                dcc.Store(id={"type": f"{self.id_prefix}refresh-flag", "index": file_path}, data=False),
                dmc.Tooltip(
                    dmc.ActionIcon(
                        get_icon("copy"),
                        variant="transparent",
                        id={"type": f"{self.id_prefix}copy-workspace-file", "index": file_path},
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
                                    id={"type": f"{self.id_prefix}rename-workspace-file", "index": file_path},
                                    n_clicks=0,
                                    disabled=not has_permission,
                                ),
                                label="Rename" if has_permission else "No permission to rename",
                                openDelay=500,
                            )
                        ),
                        dmc.MenuDropdown(
                            [
                                dmc.MenuLabel(
                                    dmc.TextInput(
                                        value=file_name,
                                        id={
                                            "type": f"{self.id_prefix}rename-workspace-file-newfilename",
                                            "index": file_path,
                                        },
                                    )
                                ),
                                dmc.MenuItem(
                                    "Confirm",
                                    n_clicks=0,
                                    id={
                                        "type": f"{self.id_prefix}rename-workspace-file-confirm-btn",
                                        "index": file_path,
                                    },
                                ),
                            ]
                        ),
                    ],
                    disabled=not has_permission,
                ),
                dmc.Tooltip(
                    dmc.ActionIcon(
                        get_icon("remove"),
                        variant="subtle",
                        id={"type": f"{self.id_prefix}remove-workspace-file", "index": file_path},
                        n_clicks=0,
                        disabled=not has_permission,
                    ),
                    label="Remove" if has_permission else "No permission to remove",
                    openDelay=500,
                ),
            ]
        )

    def file_info(self, path):
        owner = get_file_owner(path)
        is_locked, locked_by = get_lock_status(path)
        file_stat = path.stat()
        size = self._format_size(file_stat.st_size)

        return {
            "icon": path.suffix if not path.name.startswith(".") else path.name,
            "filename": "",
            "option": "",
            "locked": locked_by if is_locked and not self.id_prefix else "",
            "size": size,
            "owner": owner,
            "created": self._format_timestamp(file_stat.st_ctime),
        }

    def _format_timestamp(self, timestamp: float) -> str:
        return datetime.datetime.fromtimestamp(timestamp).strftime(self.datetime_format)

    def _format_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"

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

                return stored_cwd.replace(CONFIG.WORKSPACE, "WORKSPACE")
            if currentdir == "WORKSPACE":
                return "WORKSPACE"
            if currentdir.startswith("WORKSPACE"):
                currentdir = currentdir.replace("WORKSPACE", CONFIG.WORKSPACE)
            parent = Path(currentdir).parent.as_posix()
            return parent.replace(CONFIG.WORKSPACE, "WORKSPACE")

        @app.callback(
            Output(f"{self.id_prefix}cwd_files", "children"),
            Output(f"{self.id_prefix}pagination", "total"),
            Input(f"{self.id_prefix}cwd", "children"),
            Input(f"{self.id_prefix}search_button", "n_clicks"),
            Input(f"{self.id_prefix}pagination", "value"),
            Input({"type": f"{self.id_prefix}refresh-flag", "index": ALL}, "data"),
            State(f"{self.id_prefix}search_input", "value"),
            prevent_initial_call=True,
        )
        def list_cwd_files(cwd, n_clicks, page, refresh_ns, search_pattern):
            if (
                ctx.triggered_id
                and isinstance(ctx.triggered_id, dict)
                and ctx.triggered_id.get("type") == f"{self.id_prefix}refresh-flag"
                and sum(refresh_ns) == 0
            ):
                return no_update

            if cwd and cwd.startswith("WORKSPACE"):
                cwd = cwd.replace("WORKSPACE", CONFIG.WORKSPACE)
            else:
                cwd = ""

            if ctx.triggered_id == f"{self.id_prefix}search_button" and search_pattern:
                all_file_details = self.search_files(cwd, search_pattern)
            else:
                path = Path(cwd)
                all_file_details = []
                if path.is_dir():
                    files = sorted(os.listdir(path), key=str.lower)
                    self.files = []
                    for i, file in enumerate(files):

                        filepath = Path(file)
                        full_path = os.path.join(cwd, filepath.as_posix())

                        self.files.append(full_path.replace(CONFIG.WORKSPACE, "WORKSPACE"))
                        if file.endswith(".lock"):
                            continue

                        is_dir = Path(full_path).is_dir()
                        details = self.file_info(Path(full_path))

                        if is_dir:
                            details["filename"] = html.A(
                                file,
                                href="#",
                                id={"type": f"{self.id_prefix}listed_file", "index": i},
                                title=full_path.replace(CONFIG.WORKSPACE, "WORKSPACE"),
                                style={"fontWeight": "bold", "fontSize": 15},
                            )
                            details["icon"] = get_icon("bx-folder")
                        else:

                            details["filename"] = html.A(
                                file,
                                href="#",
                                id={"type": f"{self.id_prefix}open-workspace-file", "index": full_path},
                                title=full_path.replace(CONFIG.WORKSPACE, "WORKSPACE"),
                                n_clicks=0,
                            )

                            if not self.id_prefix:
                                details["option"] = dmc.ButtonGroup(
                                    [
                                        dcc.Store(
                                            id={"type": f"{self.id_prefix}refresh-flag", "index": full_path}, data=False
                                        ),
                                        dmc.Tooltip(
                                            dmc.ActionIcon(
                                                get_icon("copy"),
                                                variant="transparent",
                                                id={"type": f"{self.id_prefix}copy-workspace-file", "index": full_path},
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
                                                    )
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
                                    ]
                                )

                            details["icon"] = get_icon("bx-file")

                        all_file_details.append(details)

            table_header = [
                dmc.TableThead(
                    dmc.TableTr(
                        [
                            dmc.TableTh("", style={"width": "30px"}),
                            dmc.TableTh("Filename"),
                            dmc.TableTh("Locked"),
                            dmc.TableTh("Size"),
                            dmc.TableTh("Owner"),
                            dmc.TableTh("Created"),
                            dmc.TableTh("Actions", style={"width": "100px"}),
                        ]
                    )
                )
            ]
            # 페이지네이션 로직
            items_per_page = 20
            start = (page - 1) * items_per_page
            end = start + items_per_page
            paginated_files = all_file_details[start:end]

            table_body = [
                dmc.TableTr(
                    [
                        dmc.TableTd(details["icon"]),
                        dmc.TableTd(details["filename"]),
                        dmc.TableTd(details["locked"]),
                        dmc.TableTd(details["size"]),
                        dmc.TableTd(details["owner"]),
                        dmc.TableTd(details["created"]),
                        dmc.TableTd(details.get("option", "")),
                    ]
                )
                for details in paginated_files
            ]

            table = dmc.Table(table_header + table_body, striped=True, highlightOnHover=True)
            total_pages = -(-len(all_file_details) // items_per_page)  # 올림 나눗셈

            return table, total_pages

        @app.callback(
            Output(f"{self.id_prefix}stored_cwd", "data"),
            Input({"type": f"{self.id_prefix}listed_file", "index": ALL}, "n_clicks"),
            State({"type": f"{self.id_prefix}listed_file", "index": ALL}, "title"),
        )
        def store_clicked_file(n_clicks, title):
            if not n_clicks or set(n_clicks) == {None}:
                raise exceptions.PreventUpdate
            index = ctx.triggered_id["index"]

            return self.files[index]

        if not self.id_prefix:

            @app.callback(
                Output({"type": "refresh-flag", "index": ALL}, "data"),
                Output("workspace-drawer", "opened", allow_duplicate=True),
                Output("aggrid-table", "columnDefs", allow_duplicate=True),
                Output("aggrid-table", "dashGridOptions", allow_duplicate=True),
                Output("total-row-count", "children", allow_duplicate=True),
                Output("flex-layout", "model", allow_duplicate=True),
                Output("csv-mod-time", "data", allow_duplicate=True),
                Output("notifications", "children", allow_duplicate=True),
                Input({"type": "open-workspace-file", "index": ALL}, "n_clicks"),
                Input({"type": "copy-workspace-file", "index": ALL}, "n_clicks"),
                Input({"type": "rename-workspace-file-confirm-btn", "index": ALL}, "n_clicks"),
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

                try:
                    if triggered_btn == "open-workspace-file":
                        df = file2df(file_path)
                        patched_dashGridOptions = Patch()
                        SSDF.tree_mode = False
                        SSDF.tree_col = None
                        SSDF.viewmode = None
                        SSDF.propa_rule = None
                        patched_dashGridOptions["treeData"] = False
                        if lock:
                            ret_noti = create_notification(
                                title="ReadOnly",
                                message=f"file is locked by {locked_by}, this is ReadOnly mode",
                                position="center",
                                icon_name="bx-info-circle",
                            )

                        ret_drawer_open = False
                        ret_columnDefs = generate_column_definitions(df)
                        ret_dashGridOptions = patched_dashGridOptions
                        ret_total_row_count = f"Total Rows: {len(df)}"
                        ret_display_file_path = Patch()
                        ret_display_file_path["layout"]["children"][0]["children"][0]["name"] = file_path.replace(
                            CONFIG.WORKSPACE, "WORKSPACE"
                        )

                        ret_csv_mod_time = os.path.getmtime(file_path)

                    elif triggered_btn == "copy-workspace-file":
                        index = copy_ns.index(1)
                        ret_refresh_flags[index] = True
                        current_time = datetime.datetime.now().time().strftime("%m%d_%H:%M")
                        name, ext = os.path.splitext(file_path)
                        new_file_path = f"{name}_{CONFIG.USERNAME}_{current_time}{ext}"
                        shutil.copy(file_path, new_file_path)
                        os.chmod(new_file_path, 0o777)

                    elif triggered_btn == "rename-workspace-file-confirm-btn":
                        index = rename_ns.index(1)
                        new_filename = new_filenames[index]
                        dir_path, old_file_name = os.path.split(file_path)
                        new_path = os.path.join(dir_path, new_filename)

                        if os.path.exists(new_path):
                            ret_noti = ret_noti = create_notification(
                                message=f"file '{file_path.replace(CONFIG.WORKSPACE, 'WORKSPACE')}' already exists",
                                position="center",
                                icon_name="bx-info-circle",
                            )
                        elif not file_owner == CONFIG.USERNAME:
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
                        elif not file_owner == CONFIG.USERNAME:
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
                    ret_noti = create_notification(message=f"Error: {e}", position="center", icon_name="bx-info-circle")

                return (
                    ret_refresh_flags,
                    ret_drawer_open,
                    ret_columnDefs,
                    ret_dashGridOptions,
                    ret_total_row_count,
                    ret_display_file_path,
                    ret_csv_mod_time,
                    ret_noti,
                )
