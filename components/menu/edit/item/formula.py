import re
import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, html, no_update, exceptions, ctx, ALL, MATCH
from typing import Dict, List, Any, Optional, Union
import uuid

from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions
from components.menu.edit.common_utils import handle_tab_button_click, FormComponents


class Formula:
    def __init__(self):
        self.form = FormComponents()
        
        # Simple formula operations with improved text operations
        self.operations = {
            "arithmetic": {
                "name": "Arithmetic",
                "operations": [
                    {"value": "add", "label": "Add (+)", "inputs": 2},
                    {"value": "subtract", "label": "Subtract (-)", "inputs": 2},
                    {"value": "multiply", "label": "Multiply (*)", "inputs": 2},
                    {"value": "divide", "label": "Divide (/)", "inputs": 2},
                    {"value": "power", "label": "Power (^)", "inputs": 2},
                    {"value": "modulo", "label": "Modulo (%)", "inputs": 2},
                    {"value": "sqrt", "label": "Square Root", "inputs": 1},
                    {"value": "abs", "label": "Absolute Value", "inputs": 1},
                ]
            },
            "statistical": {
                "name": "Statistical",
                "operations": [
                    {"value": "mean", "label": "Mean", "inputs": "multiple"},
                    {"value": "sum", "label": "Sum", "inputs": "multiple"},
                    {"value": "min", "label": "Minimum", "inputs": "multiple"},
                    {"value": "max", "label": "Maximum", "inputs": "multiple"},
                    {"value": "std", "label": "Standard Deviation", "inputs": "multiple"},
                    {"value": "median", "label": "Median", "inputs": "multiple"},
                ]
            },
            "conditional": {
                "name": "Conditional",
                "operations": [
                    {"value": "if_then_else", "label": "If-Then-Else", "inputs": "custom"},
                ]
            },
            "transform": {
                "name": "Transform",
                "operations": [
                    {"value": "round", "label": "Round", "inputs": 1, "params": ["decimals"]},
                    {"value": "ceil", "label": "Ceiling", "inputs": 1},
                    {"value": "floor", "label": "Floor", "inputs": 1},
                    {"value": "log", "label": "Logarithm", "inputs": 1},
                    {"value": "exp", "label": "Exponential", "inputs": 1},
                ]
            },
            "text": {
                "name": "Text",
                "operations": [
                    {"value": "concat", "label": "Concatenate", "inputs": "multiple"},
                    {"value": "substring", "label": "Substring", "inputs": 1, "params": ["start", "length"]},
                    {"value": "replace", "label": "Replace", "inputs": 1, "params": ["find", "replace"]},
                    {"value": "upper", "label": "Upper Case", "inputs": 1},
                    {"value": "lower", "label": "Lower Case", "inputs": 1},
                    {"value": "trim", "label": "Trim", "inputs": 1},
                    {"value": "length", "label": "Length", "inputs": 1},
                    {"value": "count_char", "label": "Count Character", "inputs": 1, "params": ["char_to_count"]},
                    {"value": "count_substring", "label": "Count Substring", "inputs": 1, "params": ["substring_to_count"]},
                    {"value": "count_regex", "label": "Count Regex Pattern", "inputs": 1, "params": ["regex_pattern"]},
                ]
            }
        }
        
        # Condition operators
        self.condition_operators = [
            {"value": "==", "label": "Equal to (==)"},
            {"value": "!=", "label": "Not equal to (!=)"},
            {"value": ">", "label": "Greater than (>)"},
            {"value": "<", "label": "Less than (<)"},
            {"value": ">=", "label": "Greater or equal (>=)"},
            {"value": "<=", "label": "Less or equal (<=)"},
            {"value": "contains", "label": "Contains (text)"},
            {"value": "starts_with", "label": "Starts with (text)"},
            {"value": "ends_with", "label": "Ends with (text)"},
            {"value": "is_null", "label": "Is NULL"},
            {"value": "is_not_null", "label": "Is not NULL"},
        ]



    def button_layout(self):
        return dbpc.Button("Formula", id="formula-btn", icon="function", minimal=True, outlined=True)


    def tab_layout(self):
        return dmc.Stack(
            [
                self.form.create_section_card(
                    title="Formula Builder",
                    icon="function",
                    description="Create formulas for data analysis and transformation",
                    children=[
                        # Result column name
                        dmc.TextInput(
                            id="formula-column-name",
                            label="New Column Name",
                            description="Name for the calculated column",
                            placeholder="e.g., calculated_value",
                            required=True,
                            leftSection=dbpc.Icon(icon="new-text-box"),
                        ),
                        dmc.Space(h=20),
                        
                        # Formula builder tabs
                        dmc.Tabs(
                            id="formula-builder-tabs",
                            value="simple",
                            children=[
                                dmc.TabsList([
                                    dmc.TabsTab("Simple Formula", value="simple"),
                                    dmc.TabsTab("Complex Logic", value="complex"),
                                ]),
                                
                                # Simple formula tab
                                dmc.TabsPanel(
                                    value="simple",
                                    children=[
                                        dmc.Space(h=15),
                                        dmc.Select(
                                            id="formula-category",
                                            label="Operation Category",
                                            description="Select the type of operation",
                                            data=[{"value": k, "label": v["name"]} for k, v in self.operations.items()],
                                            clearable=False,
                                        ),
                                        dmc.Space(h=15),
                                        dmc.Select(
                                            id="formula-operation",
                                            label="Operation",
                                            description="Select specific operation",
                                            data=[],
                                            clearable=False,
                                        ),
                                        dmc.Space(h=15),
                                        html.Div(id="simple-formula-inputs"),
                                    ],
                                ),
                                
                                # Complex logic tab
                                dmc.TabsPanel(
                                    value="complex",
                                    children=[
                                        dmc.Space(h=15),
                                        dmc.Alert(
                                            "Build complex conditional logic with multiple conditions",
                                            title="Complex Logic Builder",
                                            color="blue",
                                            variant="light"
                                        ),
                                        dmc.Space(h=15),
                                        
                                        # Conditions container
                                        html.Div(id="complex-conditions-container", children=[]),
                                        
                                        dmc.Space(h=15),
                                        dmc.Button(
                                            "Add Condition Group",
                                            id="add-condition-group-btn",
                                            leftSection=dbpc.Icon(icon="add"),
                                            variant="outline",
                                            size="sm",
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                
                # Action buttons
                dmc.Group([
                    self.form.create_action_button(
                        id="formula-apply-btn",
                        label="Apply Formula",
                        icon="tick"
                    )
                ], justify="center"),
                
                # Help section with count examples
                self.form.create_help_section([
                    "Enter a name for the new calculated column",
                    "Choose formula type: Simple or Complex",
                    "For Simple: Select category and operation, then fill inputs",
                    "For Complex: Build if-then-else logic with multiple conditions",
                    "Use complex logic for conditions like: if column.ends_with('.xmn') and (drain_v - bulk_v) >= 0.95 then 'O' else 'X'",
                    "Click Apply to create the new column",
                ])
            ],
            gap="md",
        )

    def create_condition_group(self, group_id: str = None) -> html.Div:
        """Create a condition group component"""
        if not group_id:
            group_id = str(uuid.uuid4())
            
        return dmc.Card(
            id={"type": "condition-group", "index": group_id},
            withBorder=True,
            shadow="sm",
            radius="md",
            mb="md",
            children=[
                dmc.Group([
                    dmc.Text(f"Condition Group", w=500),
                    dmc.ActionIcon(
                        dbpc.Icon(icon="trash"),
                        id={"type": "remove-condition-group", "index": group_id},
                        color="red",
                        variant="subtle",
                        size="sm",
                    )
                ], justify="apart", mb="md"),
                
                # Conditions
                html.Div(
                    id={"type": "conditions-list", "index": group_id},
                    children=[self.create_condition_row(group_id, str(uuid.uuid4()))]
                ),
                
                dmc.Space(h=10),
                
                # Add condition button
                dmc.Button(
                    "Add Condition",
                    id={"type": "add-condition", "index": group_id},
                    leftSection=dbpc.Icon(icon="add"),
                    variant="subtle",
                    size="xs",
                    mb="md",
                ),
                
                # Logic operator
                dmc.RadioGroup(
                    id={"type": "logic-operator", "index": group_id},
                    label="Combine conditions with:",
                    value="AND",
                    children=[
                        dmc.Radio("AND", value="AND"),
                        dmc.Radio("OR", value="OR"),
                    ],
                    mb="md",
                ),
                
                # Result values
                dmc.Grid([
                    dmc.GridCol([
                        dmc.TextInput(
                            id={"type": "then-value", "index": group_id},
                            label="Then (True) Value",
                            description="Value when condition is true",
                            placeholder="e.g., 'O', 1, column_name",
                        )
                    ], span=6),
                    dmc.GridCol([
                        dmc.TextInput(
                            id={"type": "else-value", "index": group_id},
                            label="Else (False) Value",
                            description="Value when condition is false",
                            placeholder="e.g., 'X', 0, column_name",
                        )
                    ], span=6),
                ]),
            ]
        )

        
    def create_condition_row(self, group_id: str, condition_id: str) -> html.Div:
        """Create a single condition row"""
        
        col_list = [{"value": col, "label": col} for col in SSDF.dataframe.columns if col not in ["uniqid", "group", "childCount"]]

        return html.Div(
            id={"type": "condition-row", "group": group_id, "index": condition_id},
            children=[
                dmc.Grid([
                    dmc.GridCol([
                        dmc.Select(
                            id={"type": "condition-column", "group": group_id, "index": condition_id},
                            label="Column",
                            placeholder="Select column",
                            data=col_list,
                            searchable=True,
                        )
                    ], span=3),
                    
                    dmc.GridCol([
                        dmc.Select(
                            id={"type": "condition-operator", "group": group_id, "index": condition_id},
                            label="Operator",
                            placeholder="Select operator",
                            data=self.condition_operators,
                        )
                    ], span=3),
                    
                    dmc.GridCol([
                        dmc.TextInput(
                            id={"type": "condition-value", "group": group_id, "index": condition_id},
                            label="Value",
                            placeholder="Enter value or column name",
                        )
                    ], span=5),
                    
                    dmc.GridCol([
                        dmc.ActionIcon(
                            dbpc.Icon(icon="trash"),
                            id={"type": "remove-condition", "group": group_id, "index": condition_id},
                            color="red",
                            variant="subtle",
                            size="sm",
                            mt=25,
                        )
                    ], span=1),
                ]),
                dmc.Space(h=10),
            ]
        )



    def register_callbacks(self, app):
        """Register callbacks"""
        
        @app.callback(
            Output("flex-layout", "model", allow_duplicate=True),
            Output("toaster", "toasts", allow_duplicate=True),
            Input("formula-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True,
        )
        def handle_formula_button_click(n_clicks, current_model):
            return handle_tab_button_click(n_clicks, current_model, "formula-tab", "Formula")

        @app.callback(
            Output("formula-operation", "data"),
            Input("formula-category", "value"),
            prevent_initial_call=True,
        )
        def update_operations(category):
            if not category:
                return []
            
            operations = self.operations.get(category, {}).get("operations", [])
            return [{"value": op["value"], "label": op["label"]} for op in operations]

        @app.callback(
            Output("simple-formula-inputs", "children"),
            [Input("formula-category", "value"), Input("formula-operation", "value")],
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True,
        )
        def update_simple_inputs(category, operation, columnDefs):
            if not category or not operation or not columnDefs:
                return []
            
            # Get column list
            columns = [{"value": col["field"], "label": col["field"]} 
                      for col in columnDefs 
                      if col["field"] not in ["uniqid", "group", "childCount"]]
            
            # Find operation details
            op_details = None
            for op in self.operations.get(category, {}).get("operations", []):
                if op["value"] == operation:
                    op_details = op
                    break
            
            if not op_details:
                return []
            
            inputs = []
            
            # Handle different input types
            if op_details["inputs"] == "multiple":
                inputs.append(
                    dmc.MultiSelect(
                        id="formula-input-columns",
                        label="Select Columns",
                        description="Choose columns for the operation",
                        data=columns,
                        searchable=True,
                        required=True,
                    )
                )
            elif op_details["inputs"] == "custom":
                # For if-then-else
                inputs.extend([
                    dmc.Select(
                        id="formula-input-column",
                        label="Column",
                        description="Column to check",
                        data=columns,
                        searchable=True,
                        required=True,
                    ),
                    dmc.Select(
                        id="formula-condition-operator",
                        label="Condition",
                        description="Condition to check",
                        data=self.condition_operators,
                        required=True,
                    ),
                    dmc.TextInput(
                        id="formula-condition-value",
                        label="Compare Value",
                        description="Value to compare against",
                        required=True,
                    ),
                    dmc.TextInput(
                        id="formula-then-value",
                        label="Then Value",
                        description="Value if condition is true",
                        required=True,
                    ),
                    dmc.TextInput(
                        id="formula-else-value",
                        label="Else Value",
                        description="Value if condition is false",
                        required=True,
                    ),
                ])
            else:
                # Numeric inputs (1 or 2)
                for i in range(op_details["inputs"]):
                    inputs.append(
                        dmc.TextInput(
                            id=f"formula-input-{i}",
                            label=f"Input {i+1}",
                            description=f"Enter value or column name (e.g., 5, 3.14, column_name)",
                            placeholder="Value or column name",
                            required=True,
                        )
                    )
                # Additional parameters for count operations
                if "params" in op_details:
                    for param in op_details["params"]:
                        if param == "decimals":
                            inputs.append(
                                dmc.NumberInput(
                                    id=f"formula-param-{param}",
                                    label="Decimal Places",
                                    value=2,
                                    min=0,
                                    max=10,
                                )
                            )
                        elif param == "char_to_count":
                            inputs.append(
                                dmc.TextInput(
                                    id=f"formula-param-{param}",
                                    label="Character to Count",
                                    description="Enter character to count with regx char (e.g., '\\.', '\\-')",
                                    placeholder=".",
                                    required=True,
                                )
                            )
                        elif param == "substring_to_count":
                            inputs.append(
                                dmc.TextInput(
                                    id=f"formula-param-{param}",
                                    label="Substring to Count",
                                    description="Enter substring to count (e.g., 'abc', '.xm')",
                                    placeholder="abc",
                                    required=True,
                                )
                            )
                        elif param == "regex_pattern":
                            inputs.append(
                                dmc.TextInput(
                                    id=f"formula-param-{param}",
                                    label="Regex Pattern",
                                    description="Enter regex pattern (e.g., '\\d+' for digits, '[A-Z]+' for uppercase)",
                                    placeholder="\\d+",
                                    required=True,
                                )
                            )
                        else:
                            inputs.append(
                                dmc.TextInput(
                                    id=f"formula-param-{param}",
                                    label=param.replace("_", " ").title(),
                                    required=True,
                                )
                            )
            
            return inputs



        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("formula-column-name", "value"),
            Input("formula-apply-btn", "n_clicks"),
            [
                State("formula-column-name", "value"),
                State("formula-builder-tabs", "value"),
                State("formula-category", "value"),
                State("formula-operation", "value"),
                State("simple-formula-inputs", "children"),
                State("complex-conditions-container", "children"),
            ],
            prevent_initial_call=True,
        )
        def apply_formula(n_clicks, column_name, tab_type, category, operation, 
                         simple_inputs, complex_conditions):
            if not n_clicks or not column_name:
                raise exceptions.PreventUpdate
            
            print(f"column_name: {column_name}")
            print(f"tab_type: {tab_type}")
            print(f"category: {category}")
            print(f"operation: {operation}")
            print(f"simple_inputs: {simple_inputs}")
            print(f"complex_conditions: {complex_conditions}")


            try:
                df = SSDF.dataframe
                
                if column_name in df.columns:
                    return (
                        [dbpc.Toast(
                            message=f"Column '{column_name}' already exists",
                            intent="warning",
                            icon="warning-sign"
                        )],
                        no_update,
                        no_update,
                    )
                
                if tab_type == "simple":
                    # Extract values from simple_inputs
                    input_values = self._extract_input_values(simple_inputs)
                    
                    # Apply simple formula
                    expr = self._build_simple_expression(
                        category, operation, input_values, df
                    )
                    
                elif tab_type == "complex":
                    # Apply complex logic
                    expr = self._build_complex_expression(
                        complex_conditions, df
                    )
                
                else:
                    return (
                        [dbpc.Toast(
                            message="Invalid formula type",
                            intent="danger",
                            icon="error"
                        )],
                        no_update,
                        no_update,
                    )
                
                # Apply expression
                SSDF.dataframe = df.with_columns(expr.alias(column_name))
                
                # Update column definitions
                updated_columnDefs = generate_column_definitions(SSDF.dataframe)
                
                return (
                    [dbpc.Toast(
                        message=f"Successfully created column '{column_name}'",
                        intent="success",
                        icon="endorsed",
                        timeout=3000,
                    )],
                    updated_columnDefs,
                    "",  # Clear column name
                )
                
            except Exception as e:
                logger.error(f"Formula application error: {str(e)}")
                return (
                    [dbpc.Toast(
                        message=f"Error: {str(e)}",
                        intent="danger",
                        icon="error"
                    )],
                    no_update,
                    no_update,
                )


        @app.callback(
            Output("complex-conditions-container", "children"),
            Input("add-condition-group-btn", "n_clicks"),
            State("complex-conditions-container", "children"),
            prevent_initial_call=True,
        )
        def add_condition_group(n_clicks, current_children):
            if not n_clicks:
                return current_children or []
            
            new_group = self.create_condition_group()
            return (current_children or []) + [new_group]


        @app.callback(
            Output({"type": "conditions-list", "index": MATCH}, "children", allow_duplicate=True),
            Input({"type": "add-condition", "index": MATCH}, "n_clicks"),
            State({"type": "conditions-list", "index": MATCH}, "children"),
            State({"type": "add-condition", "index": MATCH}, "id"),
            prevent_initial_call=True,
        )
        def add_condition(n_clicks, current_conditions, button_id):
            if not n_clicks:
                return current_conditions or []
            
            group_id = button_id["index"]
            new_condition = self.create_condition_row(group_id, str(uuid.uuid4()))
            return (current_conditions or []) + [new_condition]

        # @app.callback(
        #     Output({"type": "condition-column", "group": ALL, "index": ALL}, "data"),
        #     Input("formula-builder-tabs", "value"),
        #     State("aggrid-table", "columnDefs"),
        #     prevent_initial_call=True,
        # )
        # def update_column_dropdowns(tab, columnDefs):
        #     if not columnDefs or tab != "complex":
        #         return []
            
        #     columns = [{"value": col["field"], "label": col["field"]} 
        #               for col in columnDefs 
        #               if col["field"] not in ["uniqid", "group", "childCount"]]
            
        #     # 현재 존재하는 모든 condition-column 드롭다운에 대해 동일한 데이터 반환
        #     outputs = ctx.outputs_list
        #     if outputs:
        #         return [columns] * len(outputs)
        #     return []


        @app.callback(
            Output({"type": "conditions-list", "index": ALL}, "children", allow_duplicate=True),
            Input({"type": "remove-condition", "group": ALL, "index": ALL}, "n_clicks"),
            State({"type": "conditions-list", "index": ALL}, "children"),
            State({"type": "conditions-list", "index": ALL}, "id"),
            prevent_initial_call=True,
        )
        def remove_condition(n_clicks_list, all_conditions_lists, all_list_ids):
            if not any(n_clicks_list):
                return all_conditions_lists
            
            # 클릭된 버튼 찾기
            triggered = ctx.triggered_id
            if not triggered:
                return all_conditions_lists
            
            # 삭제할 condition의 정보
            condition_id = triggered["index"]
            group_id = triggered["group"]
            
            # 모든 conditions list를 순회하면서 해당하는 것만 수정
            updated_lists = []
            for i, (conditions_list, list_id) in enumerate(zip(all_conditions_lists, all_list_ids)):
                if list_id["index"] == group_id:
                    # 해당 그룹에서 condition 삭제
                    filtered_conditions = []
                    for child in conditions_list:
                        if isinstance(child, dict) and "props" in child:
                            child_id = child["props"].get("id", {})
                            if isinstance(child_id, dict) and child_id.get("index") != condition_id:
                                filtered_conditions.append(child)
                        else:
                            filtered_conditions.append(child)
                    updated_lists.append(filtered_conditions)
                else:
                    # 다른 그룹은 그대로 유지
                    updated_lists.append(conditions_list)
            
            return updated_lists


        # Callback to remove condition groups
        @app.callback(
            Output("complex-conditions-container", "children", allow_duplicate=True),
            Input({"type": "remove-condition-group", "index": ALL}, "n_clicks"),
            State("complex-conditions-container", "children"),
            prevent_initial_call=True,
        )
        def remove_condition_group(n_clicks_list, current_children):
            if not any(n_clicks_list) or not current_children:
                return current_children
            
            # Find which button was clicked
            triggered_id = ctx.triggered_id
            if not triggered_id:
                return current_children
            
            # Remove the corresponding group
            group_id = triggered_id["index"]
            return [child for child in current_children 
                   if not (isinstance(child, dict) and 
                          "props" in child and 
                          "id" in child["props"] and 
                          child["props"]["id"].get("index") == group_id)]



    def _extract_input_values(self, inputs_container: List) -> Dict:
        """Extract values from input components"""
        values = {}
        
        if not inputs_container:
            return values
        
        for component in inputs_container:
            if isinstance(component, dict) and "props" in component:
                props = component["props"]
                if "id" in props and "value" in props:
                    values[props["id"]] = props["value"]
        
        return values

    def _build_simple_expression(self, category: str, operation: str, 
                                input_values: Dict, df: pl.DataFrame) -> pl.Expr:
        """Build expression for simple formula"""
        
        # Build expression based on category and operation
        if category == "arithmetic":
            return self._build_arithmetic_expr(operation, input_values, df)
        elif category == "statistical":
            return self._build_statistical_expr(operation, input_values, df)
        elif category == "conditional":
            return self._build_conditional_expr(operation, input_values, df)
        elif category == "transform":
            return self._build_transform_expr(operation, input_values, df)
        elif category == "text":
            return self._build_text_expr(operation, input_values, df)
        else:
            raise ValueError(f"Unknown category: {category}")

    def _build_arithmetic_expr(self, operation: str, inputs: Dict, df: pl.DataFrame) -> pl.Expr:
        """Build arithmetic expression"""
        # Get input values
        val1 = self._parse_input(inputs.get("formula-input-0"), df)
        val2 = self._parse_input(inputs.get("formula-input-1"), df) if "formula-input-1" in inputs else None
        
        if operation == "add":
            return val1 + val2
        elif operation == "subtract":
            return val1 - val2
        elif operation == "multiply":
            return val1 * val2
        elif operation == "divide":
            return pl.when(val2 != 0).then(val1 / val2).otherwise(None)
        elif operation == "power":
            return val1.pow(val2)
        elif operation == "modulo":
            return val1 % val2
        elif operation == "sqrt":
            return val1.sqrt()
        elif operation == "abs":
            return val1.abs()
        else:
            raise ValueError(f"Unknown arithmetic operation: {operation}")

    def _build_statistical_expr(self, operation: str, inputs: Dict, df: pl.DataFrame) -> pl.Expr:
        """Build statistical expression"""
        columns = inputs.get("formula-input-columns", [])
        if not columns:
            raise ValueError("No columns selected for statistical operation")
        
        col_exprs = [pl.col(c) for c in columns]
        
        if operation == "mean":
            return pl.mean_horizontal(col_exprs)
        elif operation == "sum":
            return pl.sum_horizontal(col_exprs)
        elif operation == "min":
            return pl.min_horizontal(col_exprs)
        elif operation == "max":
            return pl.max_horizontal(col_exprs)
        elif operation == "median":
            # Median requires special handling
            return pl.concat_list(col_exprs).list.eval(pl.element().median()).list.first()
        elif operation == "std":
            # Standard deviation requires special handling
            return pl.concat_list(col_exprs).list.eval(pl.element().std()).list.first()
        else:
            raise ValueError(f"Unknown statistical operation: {operation}")

    def _build_conditional_expr(self, operation: str, inputs: Dict, df: pl.DataFrame) -> pl.Expr:
        """Build conditional expression"""
        if operation == "if_then_else":
            column = inputs.get("formula-input-column")
            operator = inputs.get("formula-condition-operator")
            value = inputs.get("formula-condition-value")
            then_val = inputs.get("formula-then-value")
            else_val = inputs.get("formula-else-value")
            
            if not all([column, operator, then_val, else_val]):
                raise ValueError("Missing required inputs for conditional operation")
            
            # Build condition
            condition = self._build_condition(column, operator, value, df)
            
            # Parse then/else values
            then_expr = self._parse_input(then_val, df)
            else_expr = self._parse_input(else_val, df)
            
            return pl.when(condition).then(then_expr).otherwise(else_expr)
        else:
            raise ValueError(f"Unknown conditional operation: {operation}")

    def _build_transform_expr(self, operation: str, inputs: Dict, df: pl.DataFrame) -> pl.Expr:
        """Build transform expression"""
        val = self._parse_input(inputs.get("formula-input-0"), df)
        
        if operation == "round":
            decimals = inputs.get("formula-param-decimals", 0)
            return val.round(decimals)
        elif operation == "ceil":
            return val.ceil()
        elif operation == "floor":
            return val.floor()
        elif operation == "log":
            return val.log()
        elif operation == "exp":
            return val.exp()
        else:
            raise ValueError(f"Unknown transform operation: {operation}")

    def _build_text_expr(self, operation: str, inputs: Dict, df: pl.DataFrame) -> pl.Expr:
        """Build text expression with enhanced count operations"""
        if operation == "concat":
            columns = inputs.get("formula-input-columns", [])
            if not columns:
                raise ValueError("No columns selected for concatenation")
            
            # Concatenate with space as separator
            expr = pl.col(columns[0]).cast(pl.Utf8)
            for col in columns[1:]:
                expr = expr + pl.lit(" ") + pl.col(col).cast(pl.Utf8)
            return expr
        
        # Count operations
        elif operation == "count_char":
            col = inputs.get("formula-input-0")
            char_to_count = inputs.get("formula-param-char_to_count")
            
            if not col or not char_to_count:
                raise ValueError("Column and character to count are required")
            
            # Count specific character using string operations
            return (
                pl.col(col).cast(pl.Utf8)
                .str.len_chars() - 
                pl.col(col).cast(pl.Utf8).str.replace_all(char_to_count, "").str.len_chars()
            )
        
        elif operation == "count_substring":
            col = inputs.get("formula-input-0")
            substring = inputs.get("formula-param-substring_to_count")
            
            if not col or not substring:
                raise ValueError("Column and substring to count are required")
            
            # Count substring occurrences
            return pl.col(col).cast(pl.Utf8).str.count_matches(re.escape(substring))
        
        elif operation == "count_regex":
            col = inputs.get("formula-input-0")
            pattern = inputs.get("formula-param-regex_pattern")
            
            if not col or not pattern:
                raise ValueError("Column and regex pattern are required")
            
            try:
                # Validate regex pattern
                re.compile(pattern)
                return pl.col(col).cast(pl.Utf8).str.count_matches(pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")

        else:
            val = self._parse_input(inputs.get("formula-input-0"), df)
            
            if operation == "substring":
                start = int(inputs.get("formula-param-start", 0))
                length = int(inputs.get("formula-param-length", 1))
                return val.str.slice(start, length)
            elif operation == "replace":
                find = inputs.get("formula-param-find", "")
                replace = inputs.get("formula-param-replace", "")
                return val.str.replace_all(find, replace)
            elif operation == "upper":
                return val.str.to_uppercase()
            elif operation == "lower":
                return val.str.to_lowercase()
            elif operation == "trim":
                return val.str.strip_chars()
            elif operation == "length":
                return val.str.len_chars()
            else:
                raise ValueError(f"Unknown text operation: {operation}")



    def _build_complex_expression(self, conditions_container: List, df: pl.DataFrame) -> pl.Expr:
        """Build complex conditional expression - 개선된 버전"""
        if not conditions_container:
            raise ValueError("No conditions defined")
        
        
        print(f"conditions_container: {conditions_container}")


        # Start with a default value
        result_expr = pl.lit(None)
        
        # Process each condition group in reverse order (to handle if-then-else chain)
        for group in reversed(conditions_container):
            if not isinstance(group, dict) or "props" not in group:
                continue
                
            group_props = group["props"]
            group_id = group_props.get("id", {}).get("index")
            
            # Extract group data
            group_data = self._extract_group_data(group_props.get("children", []))
            
            if not group_data["conditions"]:
                continue
                
            # Build conditions for this group
            group_conditions = []
            for condition_data in group_data["conditions"]:
                if all(k in condition_data for k in ["column", "operator"]):
                    condition = self._build_condition(
                        condition_data["column"],
                        condition_data["operator"],
                        condition_data.get("value"),
                        df
                    )
                    group_conditions.append(condition)
            
            if not group_conditions:
                continue
                
            # Combine conditions based on logic operator
            if group_data["logic_operator"] == "AND":
                combined_condition = group_conditions[0]
                for cond in group_conditions[1:]:
                    combined_condition = combined_condition & cond
            else:  # OR
                combined_condition = group_conditions[0]
                for cond in group_conditions[1:]:
                    combined_condition = combined_condition | cond
            
            # Parse then/else values
            then_expr = self._parse_input(group_data["then_value"], df) if group_data["then_value"] else pl.lit(None)
            else_expr = self._parse_input(group_data["else_value"], df) if group_data["else_value"] else result_expr
            
            # Build if-then-else chain
            result_expr = pl.when(combined_condition).then(then_expr).otherwise(else_expr)
        
        return result_expr

    def _extract_group_data(self, children: List) -> Dict:
        """Extract data from condition group children - 개선된 버전"""
        data = {
            "conditions": [],
            "logic_operator": "AND",
            "then_value": None,
            "else_value": None
        }
        
        for child in children:
            if not isinstance(child, dict) or "props" not in child:
                continue
                
            child_props = child.get("props", {})
            child_id = child_props.get("id", {})
            
            # Conditions list container
            if isinstance(child_id, dict) and child_id.get("type") == "conditions-list":
                conditions_children = child_props.get("children", [])
                for condition_child in conditions_children:
                    condition_data = self._extract_condition_data(condition_child)
                    if condition_data:
                        data["conditions"].append(condition_data)
            
            # Process other components
            elif "children" in child_props:
                for grandchild in child_props.get("children", []):
                    if not isinstance(grandchild, dict) or "props" not in grandchild:
                        continue
                        
                    gc_props = grandchild.get("props", {})
                    gc_id = gc_props.get("id", {})
                    
                    if isinstance(gc_id, dict):
                        id_type = gc_id.get("type")
                        if id_type == "logic-operator" and "value" in gc_props:
                            data["logic_operator"] = gc_props["value"]
                        elif id_type == "then-value" and "value" in gc_props:
                            data["then_value"] = gc_props["value"]
                        elif id_type == "else-value" and "value" in gc_props:
                            data["else_value"] = gc_props["value"]
        
        return data


    def _extract_condition_data(self, condition_row: Dict) -> Optional[Dict]:
        """Extract data from a single condition row - 개선된 버전"""
        if not isinstance(condition_row, dict) or "props" not in condition_row:
            return None
            
        condition_data = {
            "column": None,
            "operator": None,
            "value": None
        }
        
        row_props = condition_row.get("props", {})
        if "children" in row_props:
            # Grid 구조 탐색
            for child in row_props.get("children", []):
                if isinstance(child, dict) and "props" in child:
                    # Grid columns
                    for col_child in child.get("props", {}).get("children", []):
                        if isinstance(col_child, dict) and "props" in col_child:
                            # Grid column content
                            for component in col_child.get("props", {}).get("children", []):
                                if isinstance(component, dict) and "props" in component:
                                    comp_props = component.get("props", {})
                                    comp_id = comp_props.get("id", {})
                                    
                                    if isinstance(comp_id, dict):
                                        id_type = comp_id.get("type")
                                        if id_type == "condition-column" and "value" in comp_props:
                                            condition_data["column"] = comp_props["value"]
                                        elif id_type == "condition-operator" and "value" in comp_props:
                                            condition_data["operator"] = comp_props["value"]
                                        elif id_type == "condition-value" and "value" in comp_props:
                                            condition_data["value"] = comp_props["value"]
        
        return condition_data



    def _build_condition(self, column: str, operator: str, value: Any, df: pl.DataFrame) -> pl.Expr:
        """Build a single condition expression"""
        col_expr = pl.col(column)
        
        # Handle NULL checks
        if operator == "is_null":
            return col_expr.is_null()
        elif operator == "is_not_null":
            return col_expr.is_not_null()
        
        # Parse value - 개선된 버전으로 arithmetic expression 지원
        if value and isinstance(value, str):
            # Check if value contains arithmetic operations with columns
            if any(op in value for op in ['+', '-', '*', '/', '(', ')']):
                # Try to parse as arithmetic expression
                try:
                    value_expr = self._parse_arithmetic_expression(value, df)
                except:
                    # If parsing fails, treat as literal
                    value_expr = self._parse_input(value, df)
            else:
                value_expr = self._parse_input(value, df)
        else:
            value_expr = self._parse_input(value, df)
        
        # Build condition based on operator
        if operator == "==":
            return col_expr == value_expr
        elif operator == "!=":
            return col_expr != value_expr
        elif operator == ">":
            return col_expr > value_expr
        elif operator == "<":
            return col_expr < value_expr
        elif operator == ">=":
            return col_expr >= value_expr
        elif operator == "<=":
            return col_expr <= value_expr
        elif operator == "contains":
            return col_expr.cast(pl.Utf8).str.contains(str(value))
        elif operator == "starts_with":
            return col_expr.cast(pl.Utf8).str.starts_with(str(value))
        elif operator == "ends_with":
            return col_expr.cast(pl.Utf8).str.ends_with(str(value))
        else:
            raise ValueError(f"Unknown operator: {operator}")

    def _parse_arithmetic_expression(self, expr_str: str, df: pl.DataFrame) -> pl.Expr:
        """Parse arithmetic expression string (e.g., 'drain_v - bulk_v')"""
        # 간단한 파서 구현 - 기본 산술 연산 지원
        # 더 복잡한 표현식을 위해서는 실제 expression parser를 사용하는 것이 좋습니다
        
        # 토큰화
        tokens = re.split(r'(\s*[+\-*/()]\s*)', expr_str)
        tokens = [t.strip() for t in tokens if t.strip()]
        
        # 표현식 빌드
        def parse_token(token):
            if token in df.columns:
                return pl.col(token)
            elif token in ['+', '-', '*', '/', '(', ')']:
                return token
            else:
                # 숫자로 파싱 시도
                try:
                    if '.' in token:
                        return pl.lit(float(token))
                    else:
                        return pl.lit(int(token))
                except:
                    # 문자열로 처리
                    return pl.lit(token)
        
        # 간단한 두 항 연산 처리 (e.g., "drain_v - bulk_v")
        if len(tokens) == 3 and tokens[1] in ['+', '-', '*', '/']:
            left = parse_token(tokens[0])
            right = parse_token(tokens[2])
            op = tokens[1]
            
            if op == '+':
                return left + right
            elif op == '-':
                return left - right
            elif op == '*':
                return left * right
            elif op == '/':
                return left / right
        
        # 더 복잡한 표현식은 에러
        raise ValueError(f"Complex arithmetic expressions not yet supported: {expr_str}")

    def _parse_input(self, value: Any, df: pl.DataFrame) -> pl.Expr:
        """Parse input value as column reference or literal"""
        if value is None or value == "":
            return pl.lit(None)
        
        # Check if it's a column reference
        if isinstance(value, str) and value in df.columns:
            return pl.col(value)
        
        # Try to parse as number
        try:
            # Handle scientific notation
            if isinstance(value, str) and ('e' in value.lower() or 'E' in value):
                return pl.lit(float(value))
            
            # Check if it looks like a float
            if isinstance(value, str) and '.' in value:
                return pl.lit(float(value))
            else:
                # Try integer
                return pl.lit(int(value))
        except:
            # Return as string literal
            return pl.lit(str(value))
