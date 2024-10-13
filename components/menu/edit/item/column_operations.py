import polars as pl
import dash_mantine_components as dmc
from dash import Input, Output, State, Patch, no_update, exceptions
from utils.component_template import create_notification, get_icon
from utils.data_processing import displaying_df
from utils.db_management import SSDF
from components.grid.dag.column_definitions import (
    generate_column_definitions,
    generate_column_definition,
)
from components.grid.dag.server_side_operations import apply_filters


class Columns:
    def layout(self):
        return dmc.Group(
            [
                dmc.Button(
                    "Add Column",
                    id="add-column-btn",
                    leftSection=get_icon("table_column_add"),
                    variant="outline",
                    color="indigo",
                    size="xs",
                ),
                dmc.Button(
                    "Remove Column",
                    id="remove-column-btn",
                    leftSection=get_icon("table_column_delete"),
                    variant="outline",
                    color="indigo",
                    size="xs",
                ),
                dmc.Button(
                    "Concat Column",
                    id="concat-column-btn",
                    leftSection=get_icon("table-merge"),
                    variant="outline",
                    color="indigo",
                    size="xs",
                ),
                dmc.Button(
                    "Edit Column",
                    id="edit-column-btn",
                    variant="outline",
                    color="indigo",
                    size="xs",
                ),
                dmc.Button(
                    "Modify Column",
                    id="modify-column-btn",
                    # leftSection=get_icon("table-merge"),
                    variant="outline",
                    color="indigo",
                    size="xs",
                ),
                self.add_modal(),
                self.remove_modal(),
                self.concat_modal(),
                self.edit_column_modal(),
                self.modify_modal(),
            ],
            gap=2,
        )

    def add_modal(self):
        return dmc.Modal(
            title="Add Column",
            id="add-column-modal",
            children=[
                dmc.Group(
                    [
                        dmc.TextInput(
                            id="add-column-header-input",
                            value="",
                            size="xs",
                            placeholder="header",
                            label="Header",
                            style={"width": 100},
                        ),
                        dmc.TextInput(
                            id="add-column-value-input",
                            size="xs",
                            value="",
                            label="Value:",
                            placeholder="value",
                        ),
                    ],
                    gap="sm",
                ),
                dmc.Space(h=20),
                dmc.Group(
                    [
                        dmc.Button("Submit", id="add-column-submit-btn"),
                    ],
                    justify="flex-end",
                ),
            ],
        )

    def remove_modal(self):
        return dmc.Modal(
            title="Remove Column",
            id="remove-column-modal",
            children=[
                dmc.Group(
                    [
                        dmc.MultiSelect(
                            label="Select Columns to Remove",
                            id="remove-column-multi-select",
                            description="You can select a maximum of 3 Columns.",
                            maxValues=3,
                            value=[],
                            data=[],
                            w=400,
                        ),
                    ],
                    gap="sm",
                ),
                dmc.Space(h=20),
                dmc.Group(
                    [
                        dmc.Button("Submit", id="remove-column-submit-btn"),
                    ],
                    justify="flex-end",
                ),
            ],
        )

    def concat_modal(self):
        return dmc.Modal(
            title="Concat Column",
            id="concat-column-modal",
            children=[
                dmc.Group(
                    [
                        dmc.MultiSelect(
                            label="Select Columns to Concat",
                            id="concat-column-multi-select",
                            description="You can select a maximum of 3 Columns.",
                            maxValues=3,
                            value=[],
                            data=[],
                            w=400,
                        ),
                    ],
                    gap="sm",
                ),
                dmc.Space(h=20),
                dmc.Group(
                    [
                        dmc.Button("Submit", id="concat-column-submit-btn"),
                    ],
                    justify="flex-end",
                ),
            ],
        )

    def edit_column_modal(self):
        return dmc.Modal(
            title="Edit Column",
            id="edit-column-modal",
            children=[
                dmc.Group(
                    [
                        dmc.MultiSelect(
                            label="Select Columns to Edit",
                            id="edit-column-multi-select",
                            description="Waiver Column is not applied here",
                            value=[],
                            data=[],
                            w=400,
                        ),
                    ],
                    gap="sm",
                ),
                dmc.Space(h=20),
                dmc.Group(
                    [
                        dmc.Button("Submit", id="edit-column-submit-btn"),
                    ],
                    justify="flex-end",
                ),
            ],
        )

    def modify_modal(self):
        return dmc.Modal(
            title="Modify Column",
            id="modify-column-modal",
            children=[
                dmc.Group(
                    [
                        dmc.Select(
                            label="Select Column to Modify",
                            id="modify-column-select",
                            value=[],
                            data=[],
                            w=400,
                        ),
                    ],
                    gap="sm",
                ),
                dmc.Space(h=10),
                dmc.Group(
                    [
                        dmc.Checkbox(
                            id="modify-filtered-only",
                            label="filtered data only",
                            checked=True,
                            size="xs",
                        ),
                        dmc.TextInput(
                            id="modify-column-value-input",
                            size="xs",
                            value="",
                            label="modify to",
                        ),
                    ],
                    gap="sm",
                ),
                dmc.Space(h=20),
                dmc.Group(
                    [
                        dmc.Button("Submit", id="modify-column-submit-btn"),
                    ],
                    justify="flex-end",
                ),
            ],
        )

    def rename_modal(self):
        return dmc.Modal(
            title="Rename Column",
            id="rename-column-modal",
            children=[
                dmc.Group(
                    [
                        dmc.Select(
                            label="Select Columns to Rename",
                            id="rename-column-select",
                            clearable=False,
                            data=[],
                            w=200,
                        ),
                        dmc.TextInput(
                            label="New Column Name",
                            id="new-column-name-input",
                            style={"width": 200},
                        ),
                    ],
                    gap="sm",
                ),
                dmc.Space(h=20),
                dmc.Group(
                    [
                        dmc.Button("Submit", id="rename-column-submit-btn"),
                    ],
                    justify="flex-end",
                ),
            ],
        )

    def find_replace_modal(self):
        return dmc.Modal(
            title="Find and Replace",
            id="find-replace-modal",
            children=[
                dmc.Select(
                    label="Select Column",
                    id="find-replace-column-select",
                    data=[],
                    clearable=False,
                    style={"width": 200},
                ),
                dmc.Space(h=10),
                dmc.TextInput(
                    label="Find",
                    id="find-replace-find-input",
                    placeholder="Value to find",
                ),
                dmc.Space(h=10),
                dmc.TextInput(
                    label="Replace",
                    id="find-replace-replace-input",
                    placeholder="Value to replace with",
                ),
                dmc.Space(h=10),
                dmc.Checkbox(
                    label="Use Regular Expression (for string columns)",
                    id="find-replace-regex-checkbox",
                ),
                dmc.Space(h=20),
                dmc.Group(
                    [
                        dmc.Button("Apply", id="find-replace-apply-btn"),
                    ],
                    justify="flex-end",
                ),
            ],
        )

    def register_callbacks(self, app):

        @app.callback(
            Output("rename-column-modal", "opened"),
            Output("rename-column-select", "data"),
            Input("rename-column-btn", "n_clicks"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True,
        )
        def open_rename_column_modal(n_clicks, columnDefs):
            columns = [col["field"] for col in columnDefs if col["field"] != "waiver"]
            return True, columns

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Output("rename-column-modal", "opened", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("rename-column-submit-btn", "n_clicks"),
            State("rename-column-select", "value"),
            State("new-column-name-input", "value"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True,
        )
        def rename_column(n_clicks, old_name, new_name, columnDefs):
            if new_name in [col["field"] for col in columnDefs]:
                return (
                    create_notification(
                        message="Column name already exists", position="center"
                    ),
                    True,
                    no_update,
                )
            try:
                SSDF.dataframe = SSDF.dataframe.rename({old_name: new_name})
                patched_columnDefs = Patch()
                for i, columnDef in enumerate(columnDefs):
                    if columnDef["field"] == old_name:
                        patched_columnDefs[i] = generate_column_definition(
                            new_name, SSDF.dataframe[new_name]
                        )
                return None, False, patched_columnDefs
            except Exception as e:
                return create_notification(str(e)), no_update, no_update

        @app.callback(
            Output("find-replace-modal", "opened"),
            Output("find-replace-column-select", "data"),
            Input("find-replace-btn", "n_clicks"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True,
        )
        def open_find_replace_modal(n_clicks, columnDefs):
            columns = [
                {"label": col["field"], "value": col["field"]}
                for col in columnDefs
                if col["field"] != "waiver"
            ]
            return True, columns

        @app.callback(
            Output("find-replace-regex-checkbox", "disabled"),
            Input("find-replace-column-select", "value"),
        )
        def toggle_regex_checkbox(selected_column):
            if selected_column is None:
                raise exceptions.PreventUpdate
            column_dtype = SSDF.dataframe[selected_column].dtype
            return not isinstance(column_dtype, pl.Utf8)

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Output("find-replace-modal", "opened", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("find-replace-apply-btn", "n_clicks"),
            State("find-replace-column-select", "value"),
            State("find-replace-find-input", "value"),
            State("find-replace-replace-input", "value"),
            State("find-replace-regex-checkbox", "checked"),
            prevent_initial_call=True,
        )
        def apply_find_replace(n_clicks, column, find_value, replace_value, use_regex):
            if (
                n_clicks is None
                or not column
                or find_value is None
                or replace_value is None
            ):
                raise exceptions.PreventUpdate
            try:
                if isinstance(SSDF.dataframe[column].dtype, pl.Utf8):
                    SSDF.dataframe = (
                        SSDF.dataframe.with_columns(
                            pl.col(column)
                            .str.replace_all(find_value, replace_value)
                            .alias(column)
                        )
                        if use_regex
                        else SSDF.dataframe.with_columns(
                            pl.col(column)
                            .str.replace(find_value, replace_value)
                            .alias(column)
                        )
                    )
                else:
                    SSDF.dataframe = SSDF.dataframe.with_columns(
                        pl.when(
                            pl.col(column)
                            == pl.lit(find_value).cast(SSDF.dataframe[column].dtype)
                        )
                        .then(pl.lit(replace_value).cast(SSDF.dataframe[column].dtype))
                        .otherwise(pl.col(column))
                        .alias(column)
                    )
                updated_columnDefs = generate_column_definitions(SSDF.dataframe)
                return None, False, updated_columnDefs
            except Exception as e:
                return create_notification(str(e)), no_update, no_update

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Output("modify-column-modal", "opened", allow_duplicate=True),
            Output("modify-column-select", "data"),
            Output("modify-column-select", "value"),
            Input("modify-column-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def modify_column_modal_open(n):
            if n is None:
                raise exceptions.PreventUpdate
            dff = displaying_df()
            if dff is None:
                return (
                    create_notification(
                        message="No Dataframe loaded", position="center"
                    ),
                    False,
                    [],
                    None,
                )
            return None, True, dff.columns, None

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Output("modify-column-modal", "opened", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("modify-column-submit-btn", "n_clicks"),
            State("modify-column-select", "value"),
            State("modify-column-value-input", "value"),
            State("modify-filtered-only", "checked"),
            prevent_initial_call=True,
        )
        def modify_column(n, selected_column, update_val, filtered_only):
            if n is None:
                raise exceptions.PreventUpdate
            if not selected_column:
                return (
                    create_notification(
                        message="No columns selected", position="center"
                    ),
                    no_update,
                    no_update,
                )

            dff = SSDF.dataframe
            if filtered_only:
                dff = apply_filters(dff, SSDF.request)

            # 기존 'col1' 컬럼의 데이터 타입 저장
            original_dtype = dff.schema[selected_column]

            dff = dff.with_columns(pl.lit(update_val).alias(selected_column))

            # 'col1' 컬럼을 원래 데이터 타입으로 캐스팅
            dff = dff.with_columns(pl.col(selected_column).cast(original_dtype))

            # 'id' 컬럼을 기준으로 filtered_df와 df를 결합
            updated_df = SSDF.dataframe.join(
                dff, on="uniqid", how="left", suffix="_filtered"
            )

            # 'col1' 컬럼을 filtered_df의 값으로 업데이트
            updated_df = updated_df.with_columns(
                pl.when(pl.col(f"{selected_column}_filtered").is_not_null())
                .then(pl.col(f"{selected_column}_filtered"))
                .otherwise(pl.col(selected_column))
                .alias(selected_column)
            )
            # '_filtered' 접미사가 있는 모든 컬럼 삭제
            columns_to_drop = [
                col for col in updated_df.columns if col.endswith("_filtered")
            ]
            SSDF.dataframe = updated_df.drop(columns_to_drop)

            updated_columnDefs = generate_column_definitions(SSDF.dataframe)

            return None, False, updated_columnDefs

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Output("remove-column-modal", "opened", allow_duplicate=True),
            Output("remove-column-multi-select", "data"),
            Output("remove-column-multi-select", "value"),
            Input("remove-column-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def remove_column_modal_open(n):
            if n is None:
                raise exceptions.PreventUpdate
            dff = displaying_df()
            if dff is None:
                return (
                    create_notification(
                        message="No Dataframe loaded", position="center"
                    ),
                    False,
                    [],
                    [],
                )
            return None, True, dff.columns, []

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Output("remove-column-modal", "opened", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("remove-column-submit-btn", "n_clicks"),
            State("remove-column-multi-select", "value"),
            prevent_initial_call=True,
        )
        def remove_column(n, selected_columns):
            if n is None:
                raise exceptions.PreventUpdate
            if not selected_columns:
                return (
                    create_notification(
                        message="No columns selected", position="center"
                    ),
                    no_update,
                    no_update,
                )

            SSDF.dataframe = SSDF.dataframe.drop(selected_columns)
            updated_columnDefs = generate_column_definitions(SSDF.dataframe)

            return None, False, updated_columnDefs

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Output("add-column-modal", "opened", allow_duplicate=True),
            Input("add-column-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def add_column_modal_open(n):
            if n is None:
                raise exceptions.PreventUpdate
            dff = displaying_df()
            if dff is None:
                return (
                    create_notification(
                        message="No Dataframe loaded", position="center"
                    ),
                    False,
                )
            return None, True

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Output("add-column-modal", "opened", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("add-column-submit-btn", "n_clicks"),
            State("add-column-header-input", "value"),
            State("add-column-value-input", "value"),
            prevent_initial_call=True,
        )
        def add_column(n, add_column_header, add_column_value):
            if n is None:
                raise exceptions.PreventUpdate
            if not add_column_header:
                noti = create_notification(
                    message="No header name given", position="center"
                )
                return noti, no_update, no_update
            if not add_column_header:
                noti = create_notification(
                    message="No column value given", position="center"
                )
                return noti, no_update, no_update

            if add_column_header in SSDF.dataframe.columns:
                noti = create_notification(
                    message="Header name exsists in data", position="center"
                )
                return noti, no_update, no_update
            SSDF.dataframe = SSDF.dataframe.with_columns(
                pl.lit(add_column_value).alias(add_column_header)
            )
            updated_columnDefs = generate_column_definitions(SSDF.dataframe)
            return None, False, updated_columnDefs

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Output("concat-column-modal", "opened", allow_duplicate=True),
            Output("concat-column-multi-select", "data"),
            Input("concat-column-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def concat_column_modal_open(n):
            if n is None:
                raise exceptions.PreventUpdate
            dff = displaying_df()
            if dff is None:
                return (
                    create_notification(
                        message="No Dataframe loaded", position="center"
                    ),
                    False,
                    [],
                )
            return None, True, dff.columns

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Output("concat-column-modal", "opened", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("concat-column-submit-btn", "n_clicks"),
            State("concat-column-multi-select", "value"),
            prevent_initial_call=True,
        )
        def concat_column(n, selected_columns):
            if n is None:
                raise exceptions.PreventUpdate
            if not selected_columns or len(selected_columns) < 2:
                noti = create_notification(
                    message="Select more than 2 columns", position="center"
                )
                return noti, no_update, no_update
            header_name = "-".join(selected_columns)

            SSDF.dataframe = SSDF.dataframe.with_columns(
                pl.concat_str(
                    [pl.col(col) for col in selected_columns], separator="-"
                ).alias(header_name)
            )
            updated_columnDefs = generate_column_definitions(SSDF.dataframe)
            return None, False, updated_columnDefs

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Output("edit-column-modal", "opened", allow_duplicate=True),
            Output("edit-column-multi-select", "data"),
            Output("edit-column-multi-select", "value"),
            Input("edit-column-btn", "n_clicks"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True,
        )
        def edit_column_modal_open(n, current_columnDefs):
            if n is None:
                raise exceptions.PreventUpdate
            dff = displaying_df()
            if dff is None:
                return (
                    create_notification(
                        message="No Dataframe loaded", position="center"
                    ),
                    False,
                    [],
                    [],
                )
            return (
                None,
                True,
                [col for col in dff.columns if col != "waiver"],
                [
                    col_def["field"]
                    for col_def in current_columnDefs
                    if col_def["editable"]
                ],
            )

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Output("edit-column-modal", "opened", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("edit-column-submit-btn", "n_clicks"),
            State("edit-column-multi-select", "value"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True,
        )
        def edit_column(n, selected_columns, current_columnDefs):
            if n is None:
                raise exceptions.PreventUpdate
            if not selected_columns:
                return (
                    create_notification(
                        message="No columns selected", position="center"
                    ),
                    no_update,
                    no_update,
                )

            patched_columnDefs = Patch()

            for i, columnDef in enumerate(current_columnDefs):

                col = columnDef["field"]
                if col == "waiver":
                    continue
                elif col in selected_columns:
                    patched_columnDefs[i] = generate_column_definition(
                        col, SSDF.dataframe[col], is_editable=True
                    )
                else:
                    patched_columnDefs[i] = generate_column_definition(
                        col, SSDF.dataframe[col], is_editable=False
                    )

            return None, False, patched_columnDefs
