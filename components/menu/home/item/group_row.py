import dash_mantine_components as dmc
from dash import Input, Output, State
from utils.component_template import get_icon


class GroupRow:
    def layout(self):
        return dmc.Group(
            [
                dmc.Text("GroupRows: ", fw=500, size="sm", c="gray"),
                self._create_tooltip("expand-rowGroup", "Expand all groupRows", "unfold"),
                self._create_tooltip("collapse-rowGroup", "Collapse all groupRows", "fold"),
            ],
            gap=2,
        )

    def _create_tooltip(self, id, label, icon):
        return dmc.Tooltip(
            dmc.ActionIcon(get_icon(icon), variant="outline", id=id, n_clicks=0, color="grey"),
            label=label,
            withArrow=True,
            position="bottom",
            color="grey",
        )

    def register_callbacks(self, app):
        for action in ["expand", "collapse"]:
            self._register_clientside_callback(app, action)

    def _register_clientside_callback(self, app, action):
        app.clientside_callback(
            f"""
            function (n_clicks, grid_id) {{
                if (n_clicks > 0) {{
                    var grid = dash_ag_grid.getApi(grid_id);
                    if (grid) {{
                        grid.{action}All();
                    }} else {{
                        console.error("Grid with ID " + grid_id + " not found.");
                    }}
                }}
                return window.dash_clientside.no_update;
            }}
            """,
            Output(f"{action}-rowGroup", "children"),
            Input(f"{action}-rowGroup", "n_clicks"),
            State("aggrid-table", "id"),
            prevent_initial_call=True,
        )
