import socket
import threading
import dash_blueprint_components as dbpc
from dash import no_update
from utils.logging_utils import logger
from utils.config import CONFIG
from typing import Optional


class ServerClass:

    def __init__(
        self, host="localhost", port=42000, tool_name="customwaveview"
    ) -> None:
        self.host = host
        self.port = port
        self.tool_name = tool_name
        try:
            with open(CONFIG.CP_CFG, "r") as f:
                for l in f:
                    l_lower = l.lower().strip()
                    if "portband" in l_lower:
                        portband_file = l.split()[1]
                        with open(portband_file, "r") as g:
                            for m in g:
                                m_lower = m.lower().strip()
                                if self.tool_name in m_lower:
                                    self.port = int(m.split()[1])
                                else:
                                    continue
        except Exception as e:
            logger.error(f"Error opening config file: {CONFIG.cp_CFG}")

        self.max_port = self.port + 1000  # Max server count
        self.server_socket: Optional[socket.socket] = None
        self.client_socket = None
        self.clients = []
        self.running = False
        self.client_invoked = False
        self.hier = None

    def run(self):
        while self.port < self.max_port:
            try:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.bind((self.host, self.port))
                self.server_socket.listen(5)
                logger.info(
                    f"CrossProbing Server started at {str(self.host)}:{str(self.port)}"
                )
                self.running = True
                break

            except OSError as e:
                if "Address already in use" in str(e):
                    self.port += 1
                else:
                    logger.error(f"Unexpected OSError: {str(e)}")
                    break

        if not self.running:
            logger.error("Fail to retry opening server")

        else:
            self.server_thread = threading.Thread(
                target=self.accept_connections, daemon=True
            ).start()

    def accept_connections(self):
        try:
            while self.running:
                self.client_socket, client_address = self.server_socket.accept()
                logger.info(f"CP Client: {client_address}")
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(self.client_socket, client_address),
                    daemon=True,
                )
                self.clients.append((self.client_socket, client_address))
                client_thread.start()
        except Exception as e:
            logger.error(f"{str(e)} ")

    def handle_client(self, client_socket, client_address):
        try:
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break
                try:
                    self.recv_data = data.decode("utf-8")
                    logger.info(f"Received from client: {self.recv_data}")
                    if "toolinvoked" in str(self.recv_data):
                        self.client_invoked = True
                except Exception as e:
                    logger.error(f"Error receiving data from client: {str(e)}")

        except Exception as e:
            logger.error(f"Error handling client: {str(e)}")

        finally:
            client_socket.close()
            self.clients.remove((client_socket, client_address))
            self.client_invoked = False
            self.stop_server()
            logger.info(f"Connection with {client_address} closed")

    def send_command_to_client(self, cmd):
        if self.client_socket:
            try:
                self.client_socket.send((cmd + "\n").encode("utf-8"))
                return [
                    dbpc.Toast(
                        message=f"CP command: {cmd}",
                        intent="success",
                        icon="send-message",
                        timeout=3000,
                    )
                ]

            except Exception as e:
                logger.error(f"Failed to send CP cmd: {cmd}")
                return [
                    dbpc.Toast(
                        message=f"{str(e)}", intent="danger", icon="error", timeout=3000
                    )
                ]

        else:
            return no_update

    def stop_server(self):
        self.running = False

        for client_socket, _ in self.clients:
            try:
                client_socket.close()
            except:
                pass
        self.client_invoked = False

        if self.server_socket:
            self.server_socket.close()
