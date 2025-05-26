import re
import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, no_update, exceptions, ctx, dcc
from typing import List, Tuple, Optional, Any

from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions
from components.menu.edit.common_utils import handle_tab_button_click, FormComponents


class SplitColumn:
    def __init__(self):
        self.form = FormComponents()

        # Predefined delimiter options
        self.predefined_delimiters = [{"value": ",", "label": "Comma (,)"}, {"value": ";", "label": "Semicolon (;)"}, {"value": " ", "label": "Space ( )"}, {"value": "\t", "label": "Tab (\\t)"}, {"value": "|", "label": "Pipe (|)"}, {"value": "-", "label": "Hyphen (-)"}, {"value": "_", "label": "Underscore (_)"}, {"value": ".", "label": "Dot (.)"}, {"value": ":", "label": "Colon (:)"}, {"value": "custom", "label": "Custom delimiter"}]

        # Split position options
        self.split_positions = [{"value": "all", "label": "Split at all occurrences"}, {"value": "first", "label": "Split at first occurrence"}, {"value": "last", "label": "Split at last occurrence"}, {"value": "n", "label": "Split at Nth occurrence"}]

    def button_layout(self):
        """Menu button layout"""
        return dbpc.Button("Split Column", id="split-column-btn", icon="segmented-control", minimal=True, outlined=True)

    def tab_layout(self):
        """Enhanced split column tab layout"""
        return dmc.Stack(
            [
                self.form.create_section_card(
                    title="Split Text to Columns",
                    icon="segmented-control",
                    description="Split text data into multiple columns based on delimiters",
                    children=[
                        # Source column selection
                        self.form.create_column_selector(id="split-column-source", label="Source Column", description="Select the column containing text to split", multi=False, data=[]),
                        dmc.Space(h=20),
                        # Split method tabs
                        dmc.Tabs(
                            id="split-method-tabs",
                            value="delimiter",
                            children=[
                                dmc.TabsList([dmc.TabsTab("By Delimiter", value="delimiter"), dmc.TabsTab("By Position", value="position"), dmc.TabsTab("Extract Pattern", value="pattern")]),
                                # Delimiter-based split
                                dmc.TabsPanel(
                                    value="delimiter",
                                    children=[
                                        dmc.Space(h=15),
                                        dmc.Select(id="split-column-delimiter-select", label="Delimiter", description="Choose or enter a delimiter", data=self.predefined_delimiters, value=".", searchable=True, clearable=False),
                                        # Custom delimiter input
                                        html.Div(
                                            id="split-column-custom-delimiter-container",
                                            style={"display": "none"},
                                            children=[
                                                dmc.Space(h=10),
                                                dmc.TextInput(
                                                    id="split-column-custom-delimiter",
                                                    label="Custom Delimiter",
                                                    description="Enter your custom delimiter",
                                                    placeholder="e.g., //, #, =>",
                                                ),
                                            ],
                                        ),
                                        dmc.Space(h=15),
                                        # Split position selection
                                        dmc.RadioGroup(id="split-position", label="Split Position", description="Where to split the text", value="all", children=[dmc.Radio(label=opt["label"], value=opt["value"]) for opt in self.split_positions]),
                                        # N-th occurrence input
                                        html.Div(id="split-nth-container", style={"display": "none"}, children=[dmc.Space(h=10), dmc.NumberInput(id="split-nth-value", label="Occurrence Number", description="Which occurrence to split at (1-based)", value=1, min=1, step=1)]),
                                        dmc.Space(h=15),
                                        # Extract specific part option
                                        dmc.Checkbox(id="extract-part-checkbox", label="Extract specific part only", description="Extract a specific part instead of creating multiple columns", checked=False),
                                        html.Div(id="extract-part-container", style={"display": "none"}, children=[dmc.Space(h=10), dmc.RadioGroup(id="extract-part-position", label="Part to Extract", value="last", children=[dmc.Radio("First part", value="first"), dmc.Radio("Last part", value="last"), dmc.Radio("All except last", value="all_except_last"), dmc.Radio("Specific index", value="index")]), html.Div(id="extract-index-container", style={"display": "none"}, children=[dmc.NumberInput(id="extract-index-value", label="Part Index (0-based)", value=0, min=0)])]),
                                    ],
                                ),
                                # Position-based split
                                dmc.TabsPanel(value="position", children=[dmc.Space(h=15), dmc.NumberInput(id="split-position-value", label="Split at Position", description="Character position to split at", value=5, min=1)]),
                                # Pattern extraction
                                dmc.TabsPanel(value="pattern", children=[dmc.Space(h=15), dmc.TextInput(id="split-pattern-regex", label="Regular Expression", description="Extract text matching this pattern", placeholder=r"e.g., \d+, [A-Z]+, \w+", value=r"\.xm[np]\d*$"), dmc.Space(h=10), dmc.Alert("Example patterns:\n" "• \\.xm[np]\\d*$ - Extract MOS type (xmn0, xmp1, etc.)\n" "• ^[^.]+\\. - Extract first part with dot\n" "• [^.]+$ - Extract last part after any dot", color="blue", variant="light")]),
                            ],
                        ),
                        dmc.Space(h=20),
                        # Additional options
                        dmc.Group([dmc.Checkbox(id="split-column-keep-original", label="Keep original column", checked=True), dmc.Checkbox(id="split-column-skip-empty", label="Skip empty results", checked=True)]),
                        dmc.Space(h=20),
                        # Column naming
                        dmc.RadioGroup(id="split-column-naming-method", label="Result Column Naming", value="auto", children=[dmc.Radio("Auto generate (column_1, column_2, ...)", value="auto"), dmc.Radio("Custom names", value="custom")]),
                        html.Div(id="split-column-custom-names-container", style={"display": "none"}, children=[dmc.Space(h=10), dmc.TextInput(id="split-column-custom-names", label="Custom Column Names", description="Comma-separated names for result columns", placeholder="first_part,second_part,third_part")]),
                    ],
                ),
                # Preview section
                self.form.create_preview_section(id="split-column-preview-container"),
                # Action buttons
                dmc.Group([self.form.create_action_button(id="split-column-apply-btn", label="Apply Split", icon="tick")], justify="center"),
                # Help section
                self.form.create_help_section(["Select the column containing text to split", "Choose split method: delimiter, position, or pattern", "Configure split options (position, extract specific part)", "Preview the results before applying", "Click Apply to create new columns", "Example: x_edge.xlog2.xmn0 → x_edge.xlog2 (extract all except last)"]),
            ],
            gap="md",
        )

    def register_callbacks(self, app):
        """Register all callbacks for split column functionality"""

        @app.callback(Output("flex-layout", "model", allow_duplicate=True), Output("toaster", "toasts", allow_duplicate=True), Input("split-column-btn", "n_clicks"), State("flex-layout", "model"), prevent_initial_call=True)
        def handle_split_column_button_click(n_clicks, current_model):
            """Handle split column button click"""
            return handle_tab_button_click(n_clicks, current_model, "split-column-tab", "Split Column")

        @app.callback(Output("split-column-source", "data"), Input("split-column-btn", "n_clicks"), State("aggrid-table", "columnDefs"), prevent_initial_call=True)
        def update_column_list(n_clicks, columnDefs):
            """Update column list for source selection"""
            if n_clicks is None or not columnDefs:
                return []

            protected_columns = ["uniqid", "group", "childCount"]
            df = SSDF.dataframe

            text_columns = []
            for col in df.columns:
                if col not in protected_columns:
                    col_dtype = df[col].dtype
                    if col_dtype in [pl.Utf8, pl.String, pl.Categorical]:
                        text_columns.append({"label": col, "value": col})

            return text_columns

        @app.callback(Output("split-column-custom-delimiter-container", "style"), Input("split-column-delimiter-select", "value"), prevent_initial_call=True)
        def toggle_custom_delimiter(delimiter):
            """Show/hide custom delimiter input"""
            return {"display": "block" if delimiter == "custom" else "none"}

        @app.callback(Output("split-nth-container", "style"), Input("split-position", "value"), prevent_initial_call=True)
        def toggle_nth_input(position):
            """Show/hide nth occurrence input"""
            return {"display": "block" if position == "n" else "none"}

        @app.callback(Output("extract-part-container", "style"), Input("extract-part-checkbox", "checked"), prevent_initial_call=True)
        def toggle_extract_options(checked):
            """Show/hide extract part options"""
            return {"display": "block" if checked else "none"}

        @app.callback(Output("extract-index-container", "style"), Input("extract-part-position", "value"), prevent_initial_call=True)
        def toggle_extract_index(position):
            """Show/hide extract index input"""
            return {"display": "block" if position == "index" else "none"}

        @app.callback(Output("split-column-custom-names-container", "style"), Input("split-column-naming-method", "value"), prevent_initial_call=True)
        def toggle_custom_names(naming_method):
            """Show/hide custom names input"""
            return {"display": "block" if naming_method == "custom" else "none"}

        @app.callback(Output("split-column-preview-container", "children"), [Input("split-column-source", "value"), Input("split-method-tabs", "value"), Input("split-column-delimiter-select", "value"), Input("split-column-custom-delimiter", "value"), Input("split-position", "value"), Input("split-nth-value", "value"), Input("extract-part-checkbox", "checked"), Input("extract-part-position", "value"), Input("extract-index-value", "value"), Input("split-position-value", "value"), Input("split-pattern-regex", "value"), Input("split-column-skip-empty", "checked")], prevent_initial_call=True)
        def update_preview(source_column, method, delimiter_select, custom_delimiter, split_pos, nth_value, extract_part, extract_position, extract_index, position_value, pattern_regex, skip_empty):
            """Update preview based on current settings"""
            if not source_column:
                return [dmc.Text("Select a source column", size="sm", c="dimmed")]

            try:
                df = SSDF.dataframe

                # Get sample values
                sample_values = []
                count = 0
                for val in df[source_column]:
                    if val is not None and val != "" and count < 5:
                        sample_values.append(val)
                        count += 1

                if not sample_values:
                    return [dmc.Text("No sample data available", size="sm", c="dimmed")]

                # Process based on method
                preview_results = []

                for val in sample_values:
                    if method == "delimiter":
                        # Get actual delimiter
                        actual_delimiter = custom_delimiter if delimiter_select == "custom" else delimiter_select
                        if not actual_delimiter:
                            return [dmc.Text("Please enter a delimiter", size="sm", c="dimmed")]

                        result = self._split_by_delimiter(val, actual_delimiter, split_pos, nth_value, extract_part, extract_position, extract_index, skip_empty)

                    elif method == "position":
                        result = self._split_by_position(val, position_value)

                    elif method == "pattern":
                        result = self._split_by_pattern(val, pattern_regex)

                    preview_results.append((val, result))

                # Create preview table
                return self._create_preview_table(preview_results, extract_part)

            except Exception as e:
                logger.error(f"Preview generation error: {str(e)}")
                return [dmc.Alert(f"Error: {str(e)}", color="red")]

        @app.callback(Output("toaster", "toasts", allow_duplicate=True), Output("aggrid-table", "columnDefs", allow_duplicate=True), Output("split-column-apply-btn", "loading"), [Input("split-column-apply-btn", "n_clicks")], [State("split-column-source", "value"), State("split-method-tabs", "value"), State("split-column-delimiter-select", "value"), State("split-column-custom-delimiter", "value"), State("split-position", "value"), State("split-nth-value", "value"), State("extract-part-checkbox", "checked"), State("extract-part-position", "value"), State("extract-index-value", "value"), State("split-position-value", "value"), State("split-pattern-regex", "value"), State("split-column-naming-method", "value"), State("split-column-custom-names", "value"), State("split-column-keep-original", "checked"), State("split-column-skip-empty", "checked")], prevent_initial_call=True)
        def apply_split_column(n_clicks, source_column, method, delimiter_select, custom_delimiter, split_pos, nth_value, extract_part, extract_position, extract_index, position_value, pattern_regex, naming_method, custom_names, keep_original, skip_empty):
            """Apply the split column operation"""
            if not n_clicks or not source_column:
                raise exceptions.PreventUpdate

            try:
                df = SSDF.dataframe.clone()

                if method == "delimiter":
                    # Apply delimiter-based split
                    actual_delimiter = custom_delimiter if delimiter_select == "custom" else delimiter_select
                    if not actual_delimiter:
                        return ([dbpc.Toast(message="Please specify a delimiter", intent="warning", icon="warning-sign")], no_update, False)

                    new_columns = self._apply_delimiter_split(df, source_column, actual_delimiter, split_pos, nth_value, extract_part, extract_position, extract_index, skip_empty, naming_method, custom_names)

                elif method == "position":
                    new_columns = self._apply_position_split(df, source_column, position_value, naming_method, custom_names)

                elif method == "pattern":
                    new_columns = self._apply_pattern_split(df, source_column, pattern_regex, naming_method, custom_names)

                # Remove original column if not keeping
                if not keep_original and not extract_part:
                    SSDF.dataframe = SSDF.dataframe.drop(source_column)

                # Update dataframe
                updated_columnDefs = generate_column_definitions(SSDF.dataframe)

                # Success message
                if extract_part:
                    message = f"Successfully extracted data to column '{new_columns[0]}'"
                else:
                    message = f"Successfully split into {len(new_columns)} columns: {', '.join(new_columns)}"

                return ([dbpc.Toast(message=message, intent="success", icon="endorsed", timeout=3000)], updated_columnDefs, False)

            except Exception as e:
                logger.error(f"Split column error: {str(e)}")
                return ([dbpc.Toast(message=f"Error: {str(e)}", intent="danger", icon="error")], no_update, False)

    def _split_by_delimiter(self, text: str, delimiter: str, split_pos: str, nth_value: int, extract_part: bool, extract_position: str, extract_index: int, skip_empty: bool) -> List[str]:
        """Split text by delimiter with various options"""
        if split_pos == "all":
            parts = text.split(delimiter)
        elif split_pos == "first":
            parts = text.split(delimiter, 1)
        elif split_pos == "last":
            # Split at last occurrence
            parts = text.rsplit(delimiter, 1)
        elif split_pos == "n":
            # Split at nth occurrence
            splits = text.split(delimiter)
            if len(splits) > nth_value:
                parts = [delimiter.join(splits[:nth_value]), delimiter.join(splits[nth_value:])]
            else:
                parts = [text]

        if skip_empty:
            parts = [p for p in parts if p]

        if extract_part:
            if extract_position == "first":
                return [parts[0]] if parts else [""]
            elif extract_position == "last":
                return [parts[-1]] if parts else [""]
            elif extract_position == "all_except_last":
                if len(parts) > 1:
                    return [delimiter.join(parts[:-1])]
                return [""]
            elif extract_position == "index":
                if 0 <= extract_index < len(parts):
                    return [parts[extract_index]]
                return [""]

        return parts

    def _split_by_position(self, text: str, position: int) -> List[str]:
        """Split text at specific position"""
        if position >= len(text):
            return [text, ""]
        return [text[:position], text[position:]]

    def _split_by_pattern(self, text: str, pattern: str) -> List[str]:
        """Extract text matching pattern"""
        try:
            match = re.search(pattern, text)
            if match:
                return [match.group()]
            return [""]
        except re.error:
            return [""]

    def _create_preview_table(self, results: List[Tuple[str, List[str]]], extract_only: bool) -> List[Any]:
        """Create preview table for split results"""
        preview_content = []

        # Determine maximum parts
        max_parts = max(len(result[1]) for result in results)

        # Create table headers
        headers = [dmc.TableTh("Original")]
        if extract_only:
            headers.append(dmc.TableTh("Extracted"))
        else:
            for i in range(max_parts):
                headers.append(dmc.TableTh(f"Part {i+1}"))

        # Create table rows
        rows = []
        for original, parts in results:
            cells = [dmc.TableTd(original)]
            for i in range(max_parts if not extract_only else 1):
                if i < len(parts):
                    cells.append(dmc.TableTd(parts[i]))
                else:
                    cells.append(dmc.TableTd("-", style={"color": "gray"}))
            rows.append(dmc.TableTr(cells))

        preview_table = dmc.Table([dmc.TableThead(dmc.TableTr(headers)), dmc.TableTbody(rows)], striped=True, highlightOnHover=True, withTableBorder=True, withColumnBorders=True)

        preview_content.append(preview_table)
        return preview_content

    def _apply_delimiter_split(self, df: pl.DataFrame, source_column: str, delimiter: str, split_pos: str, nth_value: int, extract_part: bool, extract_position: str, extract_index: int, skip_empty: bool, naming_method: str, custom_names: str) -> List[str]:
        """Apply delimiter-based split to dataframe"""

        # Define split function
        def split_text(text):
            if text is None or text == "":
                return []
            return self._split_by_delimiter(str(text), delimiter, split_pos, nth_value, extract_part, extract_position, extract_index, skip_empty)

        # Apply split to get max parts
        split_results = []
        max_parts = 0

        for val in df[source_column]:
            parts = split_text(val)
            split_results.append(parts)
            max_parts = max(max_parts, len(parts))

        # Generate column names
        if extract_part:
            if naming_method == "custom" and custom_names:
                column_names = [custom_names.strip()]
            else:
                if extract_position == "all_except_last":
                    column_names = [f"{source_column}_prefix"]
                else:
                    column_names = [f"{source_column}_extracted"]
        else:
            if naming_method == "auto":
                column_names = [f"{source_column}_{i+1}" for i in range(max_parts)]
            else:
                names = [name.strip() for name in custom_names.split(",")]
                column_names = names[:max_parts]
                if len(names) < max_parts:
                    column_names.extend([f"{source_column}_{i+1}" for i in range(len(names), max_parts)])

            # Add new columns to dataframe
            for i, col_name in enumerate(column_names):
                values = []
                for parts in split_results:
                    if i < len(parts):
                        values.append(parts[i])
                    else:
                        values.append(None)

                SSDF.dataframe = SSDF.dataframe.with_columns(pl.Series(name=col_name, values=values))

        return column_names

    def _apply_position_split(self, df: pl.DataFrame, source_column: str, position: int, naming_method: str, custom_names: str) -> List[str]:
        """Apply position-based split to dataframe"""

        # Generate column names
        if naming_method == "auto":
            column_names = [f"{source_column}_left", f"{source_column}_right"]
        else:
            names = [name.strip() for name in custom_names.split(",")]
            column_names = names[:2] if len(names) >= 2 else [f"{source_column}_left", f"{source_column}_right"]

        # Apply split
        SSDF.dataframe = SSDF.dataframe.with_columns([pl.col(source_column).str.slice(0, position).alias(column_names[0]), pl.col(source_column).str.slice(position, None).alias(column_names[1])])

        return column_names

    def _apply_pattern_split(self, df: pl.DataFrame, source_column: str, pattern: str, naming_method: str, custom_names: str) -> List[str]:
        """Apply pattern-based extraction to dataframe"""

        # Generate column name
        if naming_method == "auto":
            column_name = f"{source_column}_extracted"
        else:
            column_name = custom_names.strip() if custom_names else f"{source_column}_extracted"

        # Apply pattern extraction
        SSDF.dataframe = SSDF.dataframe.with_columns(pl.col(source_column).str.extract(pattern, group_index=0).alias(column_name))

        return [column_name]
