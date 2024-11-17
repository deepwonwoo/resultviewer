import os
import yaml
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc

from dash import Input, Output, State, exceptions, no_update, dcc, html
from utils.component_template import get_icon, create_notification
from utils.data_processing import displaying_df
from utils.logging_utils import logger
from utils.config import CONFIG


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
                # 역필터 적용 버튼 추가
                dbpc.Button(
                    icon='swap-horizontal',
                    id="inverse-filter-btn", 
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
                        id="store-filter-condition-btn",
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
                        dmc.Button("Clear Filters", color="blue", variant="outline", id="clear-filters-btn"),
                        dmc.Button("Preview", color="green", variant="outline", id="filter-preview-btn"),
                        dmc.Button("Apply", color="indigo", variant="outline", id="apply-filter-btn"),
                        dmc.Button("Close", color="red", variant="outline", id="close-filter-storage-btn"),
                    ]
                ),
                dmc.Space(h=20),
                dmc.List([], id="filter-history", size="sm"),
            ],
        )


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




    
    def register_callbacks(self, app):


        app.clientside_callback(
        """
        function(n_clicks, grid_id) {
            if (!n_clicks) return window.dash_clientside.no_update;
            
            console.log("n_clicks:", n_clicks);

            var grid = dash_ag_grid.getApi(grid_id);
            if (!grid) {
                console.error("Grid API not found");
                return window.dash_clientside.no_update;
            }
            
            console.log("grid:", grid);

            const filterModel = grid.getAdvancedFilterModel();

            console.log("filterModel:", filterModel);
            
            if (!filterModel) return window.dash_clientside.no_update;
            
            // Advanced Filter Model을 inverse 변환하는 함수
            function inverseFilterModel(model) {
                
                // Join type filter (AND/OR 결합)
                if (model.filterType === 'join') {
                    return {
                        filterType: 'join',
                        // AND <-> OR 변환 (De Morgan's Law)
                        type: model.type === 'AND' ? 'OR' : 'AND',
                        // 재귀적으로 모든 조건에 대해 inverse 적용
                        conditions: model.conditions.map(condition => inverseFilterModel(condition))
                    };
                }
                
                // 기본 구조 복사
                const inversedModel = { ...model };

                // 데이터 타입별 inverse 매핑 처리
                switch (model.filterType) {
                    case 'text':
                    case 'object':
                        // 텍스트/오브젝트 타입 필터 inverse
                        const textInverseMap = {
                            'equals': 'notEqual',
                            'notEqual': 'equals',
                            'contains': 'notContains', 
                            'notContains': 'contains',
                            'startsWith': 'notStartsWith',
                            'notStartsWith': 'startsWith', 
                            'endsWith': 'notEndsWith',
                            'notEndsWith': 'endsWith',
                            'blank': 'notBlank',
                            'notBlank': 'blank'
                        };
                        inversedModel.type = textInverseMap[model.type] || model.type;
                        break;

                    case 'number':
                    case 'date':
                    case 'dateString':
                        // 숫자/날짜 타입 필터 inverse 
                        const scalarInverseMap = {
                            'equals': 'notEqual',
                            'notEqual': 'equals',
                            'lessThan': 'greaterThanOrEqual',
                            'lessThanOrEqual': 'greaterThan', 
                            'greaterThan': 'lessThanOrEqual',
                            'greaterThanOrEqual': 'lessThan',
                            'blank': 'notBlank',
                            'notBlank': 'blank',
                            'inRange': 'notInRange',
                            'notInRange': 'inRange'
                        };
                        inversedModel.type = scalarInverseMap[model.type] || model.type;
                        break;

                    case 'boolean':
                        // 불리언 타입 필터 inverse
                        inversedModel.type = model.type === 'true' ? 'false' : 'true';
                        break;

                    default:
                        console.warn(`Unknown filter type: ${model.filterType}`);
                        return model;
                }

                return inversedModel;
            }

            try {
                console.log('Original Filter Model:', filterModel);
                const inversedModel = inverseFilterModel(filterModel);
                console.log('Inversed Filter Model:', inversedModel);
                
                grid.setAdvancedFilterModel(inversedModel);
                return window.dash_clientside.no_update;
            } catch (error) {
                console.error('Error inverting filter model:', error);
                return window.dash_clientside.no_update;
            }

        }
        """,
        Output("inverse-filter-btn", "children"),
        Input("inverse-filter-btn", "n_clicks"), 
        State("aggrid-table", "id"),
        prevent_initial_call=True
    )







        @app.callback(
            Output("filter-store-modal", "opened"),
            Output("notifications", "children", allow_duplicate=True),
            Input("open-filter-storage-btn", "n_clicks"),
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
            Input("store-filter-condition-btn", "n_clicks"),
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
            Input("clear-filters-btn", "n_clicks"),
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
            Input("filter-preview-btn", "n_clicks"),
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
            Input("apply-filter-btn", "n_clicks"),
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
