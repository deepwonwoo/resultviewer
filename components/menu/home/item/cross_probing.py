import re
import socket
import polars as pl
import dash_mantine_components as dmc
from dash import Input, Output, State
from utils.component_template import get_icon, create_notification
from utils.db_management import SSDF
from utils.logging_utils import logger


class CrossProber:

    def __init__(self):
        self.CP = SSDF.cp
        self.CP_socket = self.create_connection() if all(self.CP.values()) else False
        self.CP_layout = self.cp_layout()
        self.current_view = ""
        self.history = []

    def create_connection(self):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)
            client_socket.connect((self.CP["host"], self.CP["port"]))
            logger.info("Successfully connected to CP server.")
            return client_socket
        except (socket.error, socket.timeout) as e:
            logger.error(f"Failed to connect to CP server: {e}")
            return False

    def cp_layout(self):
        return self.cp_connected_layout() if self.CP_socket else self.cp_disconnected_layout()

    def cp_connected_layout(self):
        return dmc.Group(
            [
                get_icon("bx-wifi"),
                dmc.Tooltip(
                    label="Select Net/Instance and Column, Middle click on a row to CrossProbe",
                    color="grey",
                    withArrow=True,
                    children=dmc.Group(
                        [
                            dmc.SegmentedControl(
                                id="cp-object-segmented",
                                value="inst",
                                color="red.5",
                                data=[{"value": "net", "label": "Net"}, {"value": "inst", "label": "Instance"}],
                                size="xs",
                            ),
                            dmc.Select(
                                id="cp-column-select",
                                data=[],
                                placeholder="Select column",
                                style={"width": 150},
                                size="xs",
                            ),
                        ]
                    ),
                ),
                dmc.TextInput(
                    id="cp-manual-input",
                    placeholder="manual CrossProbing",
                    rightSection=dmc.ActionIcon(
                        get_icon("bx-send"), id="cp-manual-button", size="sm", color="grey", variant="outline"
                    ),
                    style={"width": 200},
                    size="xs",
                ),
            ]
        )

    def cp_disconnected_layout(self):
        return dmc.Tooltip(
            label="Open from VSE/BTS to CrossProbe",
            color="grey",
            withArrow=True,
            children=dmc.Button(
                "Disabled",
                leftSection=get_icon("bx-wifi-off"),
                size="xs",
                disabled=True,
                rightSection=dmc.SegmentedControl(
                    id="cp-object-segmented", value="", color="black", data=[], size="xs", fullWidth=True
                ),
            ),
        )

    def layout(self):
        return dmc.Group([dmc.Text(f"CrossProbe: ", fw=500, size="sm", c="gray"), self.CP_layout], gap=2)

    def send_message(self, message):
        """Usage:
        select -obj inst -hier top1.top2.top3 -name object_names
        pushDesign -top true -hier top1.path1.path2
        selectCurObject -obj net(or inst) -name object_names
        """
        try:
            self.CP_socket.sendall(message.encode())
            return create_notification(message=f"CP command: {message}", title="CrossProbing")
        except socket.timeout:
            return create_notification(message="Timed out while sending message", title="CrossProbing", color="red")
        except Exception as e:
            return create_notification(message=f"Error: {e}", title="CrossProbing", color="red")

    def close_connection(self):
        if self.CP_socket:
            try:
                self.CP_socket.close()
            except Exception as e:
                print(f"Error closing connection: {e}")

    def hier_name(self, s, delimiter="."):
        def remove_initial_x(s):
            s = re.sub(r"^[xX]{2}(?!or)", "x", s, flags=re.IGNORECASE)
            s = re.sub(r"^[xX]", "", s, flags=re.IGNORECASE)
            return s

        def remove_dot_main(s):
            return re.sub(r"\.main$", "", s)

        s = s.split("@")[0].replace("/", ".")
        s = remove_dot_main(s)

        paths = s.split(delimiter)
        if len(paths) > 1:
            paths = [remove_initial_x(path) for path in paths]
            s = delimiter.join(paths)
        try:
            hier_path, name = s.rsplit(delimiter, 1)  # 오른쪽에서부터 문자열을 '.'으로 분리
        except ValueError:  # '.'이 없어서 분리할 수 없는 경우
            hier_path = ""  # hier_path를 빈 문자열로 설정
            name = s  # name에 입력받은 문자열을 그대로 반환
        return hier_path, name

    def remove_init_r_m(self, obj, selected_name):
        # remove 'm' or 'r' at the begining of instance name
        if obj == "inst" and len(selected_name) > 1:
            if selected_name[0] == "r" or selected_name[0] == "m":
                selected_name = selected_name[1:]
        return selected_name

    def cross_probing(self, selected_rows, obj, cp_col):
        logger.info(f"cross_probing! (obj:{obj}, tool:{cp_col})")
        if not obj or not cp_col:
            noti = create_notification(message="select 'net/instance' or 'column' to crossprobe")
            return noti, []

        selected_row = selected_rows[0]
        value = selected_row[cp_col]
        request = SSDF.request
        groupBy = [col["id"] for col in request.get("rowGroupCols", [])]

        selected_hier_path, selected_name = self.hier_name(value)
        selected_name = self.remove_init_r_m(obj, selected_name)

        # Group CrossProbing
        if groupBy:
            dff = SSDF.dataframe
            for gc in groupBy:
                dff = dff.filter(pl.col(gc) == selected_row[gc])

            names = set([selected_name])
            for group_value in dff[cp_col]:
                group_hier_path, group_hier_name = self.hier_name(group_value)
                if group_hier_path == selected_hier_path:
                    names.add(self.remove_init_r_m(obj, group_hier_name))

                elif group_hier_path.startswith(selected_hier_path):
                    group_hier_path = group_hier_path.replace(selected_hier_path, "")
                    if len(group_hier_path) and group_hier_path[0] == ".":
                        names.add(self.remove_init_r_m(obj, group_hier_path.split(".")[1]))

            if self.current_view == selected_hier_path:
                # Single Instance CrossProbing
                msg = f"selectCurObject -obj {obj} -name {','.join(names)}\n"
            else:
                msg = f"select -obj {obj} -hier {selected_hier_path} -name {','.join(names)}\n"
        else:
            # if save view hierarchy
            if self.current_view == selected_hier_path:  # Single Instance CrossProbing

                msg = f"selectCurObject -obj {obj} -name {selected_name}\n"
            else:  # Single Instance CrossProbing

                msg = (
                    f"select -obj {obj} -hier {selected_hier_path} -name {selected_name}\n"
                    if selected_hier_path
                    else f"select -obj {obj} -name {selected_name}\n"
                )
                self.current_view = selected_hier_path

        noti = self.send_message(msg)

        return noti, []

    def register_callbacks(self, app):

        @app.callback(
            Output("cp-column-select", "data"), Input("aggrid-table", "columnDefs"), prevent_initial_call=True
        )
        def update_cp_columns(columnDefs):
            return [coldef["field"] for coldef in columnDefs]

        # middel click
        app.clientside_callback(
            """
            function(gridId) {
                dash_ag_grid.getApiAsync(gridId).then((grid) => {
                    console.log("Grid click");
                    grid.addEventListener('cellMouseDown', (e) => {
                        if (e.event.button == 1) {
                            console.log("middle click");
                            e.api.setNodesSelected({nodes: [e.node], newValue: true})
                        } 
                    })
                })
                return dash_clientside.no_update
            }
            """,
            Output("aggrid-table", "id", allow_duplicate=True),
            Input("aggrid-table", "id"),
        )

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Input("cp-manual-button", "n_clicks"),
            State("cp-manual-input", "value"),
            State("cp-object-segmented", "value"),
            prevent_initial_call=True,
        )
        def manual_crossprobing(n, cp_name, obj):
            if n and cp_name:

                selected_hier_path, selected_name = self.hier_name(cp_name)
                selected_name = self.remove_init_r_m(obj, selected_name)
                cp_command = f"select -obj {obj} -hier {selected_hier_path} -name {selected_name}\n"
                noti = self.send_message(cp_command)
                return noti
            return None
