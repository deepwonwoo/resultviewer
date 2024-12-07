import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Input, Output, State, Patch, no_update, exceptions, html
from utils.data_processing import displaying_df
from utils.db_management import SSDF
from components.grid.dag.column_definitions import generate_column_definitions
from components.grid.dag.server_side_operations import apply_filters


class Columns:
    def layout(self):
        return dmc.Group(
            [
                dbpc.Button("Modify Column", id="modify-column-btn", icon="derive-column", minimal=True, outlined=True),
                dbpc.Button("Find & Replace", id="find-replace-btn", icon="exchange", minimal=True, outlined=True),
            ],
            gap=2,
        )

    def modify_tab(self):
        return dmc.Paper(
            children=[
                dmc.Group([dbpc.EntityTitle(title="Modify Column", heading="H5", icon="derive-column")], grow=True),
                dmc.Space(h=10),
                dmc.Stack(
                    children=[
                        dmc.Select(id="modify-column-select", label="Select Column to Modify", data=[]),
                        html.Div(
                            [
                                dmc.Select(
                                    label="Operation",
                                    id="modify-numeric-operation",
                                    data=[
                                        {"label": "Add", "value": "add"},
                                        {"label": "Subtract", "value": "subtract"},
                                        {"label": "Multiply", "value": "multiply"},
                                        {"label": "Divide", "value": "divide"},
                                        {"label": "Round to", "value": "round"},
                                    ],
                                ),
                                dmc.NumberInput(label="Value", id="modify-numeric-value", mb=10),
                                dmc.Checkbox(
                                    id="modify-numeric-inplace",
                                    label="Modify in-place (otherwise create new column)",
                                    checked=True,
                                ),
                            ],
                            id="modify-numeric-options",
                            style={"display": "none"},
                        ),
                        html.Div(
                            [
                                dmc.TextInput(label="Find", id="modify-text-find", mb=10),
                                dmc.TextInput(label="Replace with", id="modify-text-replace", mb=10),
                                dmc.Checkbox(
                                    id="modify-text-regex", label="Use regular expression", checked=False, mb=20
                                ),
                                dmc.Checkbox(
                                    id="modify-text-case-sensitive",
                                    label="Case sensitive",
                                    checked=False,
                                    disabled=True,
                                ),
                            ],
                            id="modify-text-options",
                            style={"display": "none"},
                        ),
                    ],
                    justify="space-around",
                    align="stretch",
                    gap="lg",
                ),
                dmc.Space(h=20),
                dmc.Checkbox(
                    id="modify-filtered-only", label="Apply to filtered data only", checked=True, size="sm", mb=10
                ),
                dbpc.Button(
                    "Apply", id="modify-column-apply-btn", intent="primary", outlined=True, minimal=True, fill=True
                ),
            ],
            p="md",
            shadow="sm",
            radius="xs",
            withBorder=True,
        )

    def find_replace_tab(self):
        return dmc.Paper(
            children=[
                dmc.Group([dbpc.EntityTitle(title="Find & Replace", heading="H5", icon="exchange")], grow=True),
                dmc.Space(h=10),
                dmc.Stack(
                    children=[
                        dmc.Select(
                            label="Select Column",
                            id="find-replace-column-select",
                            data=[],
                            clearable=False,
                            style={"width": 200},
                        ),
                        dmc.Space(h=5),
                        dmc.TextInput(label="Find", id="find-replace-find-input", placeholder="Value to find"),
                        dmc.TextInput(
                            label="Replace", id="find-replace-replace-input", placeholder="Value to replace with"
                        ),
                        dmc.Checkbox(
                            label="Use Regular Expression (for string columns)", id="find-replace-regex-checkbox"
                        ),
                    ],
                    justify="space-around",
                    align="stretch",
                    gap="lg",
                ),
                dmc.Space(h=10),
                dbpc.Button(
                    "Apply", id="find-replace-apply-btn", intent="primary", outlined=True, minimal=True, fill=True
                ),
            ],
            p="md",
            shadow="sm",
            radius="xs",
            withBorder=True,
        )

    def _register_modify_column_callback(self, app):

        @app.callback(
            Output("flex-layout", "model", allow_duplicate=True),
            Output("toaster", "toasts", allow_duplicate=True),
            Output("modify-column-select", "data"),
            Output("modify-column-select", "value"),
            Input("modify-column-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True,
        )
        def handle_modify_column_button_click(n_clicks, current_model):
            if n_clicks is None:
                raise exceptions.PreventUpdate
            dff = displaying_df()
            if dff is None:
                return (
                    no_update,
                    [dbpc.Toast(message=f"No Dataframe loaded", intent="warning", icon="warning-sign")],
                    [],
                    [],
                )
            right_border_index = next(
                (i for i, b in enumerate(current_model["borders"]) if b["location"] == "right"), None
            )
            # 이미 col-modify-tab 탭이 있는지 확인
            if right_border_index is not None:
                existing_tabs = current_model["borders"][right_border_index].get("children", [])
                tab_exists = any(tab.get("id") == "col-modify-tab" for tab in existing_tabs)
                if tab_exists:
                    # 이미 탭이 있다면 해당 탭을 선택하도록 함
                    patched_model = Patch()
                    tab_index = next(i for i, tab in enumerate(existing_tabs) if tab.get("id") == "col-modify-tab")
                    patched_model["borders"][right_border_index]["selected"] = tab_index
                    return patched_model, no_update, dff.columns, None
            # 새로운 탭 정의
            new_tab = {
                "type": "tab",
                "name": "Modify Column",
                "component": "button",
                "enableClose": True,
                "id": "col-modify-tab",
            }
            patched_model = Patch()

            if right_border_index is not None:
                # 기존 right border 수정
                patched_model["borders"][right_border_index]["children"].append(new_tab)
                patched_model["borders"][right_border_index]["selected"] = len(
                    current_model["borders"][right_border_index]["children"]
                )
            else:
                # right border가 없으면 새로 추가
                patched_model["borders"].append(
                    {"type": "border", "location": "right", "size": 300, "selected": 0, "children": [new_tab]}
                )
            return patched_model, no_update, dff.columns, None

        def _register_find_and_replace_callback(self, app):

            @app.callback(
                Output("flex-layout", "model", allow_duplicate=True),
                Output("toaster", "toasts", allow_duplicate=True),
                Output("find-replace-column-select", "data"),
                Input("find-replace-btn", "n_clicks"),
                State("flex-layout", "model"),
                State("aggrid-table", "columnDefs"),
                prevent_initial_call=True,
            )
            def handle_open_find_replace_modal(n_clicks, current_model, columnDefs):
                if n_clicks is None:
                    raise exceptions.PreventUpdate

                dff = displaying_df()
                if dff is None:
                    return (
                        no_update,
                        [dbpc.Toast(message=f"No Dataframe loaded", intent="warning", icon="warning-sign")],
                        [],
                    )

                columns = [
                    {"label": col["field"], "value": col["field"]} for col in columnDefs if col["field"] != "waiver"
                ]

                right_border_index = next(
                    (i for i, b in enumerate(current_model["borders"]) if b["location"] == "right"), None
                )
                # 이미 col-find_replace-tab 탭이 있는지 확인
                if right_border_index is not None:
                    existing_tabs = current_model["borders"][right_border_index].get("children", [])
                    tab_exists = any(tab.get("id") == "col-find-replace-tab" for tab in existing_tabs)
                    if tab_exists:
                        # 이미 탭이 있다면 해당 탭을 선택하도록 함
                        patched_model = Patch()
                        tab_index = next(
                            i for i, tab in enumerate(existing_tabs) if tab.get("id") == "col-find-replace-tab"
                        )
                        patched_model["borders"][right_border_index]["selected"] = tab_index
                        return patched_model, no_update, columns

                # 새로운 탭 정의
                new_tab = {
                    "type": "tab",
                    "name": "Find & Replace Column",
                    "component": "button",
                    "enableClose": True,
                    "id": "col-find-replace-tab",
                }

                patched_model = Patch()

                if right_border_index is not None:
                    # 기존 right border 수정
                    patched_model["borders"][right_border_index]["children"].append(new_tab)
                    patched_model["borders"][right_border_index]["selected"] = len(
                        current_model["borders"][right_border_index]["children"]
                    )
                else:
                    # right border가 없으면 새로 추가
                    patched_model["borders"].append(
                        {"type": "border", "location": "right", "size": 300, "selected": 0, "children": [new_tab]}
                    )

                return patched_model, no_update, columns

            @app.callback(
                Output("find-replace-regex-checkbox", "disabled"),
                Input("find-replace-column-select", "value"),
                prevent_initial_call=True,
            )
            def handle_toggle_regex_checkbox(selected_column):
                if selected_column is None:
                    raise exceptions.PreventUpdate
                column_dtype = SSDF.dataframe[selected_column].dtype
                return not isinstance(column_dtype, pl.Utf8)

            @app.callback(
                Output("toaster", "toasts", allow_duplicate=True),
                Output("aggrid-table", "columnDefs", allow_duplicate=True),
                Input("find-replace-apply-btn", "n_clicks"),
                State("find-replace-column-select", "value"),
                State("find-replace-find-input", "value"),
                State("find-replace-replace-input", "value"),
                State("find-replace-regex-checkbox", "checked"),
                prevent_initial_call=True,
            )
            def handle_apply_find_replace(n_clicks, column, find_value, replace_value, use_regex):
                if n_clicks is None or not column or find_value is None or replace_value is None:
                    raise exceptions.PreventUpdate
                try:
                    if isinstance(SSDF.dataframe[column].dtype, pl.Utf8):
                        if use_regex:
                            SSDF.dataframe = SSDF.dataframe.with_columns(
                                pl.col(column).str.replace_all(find_value, replace_value).alias(column)
                            )
                        else:
                            SSDF.dataframe = SSDF.dataframe.with_columns(
                                pl.col(column).str.replace(find_value, replace_value).alias(column)
                            )
                    else:
                        # For numeric columns, we use a when-then-otherwise expression
                        SSDF.dataframe = SSDF.dataframe.with_columns(
                            pl.when(pl.col(column) == pl.lit(find_value).cast(SSDF.dataframe[column].dtype))
                            .then(pl.lit(replace_value).cast(SSDF.dataframe[column].dtype))
                            .otherwise(pl.col(column))
                            .alias(column)
                        )

                    updated_columnDefs = generate_column_definitions(SSDF.dataframe)
                    return no_update, updated_columnDefs

                except Exception as e:
                    return [dbpc.Toast(message=f"Error: {str(e)}", intent="danger", icon="error")], no_update

            @app.callback(
                Output("modify-numeric-options", "style"),
                Output("modify-text-options", "style"),
                Input("modify-column-select", "value"),
            )
            def update_modify_options(selected_column):
                if not selected_column:
                    return {"display": "none"}, {"display": "none"}

                column_type = SSDF.dataframe[selected_column].dtype

                if column_type in [pl.Float64, pl.Float32, pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                    return {"display": "block"}, {"display": "none"}
                else:
                    return {"display": "none"}, {"display": "block"}

            @app.callback(
                Output("aggrid-table", "columnDefs", allow_duplicate=True),
                Output("toaster", "toasts", allow_duplicate=True),
                Input("modify-column-apply-btn", "n_clicks"),
                State("modify-column-select", "value"),
                State("modify-filtered-only", "checked"),
                State("modify-numeric-operation", "value"),
                State("modify-numeric-value", "value"),
                State("modify-numeric-inplace", "checked"),
                State("modify-text-find", "value"),
                State("modify-text-replace", "value"),
                State("modify-text-regex", "checked"),
                prevent_initial_call=True,
            )
            def handle_modify_column_submission(
                n_clicks,
                selected_column,
                filtered_only,
                numeric_operation,
                numeric_value,
                numeric_inplace,
                text_find,
                text_replace,
                text_regex,
            ):
                # 연산 함수 정의
                def apply_numeric_operation(col):
                    if numeric_operation == "add":
                        return col + numeric_value
                    elif numeric_operation == "subtract":
                        return col - numeric_value
                    elif numeric_operation == "multiply":
                        return col * numeric_value
                    elif numeric_operation == "divide":
                        if numeric_value == 0:
                            raise ValueError("Cannot divide by zero.")
                        return col / numeric_value
                    elif numeric_operation == "power":
                        return col**numeric_value
                    elif numeric_operation == "round":
                        return col.round(numeric_value)

                    if not n_clicks or not selected_column:
                        return no_update, no_update

                # 원본 데이터프레임 복사
                df_to_modify = SSDF.dataframe.clone()

                # filtered_only가 True인 경우 필터링된 데이터의 uniqid를 가져옴
                if filtered_only:
                    filtered_df = apply_filters(df_to_modify, SSDF.request)
                    filtered_ids = filtered_df["uniqid"]

                column_type = df_to_modify[selected_column].dtype

                # 수치형 컬럼 처리
                if column_type in [pl.Float64, pl.Float32, pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                    if numeric_operation is None or numeric_value is None:
                        raise ValueError("Numeric operation and value must be provided for numeric columns.")

                    if numeric_inplace:
                        new_column_name = selected_column
                    else:
                        new_column_name = f"{selected_column}_{numeric_operation}"

                    # filtered_only에 따라 조건부 수정
                    if filtered_only:
                        modified_values = apply_numeric_operation(df_to_modify[selected_column])
                        df_to_modify = df_to_modify.with_columns(
                            [
                                pl.when(pl.col("uniqid").is_in(filtered_ids))
                                .then(modified_values)
                                .otherwise(pl.col(selected_column))
                                .alias(new_column_name)
                            ]
                        )
                    else:
                        modified_values = apply_numeric_operation(df_to_modify[selected_column])
                        df_to_modify = df_to_modify.with_columns(modified_values.alias(new_column_name))

                # 텍스트형 컬럼 처리
                else:
                    if text_find is None:
                        raise ValueError("Find value must be provided for text columns.")

                    if text_regex:
                        replace_func = lambda x: x.str.replace_all(text_find, text_replace or "")
                    else:
                        replace_func = lambda x: x.str.replace(text_find, text_replace or "", literal=True)

                    # filtered_only에 따라 조건부 수정
                    if filtered_only:
                        modified_values = replace_func(df_to_modify[selected_column])
                        df_to_modify = df_to_modify.with_columns(
                            [
                                pl.when(pl.col("uniqid").is_in(filtered_ids))
                                .then(modified_values)
                                .otherwise(pl.col(selected_column))
                                .alias(selected_column)
                            ]
                        )
                    else:
                        modified_values = replace_func(df_to_modify[selected_column])
                        df_to_modify = df_to_modify.with_columns(modified_values.alias(selected_column))

                # 수정된 데이터프레임을 SSDF에 저장
                SSDF.dataframe = df_to_modify

                updated_columnDefs = generate_column_definitions(SSDF.dataframe)

                return updated_columnDefs, [dbpc.Toast(message=f"Column modified successfully", icon="endorsed")]
