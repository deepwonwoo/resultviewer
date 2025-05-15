import os
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, html, dcc, no_update, exceptions, set_props
from utils.db_management import SSDF
from utils.config import CONFIG
from utils.data_processing import validate_df
from components.grid.dag.column_definitions import generate_column_definitions


class FileReload:

    def layout(self):
        return dmc.Group([dcc.Interval(id="update-interval", interval=10000),dcc.Store("csv-mod-time"),dbpc.Button("Reload",id="file-reload-btn",small=True,icon="data-sync",intent="warning",minimal=True), dbpc.Alert(id="data-reload-alert",children=[f"Do you want Reload the Data? (current changes will disappear)"],cancelButtonText="Cancel",confirmButtonText="Reload",icon="refresh",intent="warning")],justify="flex-start")

    def register_callbacks(self, app):

        @app.callback(Output("file-reload-btn", "minimal"),Input("update-interval", "n_intervals"),State("flex-layout", "model"),State("csv-mod-time", "data"))
        def check_file_update(n, model_layout, stored_mod_time):
            file_path = model_layout["layout"]["children"][0]["children"][0].get("name")            
            if not file_path:
                return no_update
            if file_path.startswith("WORKSPACE"):
                file_path = file_path.replace("WORKSPACE", CONFIG.WORKSPACE)
            if not os.path.exists(file_path):
                return no_update
            current_mod_time = os.path.getmtime(file_path)
            return True if stored_mod_time == current_mod_time else False

        @app.callback(Output("data-reload-alert", "isOpen", allow_duplicate=True),Input("file-reload-btn", "n_clicks"),prevent_initial_call=True)
        def reload_file_alert(n):
            if n is None:
                return no_update
            return True

        @app.callback(Output("aggrid-table", "columnDefs", allow_duplicate=True),Output("csv-mod-time", "data"),Output("data-reload-alert", "isConfirmed"),Input("data-reload-alert", "isConfirmed"),State("flex-layout", "model"),prevent_initial_call=True)
        def reload_file(n, model_layout):
            file_path = model_layout["layout"]["children"][0]["children"][0]["name"]

            if not file_path:
                return no_update, no_update, False

            if file_path.startswith("WORKSPACE"):
                file_path = file_path.replace("WORKSPACE", CONFIG.WORKSPACE)

            if not os.path.exists(file_path):
                return no_update, no_update, False

            SSDF.dataframe = validate_df(file_path)

            current_mod_time = os.path.getmtime(file_path)

            return generate_column_definitions(SSDF.dataframe), current_mod_time, False