import re
import polars as pl
import dash_mantine_components as dmc
import dash_ag_grid as dag
from utils.component_template import get_icon
from functools import lru_cache
from dash import Input, Output, State, html, no_update, ctx
from components.grid.dag.column_definitions import generate_column_definitions
from utils.db_management import SSDF
from utils.config import CONFIG
from utils.logging_utils import logger
from utils.component_template import create_notification
import subprocess


class CategorizePart:

    def __init__(self) -> None:
        self.rule_df = pl.read_csv(f"{CONFIG.SCRIPT}/categorize_rule.csv")

    def layout(self):
        return html.Div(
            [
                dmc.Button(
                    "Categorize Part",
                    id="categorizePart-modal-open-btn",
                    variant="outline",
                    color="indigo",
                    size="xs",
                    leftSection=get_icon("bx-code"),
                ),
                self.modal(),
            ]
        )

        def modal(self):
            return dmc.Modal(
                title=dmc.Title(f"Categorize Part", order=3),
                id="categorizePart-modal",
                size="xl",
                opened=False,
                closeOnClickOutside=False,
                children=[
                    dmc.Card(
                        children=[
                            dmc.LoadingOverlay(
                                visible=False,
                                id="categorizePart-loading-overlay",
                                zIndex=1000,
                                overlayProps={"radius": "sm", "blur": 2},
                            ),
                            dmc.Grid(
                                [
                                    dmc.GridCol(
                                        dmc.Select(
                                            label="Select categorizing column",
                                            id="categorizePart-df-column-select",
                                            data=[],
                                            required=True,
                                            size="xs",
                                            error="",
                                        ),
                                        span=8,
                                    ),
                                    dmc.GridCol(
                                        dmc.RadioGroup(
                                            children=dmc.Group(
                                                [
                                                    dmc.Radio(i, value=i)
                                                    for i in [".", "/"]
                                                ],
                                            ),
                                            id="categorizePart-delimiter-radioGroup",
                                            label="Select delimiter",
                                            size="xs",
                                            value=".",
                                            required=True,
                                        ),
                                        span=4,
                                    ),
                                ]
                            ),
                            dmc.Space(h=10),
                            dmc.Group(
                                [
                                    dmc.Text("Rule Table: ", mr=2, fw=500, size="sm"),
                                    dmc.Group(
                                        [
                                            dmc.Button(
                                                "Download",
                                                id="categorizePart-download-btn",
                                                size="xs",
                                                variant="outline",
                                            ),
                                            dmc.Button(
                                                "Upload",
                                                id="categorizePart-upload-btn",
                                                size="xs",
                                                variant="outline",
                                            ),
                                        ],
                                        gap="xs",
                                        mb=1,
                                    ),
                                ]
                            ),
                            dag.AgGrid(
                                id="categorizePart-rule-grid",
                                columnDefs=[
                                    {"field": col} for col in self.rule_df.columns
                                ],
                                rowData=self.rule_df.to_dicts(),
                                defaultColDef={
                                    "resizable": True,
                                    "sortable": True,
                                    "editable": True,
                                },
                            ),
                            dmc.Group(
                                [
                                    dmc.Text("Configs", size="sm", fw=500),
                                    dmc.Switch(
                                        checked=True,
                                        labelPosition="left",
                                        label="Matching Method: ",
                                        id="categorizePart-matching-switch",
                                        onLabel="Pattern",
                                        offLabel="Equal",
                                        size="md",
                                    ),
                                ],
                                mt="sm",
                                justify="flex-start",
                            ),
                            dmc.Grid(
                                [
                                    dmc.GridCol(
                                        dmc.Stack(
                                            [
                                                dmc.Text(
                                                    "Regular Expression",
                                                    size="xs",
                                                    fw=500,
                                                ),
                                                dmc.Switch(
                                                    labelPosition="left",
                                                    checked=True,
                                                    id="categorizePart-regex-switch",
                                                    onLabel="On",
                                                    offLabel="OFF",
                                                ),
                                            ],
                                            gap=5,
                                            mt=5,
                                        ),
                                        span=3,
                                    ),
                                    dmc.GridCol(
                                        dmc.Stack(
                                            [
                                                dmc.Text(
                                                    "Case Sensitive", size="xs", fw=500
                                                ),
                                                dmc.Switch(
                                                    labelPosition="left",
                                                    onLabel="On",
                                                    offLabel="OFF",
                                                    checked=False,
                                                    id="categorizePart-caseSensitive-switch",
                                                ),
                                            ],
                                            gap=6,
                                            mt=6,
                                        ),
                                        span=3,
                                    ),
                                    dmc.GridCol(
                                        dmc.Select(
                                            label="Search Direction",
                                            data=["Bottom-Top", "Top-Bottom"],
                                            required=True,
                                            size="xs",
                                            value="Top-Bottom",
                                            id="categorizePart-searchDirection-select",
                                        ),
                                        span=3,
                                    ),
                                    dmc.GridCol(
                                        dmc.TextInput(
                                            label="Skip Master:",
                                            placeholder="Ex) Master1,Master2,Master3",
                                            size="xs",
                                            id="categorizePart-skipMaster-text",
                                        ),
                                        span=3,
                                    ),
                                ]
                            ),
                            dmc.Grid(
                                [
                                    dmc.GridCol(
                                        dmc.Select(
                                            label="Select Column to make BaseName column",
                                            id="categorizePart-df-basename-column-select",
                                            data=[],
                                            size="xs",
                                            error="",
                                        ),
                                        span=8,
                                    ),
                                ]
                            ),
                            dmc.Button(
                                "Categorize",
                                id="apply-categorizePart-btn",
                                variant="outline",
                                fullWidth=True,
                                mt=15,
                                disabled=True,
                            ),
                            html.Div(id="categorizePart-output"),
                        ],
                        withBorder=True,
                        shadow="sm",
                        radius="md",
                    )
                ],
            )

    def register_callbacks(self, app):
        @app.callback(
            Output("categorizePart-modal", "opened", allow_duplicate=True),
            Output("categorizePart-df-column-select", "data"),
            Output("categorizePart-df-basename-column-select", "data"),
            Output("categorizePart-loading-overlay", "visible", allow_duplicate=True),
            Input("categorizePart-modal-open-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def categorizePart_modal_open(nc):
            columns = SSDF.dataframe.columns
            return True, columns, columns, False

        @app.callback(
            Output("apply-categorizePart-btn", "disabled", allow_duplicate=True),
            Input("categorizePart-df-column-select", "value"),
            prevent_initial_call=True,
        )
        def activate_run_perc_btn(column):
            return False if column else True

        @app.callback(
            Output("categorizePart-regex-switch", "disabled"),
            Output("categorizePart-caseSensitive-switch", "disabled"),
            Output("categorizePart-searchDirection-select", "disabled"),
            Output("categorizePart-skipMaster-text", "disabled"),
            Output("categorizePart-df-basename-column-select", "disabled"),
            Input("categorizePart-matching-switch", "checked"),
            prevent_initial_call=True,
        )
        def matching_categorize_method(match_checked):
            ret = False if match_checked else True
            return [ret] * 5

        app.clientside_callback(
            """
            function updateLoadingState(n_clicks) {
                return true
            }
            """,
            Output("categorizePart-loading-overlay", "visible", allow_duplicate=True),
            Input("apply-categorizePart-btn", "n_clicks"),
            prevent_initial_call=True,
        )

        @app.callback(
            Output("categorizePart-modal", "opened", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("categorizePart-loading-overlay", "visible"),
            Output("notifications", "children", allow_duplicate=True),
            Input("apply-categorizePart-btn", "n_clicks"),
            State("categorizePart-rule-grid", "rowData"),
            State("categorizePart-df-column-select", "value"),
            State("categorizePart-regex-switch", "checked"),
            State("categorizePart-caseSensitive-switch", "checked"),
            State("categorizePart-searchDirection-select", "value"),
            State("categorizePart-skipMaster-text", "value"),
            State("categorizePart-delimiter-radioGroup", "value"),
            State("categorizePart-df-basename-column-select", "value"),
            State("categorizePart-matching-switch", "checked"),
            prevent_initial_call=True,
        )
        def run_categorize(
            n,
            rowData,
            selected_col,
            use_regex,
            case_sensitive,
            search_dir,
            skip_masters_str,
            delimiter,
            basename_col,
            pattern_match,
        ):

            @lru_cache(maxsize=1000)  # Adjust size according to your data
            def categorize_part(full_master):
                hierarchy = full_master.split(delimiter)
                if search_dir == "Bottom-Top":
                    hierarchy.reverse()
                skipped_hier = []
                for hier in hierarchy:
                    if hier in skip_masters:
                        skipped_hier.append(hier)
                        continue
                    for pattern, columns in compiled_rules:
                        if use_regex:
                            if pattern.match(hier):
                                columns["Unit Name"] = hier

                                return columns.copy()
                        else:
                            if pattern == hier:
                                columns["Unit Name"] = hier

                                return columns

                for hier in skipped_hier:
                    for pattern, columns in compiled_rules:
                        if use_regex:
                            if pattern.match(hier):
                                columns["Unit Name"] = hier

                                return columns
                        else:
                            if pattern == hier:
                                columns["Unit Name"] = hier

                                return columns
                return {col: "Unknown" for col in column_names + ["Unit Name"]}

            def create_basename(full_master, inst_name, unit_name):
                try:
                    FMs = full_master.split(delimiter)
                    INs = inst_name.split(delimiter)
                    basename_index = FMs.index(unit_name)

                    return delimiter.join(INs[basename_index + 1 :])
                except Exception as e:
                    return "Unknown"

            try:
                if pattern_match:
                    # Convert rule data to Polars DataFrame
                    rule_df = pl.DataFrame(rowData)
                    pattern_col = rule_df.columns[0]
                    column_names = rule_df.columns[1:]
                    rules = rule_df.to_dict(as_series=False)

                    if use_regex:
                        if case_sensitive:
                            compiled_rules = [
                                (
                                    re.compile(regex),
                                    {col: rules[col][i] for col in column_names},
                                )
                                for i, regex in enumerate(rules[pattern_col])
                            ]
                        else:
                            compiled_rules = [
                                (
                                    re.compile(regex, re.IGNORECASE),
                                    {col: rules[col][i] for col in column_names},
                                )
                                for i, regex in enumerate(rules[pattern_col])
                            ]
                    else:
                        if case_sensitive:
                            compiled_rules = [
                                (regex, {col: rules[col][i] for col in column_names})
                                for i, regex in enumerate(rules[pattern_col])
                            ]
                        else:
                            compiled_rules = [
                                (
                                    regex.lower(),
                                    {col: rules[col][i] for col in column_names},
                                )
                                for i, regex in enumerate(rules[pattern_col])
                            ]

                    skip_masters = [
                        s.strip() for s in skip_masters_str.split(",") if s.strip()
                    ]

                    # Categorize and add new columns to the dataframe
                    dff = SSDF.dataframe

                    for c in column_names:
                        if c in dff.columns:
                            dff = dff.drop(c)

                    new_columns = dff[selected_col].map_elements(
                        lambda x: categorize_part(x), return_dtype=pl.Object
                    )

                    for col in column_names + ["Unit Name"]:
                        dff = dff.with_columns(
                            pl.Series(col, [nc[col] for nc in new_columns]).alias(col)
                        )

                    if basename_col:
                        dff = dff.with_columns(
                            pl.struct([selected_col, basename_col, "Unit Name"])
                            .map_elements(
                                lambda x: create_basename(
                                    x[selected_col], x[basename_col], x["Unit Name"]
                                ),
                                return_dtype=pl.Utf8,
                            )
                            .alias("Base Name")
                        )

                    SSDF.dataframe = dff
                    updated_columnDefs = generate_column_definitions(SSDF.dataframe)

                else:
                    dff = SSDF.dataframe
                    rule_df = pl.DataFrame(rowData)
                    pattern_col = rule_df.columns[0]

                    SSDF.dataframe = dff.join(
                        rule_df,
                        left_on=selected_col,
                        right_on=pattern_col,
                        how="left",
                        suffix="_cate",
                    )

                    updated_columnDefs = generate_column_definitions(SSDF.dataframe)

                return False, updated_columnDefs, False, None

            except Exception as e:
                logger.error(f"{e}")
                return (
                    no_update,
                    no_update,
                    False,
                    create_notification(message=f"{e}", position="center"),
                )
