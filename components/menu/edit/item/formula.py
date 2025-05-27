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
        
        # Simple formula operations
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
        
        # Condition operators for complex logic
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
        
        # Logical operators for combining conditions
        self.logical_operators = [
            {"value": "AND", "label": "AND"},
            {"value": "OR", "label": "OR"},
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
                                        dmc.Space(h=15),
                                        self.form.create_action_button(
                                            id="formula-simple-apply-btn",
                                            label="Apply Simple Formula",
                                            icon="tick"
                                        ),
                                    ],
                                ),

                                # Complex logic tab - Simplified
                                dmc.TabsPanel(
                                    value="complex",
                                    children=[
                                        dmc.Space(h=15),
                                        dmc.Alert(
                                            "Create conditional logic with if-then-else statements",
                                            color="blue",
                                            variant="light"
                                        ),
                                        dmc.Space(h=15),
                                        # 전체 논리 연산자 선택 (조건들을 어떻게 결합할지)
                                        dmc.Card(
                                            withBorder=True,
                                            p="md",
                                            mb="md",
                                            children=[
                                                dmc.Text("조건 연결 방식", fw=500, mb="xs"),
                                                dmc.RadioGroup(
                                                    id="global-logic-operator",
                                                    value="AND",
                                                    children=[
                                                        dmc.Group([
                                                            dmc.Radio("AND", value="AND"),
                                                            dmc.Text("모든 조건이 참일 때", size="sm", c="dimmed"),
                                                        ], gap="xs"),
                                                        dmc.Group([
                                                            dmc.Radio("OR", value="OR"),
                                                            dmc.Text("하나 이상의 조건이 참일 때", size="sm", c="dimmed"),
                                                        ], gap="xs"),
                                                    ],
                                                    size="sm"
                                                ),
                                            ]
                                        ),
                                        # Conditions container
                                        html.Div(
                                            id="complex-conditions-container",
                                            children=[]
                                        ),
                                        
                                        dmc.Space(h=15),
                                        dmc.Button(
                                            "Add Condition",
                                            id="add-condition-btn",
                                            leftSection=dbpc.Icon(icon="add"),
                                            variant="outline",
                                            size="sm",
                                        ),

                                        dmc.Space(h=20),

                                        # Then/Else values
                                        dmc.Grid([
                                            dmc.GridCol([
                                                dmc.TextInput(
                                                    id="complex-then-value",
                                                    label="Then Value (조건이 참일 때)",
                                                    description="모든 조건이 만족될 때의 값",
                                                    placeholder="e.g., 'O', 1, column_name",
                                                    required=True,
                                                )
                                            ], span=6),
                                            dmc.GridCol([
                                                dmc.TextInput(
                                                    id="complex-else-value",
                                                    label="Else Value (조건이 거짓일 때)",
                                                    description="조건이 만족되지 않을 때의 값",
                                                    placeholder="e.g., 'X', 0, column_name",
                                                    required=True,
                                                )
                                            ], span=6),
                                        ]),
                                        dmc.Space(h=10),
                                        self.form.create_action_button(
                                            id="formula-complex-apply-btn",
                                            label="Apply Complex Logic",
                                            icon="tick"
                                        )
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),

                # Help section
                self.form.create_help_section([
                    "Enter a name for the new calculated column",
                    "Choose formula type: Simple or Complex",
                    "Simple Formula: Mathematical operations and transformations",
                    "Complex Logic: Create if-then-else conditions with multiple conditions",
                    "You can reference existing columns by name in conditions",
                    "Complex Logic: Select AND (all conditions must be true) or OR (any condition can be true)",
                    "Example: mos_name contains '.xmn' AND vdb >= 0.95 → 'O', else → 'X'",
                    "Click the appropriate Apply button to create the column",
                ])
            ],
            gap="md",
        )


    def _create_condition_row(self, condition_id=None):
        """Create a single condition row for complex logic - 개선된 버전"""

        if not condition_id:
            condition_id = str(uuid.uuid4())

        # Get all columns including those created by formulas
        df = SSDF.dataframe
        all_columns = [{"value": col, "label": col} 
                        for col in df.columns 
                        if col not in ["uniqid", "group", "childCount"]]

        return dmc.Card(
            id={"type": "condition-row", "index": condition_id},
            withBorder=True,
            p="sm",
            mb="sm",
            children=[
                dmc.Grid([
                    # Column selection
                    dmc.GridCol([
                        dmc.Select(
                            id={"type": "condition-column", "index": condition_id},
                            label="Column",
                            placeholder="Select column",
                            data=all_columns,
                            searchable=True,
                            required=True,
                            size="sm",
                        )
                    ], span=3),

                    # Operator
                    dmc.GridCol([
                        dmc.Select(
                            id={"type": "condition-operator", "index": condition_id},
                            label="Operator",
                            placeholder="Select operator",
                            data=self.condition_operators,
                            required=True,
                            size="sm",
                        )
                    ], span=3),

                    # Value
                    dmc.GridCol([
                        dmc.TextInput(
                            id={"type": "condition-value", "index": condition_id},
                            label="Value",
                            placeholder="Enter value or column name",
                            required=True,
                            size="sm",
                        )
                    ], span=5),

                    # Remove button
                    dmc.GridCol([
                        dmc.ActionIcon(
                            dbpc.Icon(icon="trash"),
                            id={"type": "remove-condition", "index": condition_id},
                            color="red",
                            variant="subtle",
                            size="sm",
                        )
                    ], span=1),
                ]),
            ]
        )


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

        self.simple_formula_callbacks(app)
        self.complex_formula_callbacks(app)

    def simple_formula_callbacks(self, app):

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
                    
            # Additional parameters
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
                                description="Enter character to count",
                                placeholder=".",
                                required=True,
                            )
                        )
                    elif param == "substring_to_count":
                        inputs.append(
                            dmc.TextInput(
                                id=f"formula-param-{param}",
                                label="Substring to Count",
                                description="Enter substring to count",
                                placeholder="abc",
                                required=True,
                            )
                        )
                    elif param == "regex_pattern":
                        inputs.append(
                            dmc.TextInput(
                                id=f"formula-param-{param}",
                                label="Regex Pattern",
                                description="Enter regex pattern",
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

        # Apply Simple Formula
        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("formula-column-name", "value", allow_duplicate=True),
            Input("formula-simple-apply-btn", "n_clicks"),
            [
                State("formula-column-name", "value"),
                State("formula-category", "value"),
                State("formula-operation", "value"),
                State("simple-formula-inputs", "children"),
            ],
            prevent_initial_call=True,
        )
        def apply_simple_formula(n_clicks, column_name, category, operation, 
                               simple_inputs):
            if not n_clicks or not column_name:
                raise exceptions.PreventUpdate

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

                # Extract values from simple_inputs
                input_values = self._extract_input_values(simple_inputs)
                
                # Apply simple formula
                expr = self._build_simple_expression(
                    category, operation, input_values, df
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
                logger.error(f"Simple formula error: {str(e)}")
                return (
                    [dbpc.Toast(
                        message=f"Error: {str(e)}",
                        intent="danger",
                        icon="error"
                    )],
                    no_update,
                    no_update,
                )

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
        
        if category == "arithmetic":
            return self._build_arithmetic_expr(operation, input_values, df)
        elif category == "statistical":
            return self._build_statistical_expr(operation, input_values, df)
        elif category == "transform":
            return self._build_transform_expr(operation, input_values, df)
        elif category == "text":
            return self._build_text_expr(operation, input_values, df)
        else:
            raise ValueError(f"Unknown category: {category}")

    def _build_arithmetic_expr(self, operation: str, inputs: Dict, df: pl.DataFrame) -> pl.Expr:
        """Build arithmetic expression"""
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
            return pl.concat_list(col_exprs).list.eval(pl.element().median()).list.first()
        elif operation == "std":
            return pl.concat_list(col_exprs).list.eval(pl.element().std()).list.first()
        else:
            raise ValueError(f"Unknown statistical operation: {operation}")

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
        """Build text expression"""
        if operation == "concat":
            columns = inputs.get("formula-input-columns", [])
            if not columns:
                raise ValueError("No columns selected for concatenation")
            
            expr = pl.col(columns[0]).cast(pl.Utf8)
            for col in columns[1:]:
                expr = expr + pl.lit(" ") + pl.col(col).cast(pl.Utf8)
            return expr
        
        elif operation == "count_char":
            col = inputs.get("formula-input-0")
            char_to_count = inputs.get("formula-param-char_to_count")
            
            if not col or not char_to_count:
                raise ValueError("Column and character to count are required")
            
            return (
                pl.col(col).cast(pl.Utf8).str.len_chars() - 
                pl.col(col).cast(pl.Utf8).str.replace_all(char_to_count, "").str.len_chars()
            )
        
        elif operation == "count_substring":
            col = inputs.get("formula-input-0")
            substring = inputs.get("formula-param-substring_to_count")
            
            if not col or not substring:
                raise ValueError("Column and substring to count are required")
            
            return pl.col(col).cast(pl.Utf8).str.count_matches(re.escape(substring))
        
        elif operation == "count_regex":
            col = inputs.get("formula-input-0")
            pattern = inputs.get("formula-param-regex_pattern")
            
            if not col or not pattern:
                raise ValueError("Column and regex pattern are required")
            
            try:
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

    def complex_formula_callbacks(self, app):

        # Add condition row
        @app.callback(
            Output("complex-conditions-container", "children"),
            Input("add-condition-btn", "n_clicks"),
            State("complex-conditions-container", "children"),
            prevent_initial_call=True,
        )
        def add_condition(n_clicks, current_conditions):
            if not n_clicks:
                return current_conditions or []
            
            new_condition = self._create_condition_row()
            return (current_conditions or []) + [new_condition]

        # Remove condition row
        @app.callback(
            Output("complex-conditions-container", "children", allow_duplicate=True),
            Input({"type": "remove-condition", "index": ALL}, "n_clicks"),
            State("complex-conditions-container", "children"),
            prevent_initial_call=True,
        )
        def remove_condition(n_clicks_list, current_conditions):
            if not any(n_clicks_list) or not current_conditions:
                return current_conditions
            
            # Find which button was clicked
            triggered_id = ctx.triggered_id
            if not triggered_id:
                return current_conditions
            
            # Remove the corresponding condition
            condition_id = triggered_id["index"]
            return [cond for cond in current_conditions 
                   if cond["props"]["id"]["index"] != condition_id]


        @app.callback(
            Output("complex-conditions-container", "children", allow_duplicate=True),
            Input("formula-builder-tabs", "value"),
            State("complex-conditions-container", "children"),
            prevent_initial_call=True,
        )
        def initialize_complex_conditions(tab_value, current_conditions):
            """Complex Logic 탭 선택 시 초기 조건이 없으면 하나 추가"""
            if tab_value == "complex" and not current_conditions:
                return [self._create_condition_row()]
            return current_conditions or []

        # Apply Complex Logic
        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("formula-column-name", "value", allow_duplicate=True),
            Input("formula-complex-apply-btn", "n_clicks"),
            [
                State("formula-column-name", "value"),
                State("complex-conditions-container", "children"),
                State("global-logic-operator", "value"),
                State("complex-then-value", "value"),
                State("complex-else-value", "value"),
            ],
            prevent_initial_call=True,
        )
        def apply_complex_logic(n_clicks, column_name, conditions_container,
                               global_logic_operator, then_value, else_value):
            if not n_clicks or not column_name:
                raise exceptions.PreventUpdate
            
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
                
                # Build complex expression with improved logic
                expr = self._build_complex_expression(
                    conditions_container, global_logic_operator, then_value, else_value, df
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
                logger.error(f"Complex logic error: {str(e)}")
                return (
                    [dbpc.Toast(
                        message=f"Error: {str(e)}",
                        intent="danger",
                        icon="error"
                    )],
                    no_update,
                    no_update,
                )

    def _build_complex_expression(self, conditions_container: List, 
                                         global_logic_operator: str, then_value: str, 
                                         else_value: str, df: pl.DataFrame) -> pl.Expr:
        """Build improved complex conditional expression with global logic operator"""
        
        if not conditions_container or not then_value:
            raise ValueError("No conditions or values defined")
        
        # Extract conditions
        conditions = []
        
        for condition_div in conditions_container:
            if isinstance(condition_div, dict) and "props" in condition_div:
                condition_data = self._extract_condition_data(condition_div)
                if condition_data:
                    conditions.append(condition_data)
        
        if not conditions:
            raise ValueError("No valid conditions found")
        
        # Build individual condition expressions
        condition_expressions = []
        for cond_data in conditions:
            column = cond_data.get("column")
            operator = cond_data.get("operator")
            value = cond_data.get("value")
            
            if not column or not operator:
                continue
            
            # Build individual condition
            condition = self._build_condition(column, operator, value, df)
            condition_expressions.append(condition)
        
        if not condition_expressions:
            raise ValueError("Failed to build condition expressions")
        
        # Combine all conditions with global logic operator
        if len(condition_expressions) == 1:
            combined_condition = condition_expressions[0]
        else:
            combined_condition = condition_expressions[0]
            for condition in condition_expressions[1:]:
                if global_logic_operator == "OR":
                    combined_condition = combined_condition | condition
                else:  # Default to AND
                    combined_condition = combined_condition & condition
        
        # Parse then/else values
        then_expr = self._parse_input(then_value, df)
        else_expr = self._parse_input(else_value, df)
        
        # Build final expression
        return pl.when(combined_condition).then(then_expr).otherwise(else_expr)

    def _extract_condition_data(self, condition_div: Dict) -> Dict:
        """Extract condition data from improved UI component"""
        condition_data = {}
        
        try:
            # Navigate through the component structure to find the card content
            card_props = condition_div.get("props", {})
            card_children = card_props.get("children", [])
            
            # Find the grid component within the card
            grid_children = None
            for child in card_children:
                if isinstance(child, dict) and "props" in child:
                    if "children" in child["props"]:
                        grid_children = child["props"]["children"]
                        break
            
            if not grid_children:
                return condition_data
            
            # Extract data from grid columns
            for grid_col in grid_children:
                if not isinstance(grid_col, dict) or "props" not in grid_col:
                    continue
                
                col_children = grid_col["props"].get("children", [])
                
                for component in col_children:
                    if isinstance(component, dict) and "props" in component:
                        comp_props = component["props"]
                        if "id" in comp_props and isinstance(comp_props["id"], dict):
                            id_type = comp_props["id"].get("type")
                            
                            if id_type == "condition-column" and "value" in comp_props:
                                condition_data["column"] = comp_props["value"]
                            elif id_type == "condition-operator" and "value" in comp_props:
                                condition_data["operator"] = comp_props["value"]
                            elif id_type == "condition-value" and "value" in comp_props:
                                condition_data["value"] = comp_props["value"]
            
            return condition_data
            
        except Exception as e:
            logger.error(f"Error extracting condition data: {e}")
            return {}

    def _build_condition(self, column: str, operator: str, value: Any, df: pl.DataFrame) -> pl.Expr:
        """Build a single condition expression"""
        col_expr = pl.col(column)
        
        # Handle NULL checks
        if operator == "is_null":
            return col_expr.is_null()
        elif operator == "is_not_null":
            return col_expr.is_not_null()
        
        # Parse value - it could be a column reference or a literal
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
