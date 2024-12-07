import os
import yaml
import dash_mantine_components as dmc
from dash import Input, Output, State, exceptions, no_update, dcc
from utils.data_processing import displaying_df
from utils.logging_utils import logger
from utils.config import CONFIG

# Constants
OPEN_FILTER_STORAGE = "open-filter-storage-btn"
STORE_FILTER_CONDITION = "store-filter-condition-btn"
CLEAR_FILTERS = "clear-filters-btn"
CLOSE_FILTER_STORAGE = "close-filter-storage-btn"
FILTER_PREVIEW = "filter-preview-btn"
APPLY_FILTER = "apply-filter-btn"


class Filter:
    def __init__(self) -> None:
        self.max_filters = 10  # 최대 필터 수 설정 가능
        self.filter_yaml = os.path.join(CONFIG.USER_RV_DIR, "filters.yaml")

    def filter_model_to_expression(self, filter_model):
        """Convert filter model to expression string."""
        operator_map = {
            "contains": "contains",
            "notContains": "does not contain",
            "equals": "=",
            "notEqual": "!=",
            "startsWith": "begins with",
            "endsWith": "ends with",
            "blank": "is blank",
            "notBlank": "is not blank",
            "greaterThan": ">",
            "greaterThanOrEqual": ">=",
            "lessThan": "<",
            "lessThanOrEqual": "<=",
            "true": "is true",
            "false": "is false",
        }

        def build_expression(condition):
            if condition.get("filterType") == "join":
                expressions = [build_expression(c) for c in condition["conditions"]]
                join_type = " AND " if condition["type"] == "AND" else " OR "
                return f"({join_type.join(expressions)})"
            else:
                operator = operator_map.get(condition["type"], condition["type"])
                filter_value = (
                    f'"{condition["filter"]}"' if isinstance(condition["filter"], str) else condition["filter"]
                )
                return f"[{condition['colId']}] {operator} {filter_value}"

        return build_expression(filter_model)

    def layout(self):
        return dmc.Group(
            [
                dmc.Text(f"Filters: ", fw=500, size="sm", c="gray"),
                dmc.Tooltip(
                    dmc.ActionIcon(
                        get_icon("bx-filter-alt"),
                        variant="outline",
                        id="open-filter-storage-btn",
                        n_clicks=0,
                        color="grey",
                    ),
                    label="Open Filter Storage",
                    withArrow=True,
                    position="bottom",
                    color="grey",
                ),
                dcc.Store(id="advancedFilterModel-store"),
                self.store_filter_condition_modal(),
            ],
            gap=2,
        )

    def store_filter_condition_modal(self):
        return dmc.Modal(
            title="Filter Storage",
            id="filter-store-modal",
            zIndex=1000,
            size="lg",
            children=[
                dmc.TextInput(
                    label="Current Filter:",
                    value="",
                    rightSection=dmc.Button(
                        "Store",
                        id=STORE_FILTER_CONDITION,
                        size="xs",
                        variant="outline",
                        color="grey",
                        style={"width": 100},
                    ),
                    disabled=True,
                    rightSectionWidth=100,
                    required=True,
                    id="store-filter-condition-input",
                ),
                dmc.Space(h="sm"),
                dmc.List([], id="saved-filter-models", size="sm"),
                dmc.Space(h=20),
                dmc.Group(
                    [
                        dmc.Button("Clear Filters", color="blue", variant="outline", id=CLEAR_FILTERS),
                        dmc.Button("Preview", color="green", variant="outline", id=FILTER_PREVIEW),
                        dmc.Button("Apply", color="indigo", variant="outline", id=APPLY_FILTER),
                        dmc.Button("Close", color="red", variant="outline", id=CLOSE_FILTER_STORAGE),
                    ]
                ),
                dmc.Space(h=20),
                dmc.List([], id="filter-history", size="sm"),
            ],
        )

    def register_callbacks(self, app):
        @app.callback(
            Output("filter-store-modal", "opened"),
            Output("notifications", "children", allow_duplicate=True),
            Input(OPEN_FILTER_STORAGE, "n_clicks"),
            prevent_initial_call=True,
        )
        def open_filter_storage(n_clicks):
            if n_clicks is None or n_clicks == 0:
                raise exceptions.PreventUpdate
            try:
                self.load_filters()
                return True, None
            except Exception as e:
                logger.error(f"Error opening filter storage: {str(e)}")
                return False, create_notification(f"Error: {str(e)}", "Filter Storage Error", "red")

        @app.callback(
            Output("saved-filter-models", "children"),
            Output("notifications", "children", allow_duplicate=True),
            Input(STORE_FILTER_CONDITION, "n_clicks"),
            State("store-filter-condition-input", "value"),
            State("advancedFilterModel-store", "data"),
            prevent_initial_call=True,
        )
        def store_filter_condition(n_clicks, filter_name, filter_model):
            if n_clicks is None or n_clicks == 0 or not filter_name or not filter_model:
                raise exceptions.PreventUpdate
            try:
                filters = self.load_filters()
                filters[filter_name] = filter_model
                self.save_filters(filters)
                return self.generate_filter_list(filters), create_notification(
                    "Filter saved successfully", "Filter Saved", "green"
                )
            except Exception as e:
                logger.error(f"Error storing filter condition: {str(e)}")
                return no_update, create_notification(f"Error: {str(e)}", "Filter Storage Error", "red")

        @app.callback(
            Output("advancedFilterModel-store", "data", allow_duplicate=True),
            Output("notifications", "children", allow_duplicate=True),
            Input(CLEAR_FILTERS, "n_clicks"),
            prevent_initial_call=True,
        )
        def clear_filters(n_clicks):
            if n_clicks is None or n_clicks == 0:
                raise exceptions.PreventUpdate
            try:
                return None, create_notification("Filters cleared", "Filters Cleared", "blue")
            except Exception as e:
                logger.error(f"Error clearing filters: {str(e)}")
                return no_update, create_notification(f"Error: {str(e)}", "Clear Filters Error", "red")

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Input(FILTER_PREVIEW, "n_clicks"),
            State("advancedFilterModel-store", "data"),
            prevent_initial_call=True,
        )
        def preview_filter(n_clicks, filter_model):
            if n_clicks is None or n_clicks == 0 or not filter_model:
                raise exceptions.PreventUpdate
            try:
                df = displaying_df()
                if df is None:
                    return create_notification("No data loaded", "Preview Error", "red")
                filter_expr = self.filter_model_to_expression(filter_model)
                filtered_df = df.filter(filter_expr)
                return create_notification(f"Filter would return {len(filtered_df)} rows", "Filter Preview", "blue")
            except Exception as e:
                logger.error(f"Error previewing filter: {str(e)}")
                return create_notification(f"Error: {str(e)}", "Preview Error", "red")

        @app.callback(
            Output("aggrid-table", "filterModel", allow_duplicate=True),
            Output("filter-history", "children"),
            Output("notifications", "children", allow_duplicate=True),
            Input(APPLY_FILTER, "n_clicks"),
            State("advancedFilterModel-store", "data"),
            State("filter-history", "children"),
            prevent_initial_call=True,
        )
        def apply_filter(n_clicks, filter_model, current_history):
            if n_clicks is None or n_clicks == 0 or not filter_model:
                raise exceptions.PreventUpdate
            try:
                filter_expr = self.filter_model_to_expression(filter_model)
                new_history = current_history + [dmc.ListItem(filter_expr)]
                if len(new_history) > 5:  # Keep only last 5 filters in history
                    new_history = new_history[-5:]
                return (
                    filter_model,
                    new_history,
                    create_notification("Filter applied successfully", "Filter Applied", "green"),
                )
            except Exception as e:
                logger.error(f"Error applying filter: {str(e)}")
                return (no_update, no_update, create_notification(f"Error: {str(e)}", "Apply Filter Error", "red"))

    def load_filters(self):
        if os.path.exists(self.filter_yaml):
            with open(self.filter_yaml, "r") as file:
                return yaml.safe_load(file) or {}
        return {}

    def save_filters(self, filters):
        with open(self.filter_yaml, "w") as file:
            yaml.dump(filters, file)

    def generate_filter_list(self, filters):
        return [dmc.ListItem(name) for name in filters.keys()]
