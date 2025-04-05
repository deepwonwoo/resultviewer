import socket
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Input, Output, State, no_update
from utils.db_management import SSDF
from utils.logging_utils import logger
from utils.crossprobe_msghandler import MsgHandler


class SchemEditor:

    def __init__(self):
        self.CP = SSDF.cp
        self.CP_socket = self.create_connection() if all(self.CP.values()) else False
        self.msghandler = MsgHandler()

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

    def cp_connected_layout(self):
        return dmc.Group(
            [
                dbpc.Tooltip(
                    [
                        dbpc.Button(
                            icon="link", minimal=True, outlined=True, disabled=True
                        )
                    ],
                    placement="bottom",
                    content="Select Net/Instance and Column, Middle click on a row to CrossProbe",
                    compact=True,
                    minimal=True,
                ),
                dmc.SegmentedControl(
                    id="cp-object-segmented",
                    value="inst",
                    color="indigo.5",
                    data=[
                        {"value": "net", "label": "Net"},
                        {"value": "inst", "label": "Instance"},
                    ],
                    size="xs",
                ),
                dmc.Select(
                    id="cp-column-select",
                    data=[],
                    placeholder="Select column",
                    style={"width": 150},
                    size="xs",
                ),
                dmc.TextInput(
                    id="cp-manual-input",
                    placeholder="manual CrossProbing",
                    rightSection=dbpc.Button(
                        id="cp-manual-button",
                        icon="send-message",
                        small=True,
                        minimal=True,
                    ),
                    style={"width": 200},
                    size="xs",
                ),
            ],
            gap="xs",
        )

    def cp_disconnected_layout(self):
        return dbpc.Tooltip(
            [dbpc.Button(icon="unlink", minimal=True, outlined=True, disabled=True)],
            placement="bottom",
            content="Restart SORV from VSE/BTS to use CrossProbe",
            compact=True,
            minimal=True,
        )

    def layout(self):
        return dbpc.FormGroup(
            children=(
                self.cp_connected_layout()
                if self.CP_socket
                else self.cp_disconnected_layout()
            ),
            label=dmc.Text("Schematic: ", fw=500, size="sm", c="gray"),
            inline=True,
        )

    def send_cp_message(self, message):
        # Usage:
        # select -obj inst -hier top1.top2.top3 -name object_names
        # pushDesign -top true -hier top1.path1.path2
        # selectCurObject -obj net(or inst) -name object_names
        try:
            self.CP_socket.sendall(message.encode())
            logger.info(f"CP message: {message}")
            return [
                dbpc.Toast(
                    message=f"CP command: {message}",
                    intent="success",
                    icon="send-message",
                )
            ]

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return [dbpc.Toast(message=f"{str(e)}", intent="danger", icon="error")]

    def close_connection(self):
        if self.CP_socket:
            try:
                self.CP_socket.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

    def register_callbacks(self, app):

        if self.CP_socket:

            @app.callback(
                Output("cp-column-select", "data"),
                Input("aggrid-table", "columnDefs"),
                prevent_initial_call=True,
            )
            def update_cp_columns(columnDefs):
                return [coldef["field"] for coldef in columnDefs]

            @app.callback(
                Output("toaster", "toasts", allow_duplicate=True),
                Input("cp-manual-button", "n_clicks"),
                State("cp-manual-input", "value"),
                State("cp-object-segmented", "value"),
                prevent_initial_call=True,
            )
            def manual_crossprobing(n, cp_name, obj):
                if n and cp_name:
                    selected_hier_path, selected_name = self.hier_name(cp_name)
                    selected_name = self.remove_init_r_m(obj, selected_name)
                    # selected_name = self.preprocess_d_name(obj, selected_name)
                    cp_command = f"select -obj {obj} -hier {selected_hier_path} -name {selected_name}\n"
                    toasts = self.send_cp_message(cp_command)
                    return toasts
                return no_update

            @app.callback(
                Output("toaster", "toasts", allow_duplicate=True),
                Input("cp_selected_rows", "data"),
                State("el", "event"),
                State("cp-object-segmented", "value"),
                State("cp-column-select", "value"),
                prevent_initial_call=True,
            )
            def get_selected_row(selected_rows, event, obj, cp_col):
                if event.get("button") != 1:
                    logger.info("btn1")
                    return no_update
                elif self.CP_socket:
                    if not cp_col:
                        cp_col = event.get("srcElement.attributes.col-id.nodeValue")
                    msg = self.cross_probing(selected_rows, obj, cp_col)
                    toasts = self.send_cp_message(msg)
                    return toasts
                else:
                    return no_update
