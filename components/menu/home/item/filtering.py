import os
import yaml
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc

from dash import Input, Output, State, exceptions, no_update, dcc, html, ctx
from utils.data_processing import displaying_df
from utils.logging_utils import logger
from utils.config import CONFIG

from dataclasses import dataclass
from typing import Dict, List, Optional
import json
from datetime import datetime

@dataclass
class FilterInfo:
    name: str
    description: str 
    application: str # Signoff Application name
    columns: List[str] # Required columns for this filter
    filter_model: Dict
    created_at: str
    created_by: str


class Filter:
    def __init__(self) -> None:
        #self.filter_yaml = os.path.join(CONFIG.USER_RV_DIR, "filters.yaml")
        self.filter_yaml = "filters.yaml"

    def load_filters(self):
        if os.path.exists(self.filter_yaml):
            with open(self.filter_yaml, "r") as file:
                return yaml.safe_load(file) or {}
        return {}
    
    def save_filters(self, filters):
        with open(self.filter_yaml, "w") as file:
            yaml.dump(filters, file)
            
    def layout(self):
        return dmc.Group(
            [
                dbpc.OverlayToaster(
                    id='filter-toaster',
                    position='top-right',
                ),
                dmc.Text(f"Filters: ", fw=500, size="sm", c="gray"),
                dbpc.Button(
                    icon='filter-keep',
                    id="save-current-filter",
                ),
                dbpc.Button(
                    icon='filter-list',
                    id="open-filter-manager",
                ),
                # 역필터 적용 버튼 추가
                dbpc.Button(
                    icon='swap-horizontal',
                    id="inverse-filter-btn", 
                ),

                self.filter_manager(),

                dcc.Store(id="filter-model-store"),
                dcc.Store(id="selected-filter-store")
                
            ],
            gap=2,
        )

    def filter_manager(self):
        return dbpc.Dialog(
            title="Filter Manager",
            id="filter-manager-modal",
            children=[
                dbpc.DialogBody(
                    children=[
                        # Left Panel: Filter Categories
                        dmc.Grid(
                            [
                            dmc.GridCol([
                                dbpc.ButtonGroup([
                                    dbpc.Button(
                                    "All Filters",
                                    icon="filter-open",
                                    active=True,
                                    ),
                                    dbpc.Button(
                                        "My Filters",
                                        icon="user",
                                        disabled=True,
                                    ),
                                    dbpc.Button(
                                        "Shared Filters",
                                        icon="shared-filter",
                                        disabled=True,
                                    ),
                                ], vertical=True)

                            ], span=3),
                            # Right Panel: Filter List
                            dmc.GridCol(
                                [
                                    dbpc.InputGroup(
                                        id='input-group-3',
                                        leftIcon='search-template',
                                    ),                                
                                    # Filter Cards
                                    self._render_filter_cards(),
                            ], span=9)
                        ])
                    ]
                ),
                dbpc.DialogFooter(
                    actions=[
                        dbpc.Button(
                            id='close-filter-modal',
                            children='Close'
                        )
                    ],
                    children=dbpc.ButtonGroup(
                        [
                            dbpc.Button(
                                "Import",
                                icon="import"
                            ),
                            dbpc.Button(
                                "Export",
                                icon="export"
                            ),
                        ]
                    )
                )
            ],
            icon='filter',
            isCloseButtonShown=True
        )


    def _render_filter_cards(self):
        filters = self.load_filters()
        current_columns = self._get_current_columns()
        cards = []
        for name, filter_data in filters.items():
            filter_info = FilterInfo(**filter_data)
            is_applicable = all(col in current_columns for col in filter_info.columns)
            cards.append(
                dmc.Card(
                    children=[
                        dmc.Group([
                            dmc.Group([
                                dmc.Text(filter_info.name, w=500),
                                dmc.Badge(
                                    filter_info.application,
                                    color="blue", 
                                    variant="light"
                                ),
                                dmc.Badge(
                                    "Compatible" if is_applicable else "Incompatible",
                                    color="green" if is_applicable else "red",
                                    variant="dot"
                                )
                            ]),
                            dbpc.ButtonGroup([
                                dbpc.Button(
                                    icon="edit",
                                    minimal=True,
                                    id={
                                        "type": "edit-filter",
                                        "name": name
                                    }
                                ),
                                dbpc.Button(
                                    icon="trash",
                                    minimal=True, 
                                    intent="danger",
                                    id={
                                        "type": "delete-filter",
                                        "name": name
                                    }
                                )
                            ])
                        ], justify="space-around"),
                        
                        dmc.Text(
                            filter_info.description,
                            c="dimmed",
                            size="sm",
                            mb=10
                        ),
                        
                        dmc.Group([
                            dmc.Text(
                                f"Created by {filter_info.created_by}",
                                size="xs",
                                c="dimmed"
                            ),
                            dmc.Text(
                                f"Created at {filter_info.created_at}",
                                size="xs", 
                                c="dimmed"
                            )
                        ], gap="xs"),
                        
                        dbpc.Button(
                            "Apply Filter",
                            id={
                                "type": "apply-filter",
                                "name": name
                            },
                            disabled=not is_applicable,
                            fill=True,
                        )
                    ],
                    withBorder=True,
                    mb=10,
                    p="sm"
                )
            )
            
        return dmc.Stack(cards, gap="sm")


    def _get_current_columns(self) -> List[str]:
        df = displaying_df()
        return list(df.columns) if df is not None else []
        
    def _get_applications(self) -> List[str]:
        # TODO: Implement getting list of Signoff Applications
        return ["ADV", "DSC", "LSC", "CANA"]
    




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

        app.clientside_callback(
            """
            function(n_clicks, grid_id) {
                if (!n_clicks) return window.dash_clientside.no_update;
                
                const grid = dash_ag_grid.getApi(grid_id);
                if (!grid) {
                    console.error("Grid API not found");
                    return window.dash_clientside.no_update;
                }
                
                // Advanced Filter Model 가져오기
                const filterModel = grid.getAdvancedFilterModel();
                
                if (!filterModel) return window.dash_clientside.no_update;
                
                return JSON.stringify(filterModel); 
            }
            """,
            # Output과 State 추가
            Output("filter-model-store", "data"),
            Input("save-current-filter", "n_clicks"),
            State("aggrid-table", "id"),
            prevent_initial_call=True
        )

        @app.callback(
            Output("filter-manager-modal", "isOpen"),
            Input("open-filter-manager", "n_clicks"),
            prevent_initial_call=True,
        )
        def open_filter_storage(n_clicks):
            if n_clicks is None or n_clicks == 0:
                raise exceptions.PreventUpdate
            return True
