import os
import datetime
import re
import socket
import dash_mantine_components as dmc
from dash import Input, Output, State, html, exceptions, ctx, no_update, ALL, Patch
from components.grid.DAG.columnDef import generate_column_definitions
from utils.process_helpers import *
from utils.db_management import WORKSPACE, USERNAME, SCRIPT, CACHE, DATAFRAME
from utils.process_helpers import create_notification, backup_file
from utils.logging_config import logger


class CrossProber:

    def __init__(self):
        self.CP = CACHE.get("CP")
        self.CP_socket = self.create_connection() if all(self.CP.values()) else False
        self.connected_btn = self.cp_connected_btn()
        self.current_view = ""

    def create_connection(self):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)  # Default timeout set to 5 seconds
            client_socket.connect((self.CP["host"], self.CP["port"]))
            print("CP 서버에 성공적으로 연결되었습니다.")
            return client_socket
        except (socket.error, socket.timeout) as e:
            print(f"CP 서버에 연결할 수 없습니다: {e}")
            return False

    def cp_connected_btn(self):
        return (
            html.Div(
                [
                    dmc.Menu(
                        [
                            dmc.MenuTarget(
                                dmc.Button(
                                    children=self.CP["tool"],
                                    variant="light",
                                    leftSection=get_icon("bx-wifi"),
                                    rightSection=dmc.SegmentedControl(
                                        id="cp-object-segmented",
                                        value="inst",
                                        color="black",
                                        data=[
                                            {"value": "net", "label": "Net"},
                                            {"value": "inst", "label": "Instance"},
                                        ],
                                        size="xs",
                                        fullWidth=True,
                                    ),
                                    size="xs",
                                    id="cp-btn",
                                )
                            ),
                            dmc.MenuDropdown(
                                [
                                    dmc.MenuLabel(
                                        dmc.Group(
                                            [
                                                dmc.Text("Lib: ", size="xs"),
                                                dmc.Text(self.CP["lib"], c="red", size="xs"),
                                            ],
                                            gap="xs",
                                        )
                                    ),
                                    dmc.MenuLabel(
                                        dmc.Group(
                                            [
                                                dmc.Text("Cell: ", size="xs"),
                                                dmc.Text(self.CP["cell"], c="red", size="xs"),
                                            ],
                                            gap="xs",
                                        )
                                    ),
                                    dmc.Group(
                                        [
                                            dmc.Text("Middle Click", size="lg", fw=700),
                                            dmc.Text(" to CrossProbe", size="md"),
                                        ]
                                    ),
                                ]
                            ),
                        ],
                        trigger="hover",
                    ),
                ]
            )
            if self.CP_socket
            else dmc.Button(
                "Disabled",
                leftSection=get_icon("bx-wifi-off"),
                size="xs",
                disabled=True,
                rightSection=dmc.SegmentedControl(
                    id="cp-object-segmented",
                    value="",
                    color="black",
                    data=[],
                    size="xs",
                    fullWidth=True,
                ),
            )
        )

    def layout(self):
        return dmc.Group(
            [
                dmc.Text(f"CrossProbe: ", fw=500, size="sm", c="gray"),
                self.connected_btn,
            ],
            gap=2,
        )

    def send_message(self, message):
        """
        Usage:
        select -obj inst -hier top1.top2.top3 -name object_names
        pushDesign -top true -hier top1.path1.path2
        selectCurObject -obj net(or inst) -name object_names
        """

        try:
            self.CP_socket.sendall(message.encode())
            logger.debug(f"message: {message}")
            # response = self.CP_socket.recv(4096)
            # return response.decode()
        except socket.timeout:
            logger.warning("Timed out to get response")
            raise
        except Exception as e:
            logger.warning(f"Fail to send message: {e}")
            raise
        # finally:
        #     client_socket.close()

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
            hier_path, name = s.rsplit(delimiter, 1)
        except ValueError:
            hier_path = ""
            name = s
        return hier_path, name

    def remove_m(self, obj, selected_name):
        if obj == "inst" and len(selected_name) > 1 and selected_name[0] == "m":
            selected_name = selected_name[1:]
        return selected_name

    def register_callbacks(self, app):

        # Connecting clientside callback
        app.clientside_callback(
            """
            function(gridId) {
                dash_ag_grid.getApiAsync(gridId).then((grid) => {
                    grid.addEventListener('cellMouseDown', (e) => {
                        if (e.event.button == 1) {
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
            Output("refresh-route", "data", allow_duplicate=True),
            Output("aggrid-table", "selectedRows", allow_duplicate=True),
            Input("aggrid-table", "selectedRows"),
            State("el", "event"),
            State("cp-object-segmented", "value"),
            prevent_initial_call=True,
        )
        def get_selected_row(selected_rows, event, obj):

            if obj and event.get("button") == 1 and len(selected_rows) == 1:
                logger.debug(f"selected_rows: {selected_rows}")
                selected_row = selected_rows[0]
                value = event.get("srcElement.innerText")
                colId = event.get("srcElement.attributes.col-id.nodeValue")
                request = CACHE.get("REQUEST")
                groupBy = [col["id"] for col in request.get("rowGroupCols", [])]

                selected_hier_path, selected_name = self.hier_name(value)
                selected_name = self.remove_m(obj, selected_name)

                # Group CrossProbing
                if groupBy:
                    dff = DATAFRAME["df"]
                    for gc in groupBy:
                        dff = dff.filter(pl.col(gc) == selected_row[gc])

                    names = set([selected_name])
                    for group_value in dff[colId]:
                        group_hier_path, group_hier_name = self.hier_name(group_value)
                        if group_hier_path == selected_hier_path:
                            names.add(self.remove_m(obj, group_hier_name))

                        elif group_hier_path.startswith(selected_hier_path):
                            group_hier_path = group_hier_path.replace(selected_hier_path, "")
                            if len(group_hier_path) and group_hier_path[0] == ".":
                                names.add(self.remove_m(obj, group_hier_path.split(".")[1]))

                    if self.current_view == selected_hier_path:
                        # Single Instance CrossProbing
                        msg = f"selectCurObject -obj {obj} -name {','.join(names)}\n"
                    else:
                        msg = f"select -obj {obj} -hier {selected_hier_path} -name {','.join(names)}\n"
                else:
                    # if save view hierarchy
                    if self.current_view == selected_hier_path:
                        # Single Instance CrossProbing
                        msg = f"selectCurObject -obj {obj} -name {selected_name}\n"
                    else:
                        # Single Instance CrossProbing
                        tmsg = (
                            f"-hier {selected_hier_path} -name {selected_name}"
                            if selected_hier_path
                            else f"-name {selected_name}"
                        )
                        msg = f"select -obj {obj} {tmsg}\n"
                        self.current_view = selected_hier_path

                self.send_message(msg)

                noti = dmc.Notification(
                    title="CrossProbing",
                    id=f"noti-{msg}",
                    color="green",
                    action="show",
                    message=f"CP command: {msg}",
                    icon=html.Img(src="assets/icons/bx-send.png"),
                    style={
                        "position": "fixed",
                        "bottom": 70,
                        "right": 25,
                        "width": 400,
                    },
                )
                return noti, no_update, []

            # elif event["ctrlKey"]:
            #    ...
            # elif selected_rows[0].get("waiver"):
            #    ...

            else:
                raise exceptions.PreventUpdate
