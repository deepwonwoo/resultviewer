import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Input, Output, State, Patch, no_update, exceptions, html
from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import (
    generate_column_definitions,
    generate_column_definition,
)
from components.grid.dag.server_side_operations import apply_filters


class Columns:

    def layout(self):
        return dmc.Group(
            [
                dbpc.Divider(),
                dbpc.Button(
                    "Add Column",
                    id="add-column-btn",
                    icon="add-column-left",
                    minimal=True,
                    outlined=True,
                ),
                dbpc.Button(
                    "Remove Column",
                    id="remove-column-btn",
                    icon="remove-column",
                    minimal=True,
                    outlined=True,
                ),
                dbpc.Button(
                    "Concat Column",
                    id="concat-column-btn",
                    icon="merge-columns",
                    minimal=True,
                    outlined=True,
                ),
                dbpc.Button(
                    "Edit Column",
                    id="edit-column-btn",
                    icon="edit",
                    minimal=True,
                    outlined=True,
                ),
                dbpc.Button(
                    "Modify Column",
                    id="modify-column-btn",
                    icon="derive-column",
                    minimal=True,
                    outlined=True,
                ),
                dbpc.Button(
                    "Rename Column",
                    id="rename-column-btn",
                    icon="text-highlight",
                    minimal=True,
                    outlined=True,
                ),
                dbpc.Button(
                    "Find & Replace",
                    id="find-replace-btn",
                    icon="exchange",
                    minimal=True,
                    outlined=True,
                ),
                dbpc.Button(
                    "Count Hier",
                    id="hier-count-btn",
                    icon="align-left",
                    minimal=True,
                    outlined=True,
                ),
            ],
            gap=2,
        )

    def add_tab(self):
        return dmc.Paper(
            children=[
                dmc.Group(
                    [
                        dbpc.EntityTitle(
                            title="Add Column", heading="H5", icon="add-column-left"
                        )
                    ],
                    grow=True,
                ),
                dmc.Space(h=10),
                dmc.Stack(
                    [
                        dmc.SegmentedControl(
                            id="add-column-value-type",
                            data=[
                                {"label": "Default Value", "value": "default"},
                                {"label": "Copy Column", "value": "copy"},
                            ],
                            value="default",
                        ),
                        dmc.TextInput(
                            id="add-column-header-input",
                            value="",
                            size="xs",
                            placeholder="header",
                            label="Header",
                        ),
                        dmc.TextInput(
                            id="add-column-value-input",
                            size="xs",
                            value="",
                            label="Default Value:",
                            placeholder="value",
                        ),
                        dmc.Select(
                            id="add-column-copy-select",
                            label="Copy from Column:",
                            size="xs",
                            data=[],
                            clearable=False,
                            disabled=True,
                        ),
                    ],
                    justify="space-around",
                    align="stretch",
                ),
                dmc.Space(h=10),
                dbpc.Button(
                    "Apply",
                    id="add-column-apply-btn",
                    intent="primary",
                    outlined=True,
                    minimal=True,
                    fill=True,
                ),
            ],
            p="md",
            shadow="sm",
            radius="xs",
            withBorder=True,
        )

    def remove_tab(self):
        return dmc.Paper(
            children=[
                dmc.Group(
                    [
                        dbpc.EntityTitle(
                            title="Remove Column", heading="H5", icon="remove-column"
                        )
                    ],
                    grow=True,
                ),
                dmc.Space(h=10),
                dmc.Stack(
                    [
                        dmc.MultiSelect(
                            label="Select Columns to Remove",
                            id="remove-column-multi-select",
                            size="xs",
                            data=[],
                        )
                    ],
                    justify="space-around",
                    align="stretch",
                    gap="lg",
                ),
                dmc.Space(h=10),
                dbpc.Popover(
                    id="remove-popover",
                    children=dbpc.Button(
                        "Apply", intent="danger", outlined=True, minimal=True, fill=True
                    ),
                    content=html.Div(
                        children=[
                            html.Div("Confirm deletion", className="bp5-heading"),
                            html.P(
                                "Are you sure you want to delete these items? You won't be able to recover them."
                            ),
                            html.Div(
                                children=[
                                    dbpc.Button(
                                        children="Cancel", style={"margin-right": 10}
                                    ),
                                    dbpc.Button(
                                        children="Delete",
                                        id="remove-column-apply-btn",
                                        intent="danger",
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "justify-content": "flex-end",
                                    "margin-top": 15,
                                },
                            ),
                        ],
                        style={"padding": "20px"},
                    ),
                ),
            ],
            p="md",
            shadow="sm",
            radius="xs",
            withBorder=True,
        )

    def concat_tab(self):
        return dmc.Paper(
            children=[
                dmc.Group(
                    [
                        dbpc.EntityTitle(
                            title="Concat Column", heading="H5", icon="merge-columns"
                        )
                    ],
                    grow=True,
                ),
                dmc.Space(h=10),
                dmc.Stack(
                    [
                        dmc.MultiSelect(
                            label="Select Columns to Concat",
                            id="concat-column-multi-select",
                            value=[],
                            data=[],
                            size="xs",
                        ),
                        dmc.TextInput(
                            label="Demiliter",
                            value="-",
                            id="concat-delimiter-input",
                            placeholder="Enter delimiter",
                        ),
                    ],
                    justify="space-around",
                    align="stretch",
                    gap="lg",
                ),
                dmc.Space(h=10),
                dbpc.Button(
                    "Apply",
                    id="concat-column-apply-btn",
                    intent="primary",
                    outlined=True,
                    minimal=True,
                    fill=True,
                ),
            ],
            p="md",
            shadow="sm",
            radius="xs",
            withBorder=True,
        )

    def edit_tab(self):
        return dmc.Paper(
            children=[
                dmc.Group(
                    [dbpc.EntityTitle(title="Edit Column", heading="H5", icon="edit")],
                    grow=True,
                ),
                dmc.Space(h=10),
                dmc.Stack(
                    [
                        dmc.MultiSelect(
                            label="Select Columns to Edit",
                            id="edit-column-multi-select",
                            description="Waiver Column is not applied here",
                            hidePickedOptions=True,
                            searchable=True,
                            clearable=True,
                            value=[],
                            data=[],
                        )
                    ],
                    justify="space-around",
                    align="stretch",
                    gap="lg",
                ),
            ],
            p="md",
            shadow="sm",
            radius="xs",
            withBorder=True,
        )

    def modify_tab(self):
        return dmc.Paper(
            children=[
                dmc.Group(
                    [
                        dbpc.EntityTitle(
                            title="Modify Column", heading="H5", icon="derive-column"
                        )
                    ],
                    grow=True,
                ),
                dmc.Space(h=10),
                dmc.Stack(
                    children=[
                        dmc.Select(
                            id="modify-column-select",
                            label="Select Column to Modify",
                            data=[],
                        ),
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
                                dmc.NumberInput(
                                    label="Value", id="modify-numeric-value", mb=10
                                ),
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
                                dmc.TextInput(
                                    label="Find", id="modify-text-find", mb=10
                                ),
                                dmc.TextInput(
                                    label="Replace with",
                                    id="modify-text-replace",
                                    mb=10,
                                ),
                                dmc.Checkbox(
                                    id="modify-text-regex",
                                    label="Use regular expression",
                                    checked=False,
                                    mb=20,
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
                    id="modify-filtered-only",
                    label="Apply to filtered data only",
                    checked=True,
                    size="sm",
                    mb=10,
                ),
                dbpc.Button(
                    "Apply",
                    id="modify-column-apply-btn",
                    intent="primary",
                    outlined=True,
                    minimal=True,
                    fill=True,
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
                dmc.Group(
                    [
                        dbpc.EntityTitle(
                            title="Find & Replace", heading="H5", icon="exchange"
                        )
                    ],
                    grow=True,
                ),
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
                        dmc.TextInput(
                            label="Find",
                            id="find-replace-find-input",
                            placeholder="Value to find",
                        ),
                        dmc.TextInput(
                            label="Replace",
                            id="find-replace-replace-input",
                            placeholder="Value to replace with",
                        ),
                        dmc.Checkbox(
                            label="Use Regular Expression (for string columns)",
                            id="find-replace-regex-checkbox",
                        ),
                    ],
                    justify="space-around",
                    align="stretch",
                    gap="lg",
                ),
                dmc.Space(h=10),
                dbpc.Button(
                    "Apply",
                    id="find-replace-apply-btn",
                    intent="primary",
                    outlined=True,
                    minimal=True,
                    fill=True,
                ),
            ],
            p="md",
            shadow="sm",
            radius="xs",
            withBorder=True,
        )

    def rename_tab(self):
        return dmc.Paper(
            children=[
                dmc.Group(
                    [
                        dbpc.EntityTitle(
                            title="Rename Column", heading="H5", icon="text-highlight"
                        )
                    ],
                    grow=True,
                ),
                dmc.Stack(
                    children=[
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
                    justify="space-around",
                    align="stretch",
                    gap="lg",
                ),
                dmc.Space(h=10),
                dbpc.Button(
                    "Apply",
                    id="rename-column-apply-btn",
                    intent="primary",
                    outlined=True,
                    minimal=True,
                    fill=True,
                ),
            ],
            p="md",
            shadow="sm",
            radius="xs",
            withBorder=True,
        )

    def hier_count_tab(self):
        return dmc.Paper(
            children=[
                dmc.Group(
                    [
                        dbpc.EntityTitle(
                            title="Hierarchy Level Count",
                            heading="H5",
                            icon="align-left",
                        )
                    ],
                    grow=True,
                ),
                dmc.Space(h=10),
                dmc.Stack(
                    children=[
                        dmc.Select(
                            label="Select Column",
                            id="hier-count-column-select",
                            data=[],
                        ),
                        dmc.Select(
                            label="Hierarchy Delimiter",
                            id="hier-count-delimiter-input",
                            data=[".", "/"],
                            value=".",
                        ),
                    ],
                    justify="space-around",
                    align="stretch",
                    gap="lg",
                ),
                dmc.Space(h=10),
                dbpc.Button(
                    "Apply",
                    id="hier-count-apply-btn",
                    intent="primary",
                    outlined=True,
                    minimal=True,
                    fill=True,
                ),
            ],
            p="md",
            shadow="sm",
            radius="xs",
            withBorder=True,
        )

    def register_callbacks(self, app):
        self._register_add_column_callback(app)
        self._register_remove_column_callback(app)
        self._register_concat_column_callback(app)
        self._register_edit_column_callback(app)
        self._register_modify_column_callback(app)
        self._register_rename_column_callback(app)
        self._register_find_and_replace_callback(app)
        self._register_hier_count_callback(app)

    def _register_add_column_callback(self, app):

        @app.callback(
            Output("flex-layout", "model", allow_duplicate=True),
            Output("toaster", "toasts", allow_duplicate=True),
            Input("add-column-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True,
        )
        def handle_add_column_button_click(n_clicks, current_model):
            if n_clicks is None:
                raise exceptions.PreventUpdate

            dff = displaying_df()
            if dff is None:
                return no_update, [
                    dbpc.Toast(
                        message=f"No Dataframe loaded",
                        intent="warning",
                        icon="warning-sign",
                    )
                ]

            right_border_index = next(
                (
                    i
                    for i, b in enumerate(current_model["borders"])
                    if b["location"] == "right"
                ),
                None,
            )
            if right_border_index is not None:
                existing_tabs = current_model["borders"][right_border_index].get(
                    "children", []
                )
                tab_exists = any(
                    tab.get("id") == "col-add-tab" for tab in existing_tabs
                )
                if tab_exists:
                    patched_model = Patch()
                    tab_index = next(
                        i
                        for i, tab in enumerate(existing_tabs)
                        if tab.get("id") == "col-add-tab"
                    )
                    patched_model["borders"][right_border_index]["selected"] = tab_index
                    return patched_model, no_update

            new_tab = {
                "type": "tab",
                "name": "Add Column",
                "component": "button",
                "enableClose": True,
                "id": "col-add-tab",
            }

            patched_model = Patch()

            if right_border_index is not None:
                patched_model["borders"][right_border_index]["children"].append(new_tab)
                patched_model["borders"][right_border_index]["selected"] = len(
                    current_model["borders"][right_border_index]["children"]
                )
            else:
                patched_model["borders"].append(
                    {
                        "type": "border",
                        "location": "right",
                        "size": 300,
                        "selected": 0,
                        "children": [new_tab],
                    }
                )
            return patched_model, no_update

        @app.callback(
            Output("add-column-value-input", "disabled"),
            Output("add-column-copy-select", "disabled"),
            Output("add-column-copy-select", "data"),
            Input("add-column-value-type", "value"),
            State("aggrid-table", "columnDefs"),
        )
        def handle_value_type_change(value_type, columnDefs):
            column_data = [
                {"label": col["field"], "value": col["field"]}
                for col in columnDefs
                if col["field"] != "waiver"
            ]
            if value_type == "default":
                return False, True, column_data
            else:
                return True, False, column_data

        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("add-column-header-input", "value"),
            Output("add-column-value-input", "value"),
            Input("add-column-apply-btn", "n_clicks"),
            State("add-column-value-type", "value"),
            State("add-column-header-input", "value"),
            State("add-column-value-input", "value"),
            State("add-column-copy-select", "value"),
            prevent_initial_call=True,
        )
        def handle_add_column_submission(
            n1, mode, add_column_header, add_column_value, copy_select_val
        ):

            if not add_column_header:
                return (
                    [
                        dbpc.Toast(
                            message=f"No header name given",
                            intent="warning",
                            icon="warning-sign",
                        )
                    ],
                    no_update,
                    no_update,
                    no_update,
                )

            if add_column_header in SSDF.dataframe.columns:
                return (
                    [
                        dbpc.Toast(
                            message=f"Header name already exists in data",
                            intent="warning",
                            icon="warning-sign",
                        )
                    ],
                    no_update,
                    no_update,
                    no_update,
                )

            if mode == "copy" and not copy_select_val:
                return (
                    [
                        dbpc.Toast(
                            message=f"No source column selected",
                            intent="warning",
                            icon="warning-sign",
                        )
                    ],
                    no_update,
                    no_update,
                    no_update,
                )

            try:
                if mode == "default":
                    if add_column_value.isdigit():
                        new_column = pl.Series(
                            add_column_header,
                            [int(add_column_value)] * len(SSDF.dataframe),
                        )
                    elif add_column_value.replace(".", "", 1).isdigit():
                        new_column = pl.Series(
                            add_column_header,
                            [float(add_column_value)] * len(SSDF.dataframe),
                        )
                    elif add_column_value is None:
                        new_column = pl.Series(
                            add_column_header, [str("")] * len(SSDF.dataframe)
                        )
                    else:
                        new_column = pl.Series(
                            add_column_header,
                            [str(add_column_value)] * len(SSDF.dataframe),
                        )
                    SSDF.dataframe = SSDF.dataframe.with_columns([new_column])

                else:
                    SSDF.dataframe = SSDF.dataframe.with_columns(
                        pl.col(copy_select_val).alias(add_column_header)
                    )

                updated_columnDefs = generate_column_definitions(SSDF.dataframe)
                return no_update, updated_columnDefs, "", ""

            except Exception as e:
                return (
                    [dbpc.Toast(message=f"{str(e)}", intent="danger", icon="error")],
                    no_update,
                    no_update,
                    no_update,
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
                    [
                        dbpc.Toast(
                            message=f"No Dataframe loaded",
                            intent="warning",
                            icon="warning-sign",
                        )
                    ],
                    [],
                    [],
                )
            right_border_index = next(
                (
                    i
                    for i, b in enumerate(current_model["borders"])
                    if b["location"] == "right"
                ),
                None,
            )
            # 이미 col-modify-tab 탭이 있는지 확인
            if right_border_index is not None:
                existing_tabs = current_model["borders"][right_border_index].get(
                    "children", []
                )
                tab_exists = any(
                    tab.get("id") == "col-modify-tab" for tab in existing_tabs
                )
                if tab_exists:
                    # 이미 탭이 있다면 해당 탭을 선택하도록 함
                    patched_model = Patch()
                    tab_index = next(
                        i
                        for i, tab in enumerate(existing_tabs)
                        if tab.get("id") == "col-modify-tab"
                    )
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
                    {
                        "type": "border",
                        "location": "right",
                        "size": 300,
                        "selected": 0,
                        "children": [new_tab],
                    }
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
                        [
                            dbpc.Toast(
                                message=f"No Dataframe loaded",
                                intent="warning",
                                icon="warning-sign",
                            )
                        ],
                        [],
                    )

                columns = [
                    {"label": col["field"], "value": col["field"]}
                    for col in columnDefs
                    if col["field"] != "waiver"
                ]

                right_border_index = next(
                    (
                        i
                        for i, b in enumerate(current_model["borders"])
                        if b["location"] == "right"
                    ),
                    None,
                )
                # 이미 col-find_replace-tab 탭이 있는지 확인
                if right_border_index is not None:
                    existing_tabs = current_model["borders"][right_border_index].get(
                        "children", []
                    )
                    tab_exists = any(
                        tab.get("id") == "col-find-replace-tab" for tab in existing_tabs
                    )
                    if tab_exists:
                        # 이미 탭이 있다면 해당 탭을 선택하도록 함
                        patched_model = Patch()
                        tab_index = next(
                            i
                            for i, tab in enumerate(existing_tabs)
                            if tab.get("id") == "col-find-replace-tab"
                        )
                        patched_model["borders"][right_border_index][
                            "selected"
                        ] = tab_index
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
                    patched_model["borders"][right_border_index]["children"].append(
                        new_tab
                    )
                    patched_model["borders"][right_border_index]["selected"] = len(
                        current_model["borders"][right_border_index]["children"]
                    )
                else:
                    # right border가 없으면 새로 추가
                    patched_model["borders"].append(
                        {
                            "type": "border",
                            "location": "right",
                            "size": 300,
                            "selected": 0,
                            "children": [new_tab],
                        }
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
            def handle_apply_find_replace(
                n_clicks, column, find_value, replace_value, use_regex
            ):
                if (
                    n_clicks is None
                    or not column
                    or find_value is None
                    or replace_value is None
                ):
                    raise exceptions.PreventUpdate
                try:
                    if isinstance(SSDF.dataframe[column].dtype, pl.Utf8):
                        if use_regex:
                            SSDF.dataframe = SSDF.dataframe.with_columns(
                                pl.col(column)
                                .str.replace_all(find_value, replace_value)
                                .alias(column)
                            )
                        else:
                            SSDF.dataframe = SSDF.dataframe.with_columns(
                                pl.col(column)
                                .str.replace(find_value, replace_value)
                                .alias(column)
                            )
                    else:
                        # For numeric columns, we use a when-then-otherwise expression
                        SSDF.dataframe = SSDF.dataframe.with_columns(
                            pl.when(
                                pl.col(column)
                                == pl.lit(find_value).cast(SSDF.dataframe[column].dtype)
                            )
                            .then(
                                pl.lit(replace_value).cast(SSDF.dataframe[column].dtype)
                            )
                            .otherwise(pl.col(column))
                            .alias(column)
                        )

                    updated_columnDefs = generate_column_definitions(SSDF.dataframe)
                    return no_update, updated_columnDefs

                except Exception as e:
                    return [
                        dbpc.Toast(
                            message=f"Error: {str(e)}", intent="danger", icon="error"
                        )
                    ], no_update

            @app.callback(
                Output("modify-numeric-options", "style"),
                Output("modify-text-options", "style"),
                Input("modify-column-select", "value"),
            )
            def update_modify_options(selected_column):
                if not selected_column:
                    return {"display": "none"}, {"display": "none"}

                column_type = SSDF.dataframe[selected_column].dtype

                if column_type in [
                    pl.Float64,
                    pl.Float32,
                    pl.Int64,
                    pl.Int32,
                    pl.UInt32,
                    pl.UInt64,
                ]:
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
                if column_type in [
                    pl.Float64,
                    pl.Float32,
                    pl.Int64,
                    pl.Int32,
                    pl.UInt32,
                    pl.UInt64,
                ]:
                    if numeric_operation is None or numeric_value is None:
                        raise ValueError(
                            "Numeric operation and value must be provided for numeric columns."
                        )

                    if numeric_inplace:
                        new_column_name = selected_column
                    else:
                        new_column_name = f"{selected_column}_{numeric_operation}"

                    # filtered_only에 따라 조건부 수정
                    if filtered_only:
                        modified_values = apply_numeric_operation(
                            df_to_modify[selected_column]
                        )
                        df_to_modify = df_to_modify.with_columns(
                            [
                                pl.when(pl.col("uniqid").is_in(filtered_ids))
                                .then(modified_values)
                                .otherwise(pl.col(selected_column))
                                .alias(new_column_name)
                            ]
                        )
                    else:
                        modified_values = apply_numeric_operation(
                            df_to_modify[selected_column]
                        )
                        df_to_modify = df_to_modify.with_columns(
                            modified_values.alias(new_column_name)
                        )

                # 텍스트형 컬럼 처리
                else:
                    if text_find is None:
                        raise ValueError(
                            "Find value must be provided for text columns."
                        )

                    if text_regex:
                        replace_func = lambda x: x.str.replace_all(
                            text_find, text_replace or ""
                        )
                    else:
                        replace_func = lambda x: x.str.replace(
                            text_find, text_replace or "", literal=True
                        )

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
                        df_to_modify = df_to_modify.with_columns(
                            modified_values.alias(selected_column)
                        )

                # 수정된 데이터프레임을 SSDF에 저장
                SSDF.dataframe = df_to_modify

                updated_columnDefs = generate_column_definitions(SSDF.dataframe)

                return updated_columnDefs, [
                    dbpc.Toast(message=f"Column modified successfully", icon="endorsed")
                ]

    def _register_concat_column_callback(self, app):
        @app.callback(
            Output("flex-layout", "model", allow_duplicate=True),
            Output("toaster", "toasts", allow_duplicate=True),
            Output("concat-column-multi-select", "data"),
            Input("concat-column-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True,
        )
        def handle_concat_column_button_click(n_clicks, current_model):
            if n_clicks is None:
                raise exceptions.PreventUpdate
            dff = displaying_df()
            if dff is None:
                return (
                    no_update,
                    [
                        dbpc.Toast(
                            message=f"No Dataframe loaded",
                            intent="warning",
                            icon="warning-sign",
                        )
                    ],
                    [],
                )
            right_border_index = next(
                (
                    i
                    for i, b in enumerate(current_model["borders"])
                    if b["location"] == "right"
                ),
                None,
            )
            if right_border_index is not None:
                existing_tabs = current_model["borders"][right_border_index].get(
                    "children", []
                )
                tab_exists = any(
                    tab.get("id") == "col-concat-tab" for tab in existing_tabs
                )
                if tab_exists:
                    patched_model = Patch()
                    tab_index = next(
                        i
                        for i, tab in enumerate(existing_tabs)
                        if tab.get("id") == "col-concat-tab"
                    )
                    patched_model["borders"][right_border_index]["selected"] = tab_index
                    return patched_model, no_update, no_update
            new_tab = {
                "type": "tab",
                "name": "Concat Column",
                "component": "button",
                "enableClose": True,
                "id": "col-concat-tab",
            }
            patched_model = Patch()
            if right_border_index is not None:
                patched_model["borders"][right_border_index]["children"].append(new_tab)
                patched_model["borders"][right_border_index]["selected"] = len(
                    current_model["borders"][right_border_index]["children"]
                )
            else:
                patched_model["borders"].append(
                    {
                        "type": "border",
                        "location": "right",
                        "size": 300,
                        "selected": 0,
                        "children": [new_tab],
                    }
                )
            return patched_model, no_update, dff.columns

        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("concat-column-multi-select", "data", allow_duplicate=True),
            Output("concat-column-multi-select", "value"),
            Input("concat-column-apply-btn", "n_clicks"),
            State("concat-column-multi-select", "value"),
            State("concat-delimiter-input", "value"),
            prevent_initial_call=True,
        )
        def handle_concat_column_submission(n, selected_columns, delimiter):
            if n is None:
                raise exceptions.PreventUpdate
            if not selected_columns or len(selected_columns) < 2:
                return (
                    [
                        dbpc.Toast(
                            message=f"Select at least 2 columns",
                            intent="warning",
                            icon="warning-sign",
                        )
                    ],
                    no_update,
                    no_update,
                    no_update,
                )
            if not delimiter:
                return (
                    [
                        dbpc.Toast(
                            message=f"No delimiter given",
                            intent="warning",
                            icon="warning-sign",
                        )
                    ],
                    no_update,
                    no_update,
                    no_update,
                )
            try:
                delimiter = delimiter if delimiter else "-"
                header_name = delimiter.join(selected_columns)
                SSDF.dataframe = SSDF.dataframe.with_columns(
                    pl.concat_str(
                        [pl.col(col).cast(pl.Utf8) for col in selected_columns],
                        separator=delimiter,
                    ).alias(header_name)
                )
                updated_columnDefs = generate_column_definitions(SSDF.dataframe)
                return no_update, updated_columnDefs, SSDF.dataframe.columns, []
            except Exception as e:
                return (
                    [dbpc.Toast(message=f"{str(e)}", intent="danger", icon="error")],
                    no_update,
                    no_update,
                    no_update,
                )

    def _register_remove_column_callback(self, app):
        @app.callback(
            Output("flex-layout", "model", allow_duplicate=True),
            Output("toaster", "toasts", allow_duplicate=True),
            Output("remove-column-multi-select", "data", allow_duplicate=True),
            Input("remove-column-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True,
        )
        def handle_remove_column_button_click(n_clicks, current_model):
            if n_clicks is None:
                raise exceptions.PreventUpdate

            dff = displaying_df()
            if dff is None:
                return (
                    no_update,
                    [
                        dbpc.Toast(
                            message=f"No Dataframe loaded",
                            intent="warning",
                            icon="warning-sign",
                        )
                    ],
                    [],
                )

            right_border_index = next(
                (
                    i
                    for i, b in enumerate(current_model["borders"])
                    if b["location"] == "right"
                ),
                None,
            )
            if right_border_index is not None:
                existing_tabs = current_model["borders"][right_border_index].get(
                    "children", []
                )
                tab_exists = any(
                    tab.get("id") == "col-remove-tab" for tab in existing_tabs
                )
                if tab_exists:
                    patched_model = Patch()
                    tab_index = next(
                        i
                        for i, tab in enumerate(existing_tabs)
                        if tab.get("id") == "col-remove-tab"
                    )
                    patched_model["borders"][right_border_index]["selected"] = tab_index
                    return patched_model, no_update, no_update

            new_tab = {
                "type": "tab",
                "name": "Remove Column",
                "component": "button",
                "enableClose": True,
                "id": "col-remove-tab",
            }

            patched_model = Patch()

            if right_border_index is not None:
                patched_model["borders"][right_border_index]["children"].append(new_tab)
                patched_model["borders"][right_border_index]["selected"] = len(
                    current_model["borders"][right_border_index]["children"]
                )
            else:
                patched_model["borders"].append(
                    {
                        "type": "border",
                        "location": "right",
                        "size": 300,
                        "selected": 0,
                        "children": [new_tab],
                    }
                )
            return patched_model, no_update, dff.columns

        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("remove-column-multi-select", "data", allow_duplicate=True),
            Output("remove-column-multi-select", "value"),
            Input("remove-column-apply-btn", "n_clicks"),
            State("remove-column-multi-select", "value"),
            prevent_initial_call=True,
        )
        def handle_remove_column_submission(n, selected_columns):
            if n is None:
                raise exceptions.PreventUpdate
            if not selected_columns:
                return (
                    [
                        dbpc.Toast(
                            message=f"No columns selected",
                            intent="warning",
                            icon="warning-sign",
                        )
                    ],
                    no_update,
                    no_update,
                    no_update,
                )
            try:
                SSDF.dataframe = SSDF.dataframe.drop(selected_columns)
                updated_columnDefs = generate_column_definitions(SSDF.dataframe)

                dff = displaying_df()

                return no_update, updated_columnDefs, dff.columns, []
            except Exception as e:
                return (
                    [dbpc.Toast(message=f"{str(e)}", intent="danger", icon="error")],
                    no_update,
                    no_update,
                    no_update,
                )

    def _register_edit_column_callback(self, app):

        @app.callback(
            Output("flex-layout", "model", allow_duplicate=True),
            Output("toaster", "toasts", allow_duplicate=True),
            Output("edit-column-multi-select", "data", allow_duplicate=True),
            Output("edit-column-multi-select", "value", allow_duplicate=True),
            Input("edit-column-btn", "n_clicks"),
            State("flex-layout", "model"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True,
        )
        def handle_edit_column_button_click(
            n_clicks, current_model, current_columnDefs
        ):
            if n_clicks is None:
                raise exceptions.PreventUpdate

            dff = displaying_df()
            if dff is None:
                return (
                    no_update,
                    [
                        dbpc.Toast(
                            message=f"No Dataframe loaded",
                            intent="warning",
                            icon="warning-sign",
                        )
                    ],
                    [],
                    [],
                )

            right_border_index = next(
                (
                    i
                    for i, b in enumerate(current_model["borders"])
                    if b["location"] == "right"
                ),
                None,
            )
            if right_border_index is not None:
                existing_tabs = current_model["borders"][right_border_index].get(
                    "children", []
                )
                tab_exists = any(
                    tab.get("id") == "col-edit-tab" for tab in existing_tabs
                )
                if tab_exists:
                    patched_model = Patch()
                    tab_index = next(
                        i
                        for i, tab in enumerate(existing_tabs)
                        if tab.get("id") == "col-edit-tab"
                    )
                    patched_model["borders"][right_border_index]["selected"] = tab_index
                    return patched_model, no_update, no_update, no_update

            new_tab = {
                "type": "tab",
                "name": "Edit Column",
                "component": "button",
                "enableClose": True,
                "id": "col-edit-tab",
            }

            patched_model = Patch()

            if right_border_index is not None:
                patched_model["borders"][right_border_index]["children"].append(new_tab)
                patched_model["borders"][right_border_index]["selected"] = len(
                    current_model["borders"][right_border_index]["children"]
                )
            else:
                patched_model["borders"].append(
                    {
                        "type": "border",
                        "location": "right",
                        "size": 300,
                        "selected": 0,
                        "children": [new_tab],
                    }
                )
            return (
                patched_model,
                no_update,
                [col for col in dff.columns if col != "waiver"],
                [
                    col_def["field"]
                    for col_def in current_columnDefs
                    if col_def["editable"]
                ],
            )

        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("edit-column-multi-select", "value"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True,
        )
        def handle_edit_column_submission(selected_columns, current_columnDefs):
            if not selected_columns:
                raise exceptions.PreventUpdate
            try:
                patched_columnDefs = Patch()
                for i, columnDef in enumerate(current_columnDefs):
                    col = columnDef["field"]
                    if col == "waiver":
                        continue
                    elif col in selected_columns:
                        logger.debug(f"is_editable: {col}")
                        patched_columnDefs[i] = generate_column_definition(
                            col, SSDF.dataframe[col], is_editable=True
                        )
                    else:
                        patched_columnDefs[i] = generate_column_definition(
                            col, SSDF.dataframe[col], is_editable=False
                        )
                return no_update, patched_columnDefs
            except Exception as e:
                return [
                    dbpc.Toast(message=f"{str(e)}", intent="danger", icon="error")
                ], no_update

    def _register_rename_column_callback(self, app):
        @app.callback(
            Output("flex-layout", "model", allow_duplicate=True),
            Output("toaster", "toasts", allow_duplicate=True),
            Output("rename-column-select", "data"),
            Input("rename-column-btn", "n_clicks"),
            State("flex-layout", "model"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True,
        )
        def open_rename_column_modal(n_clicks, current_model, columnDefs):
            if n_clicks is None:
                raise exceptions.PreventUpdate
            dff = displaying_df()
            if dff is None:
                return (
                    no_update,
                    [
                        dbpc.Toast(
                            message=f"No Dataframe loaded",
                            intent="warning",
                            icon="warning-sign",
                        )
                    ],
                    [],
                )
            right_border_index = next(
                (
                    i
                    for i, b in enumerate(current_model["borders"])
                    if b["location"] == "right"
                ),
                None,
            )
            if right_border_index is not None:
                existing_tabs = current_model["borders"][right_border_index].get(
                    "children", []
                )
                tab_exists = any(
                    tab.get("id") == "col-concat-tab" for tab in existing_tabs
                )
                if tab_exists:
                    patched_model = Patch()
                    tab_index = next(
                        i
                        for i, tab in enumerate(existing_tabs)
                        if tab.get("id") == "col-concat-tab"
                    )
                    patched_model["borders"][right_border_index]["selected"] = tab_index
                    return patched_model, no_update, no_update
            new_tab = {
                "type": "tab",
                "name": "Concat Column",
                "component": "button",
                "enableClose": True,
                "id": "col-concat-tab",
            }
            patched_model = Patch()
            if right_border_index is not None:
                patched_model["borders"][right_border_index]["children"].append(new_tab)
                patched_model["borders"][right_border_index]["selected"] = len(
                    current_model["borders"][right_border_index]["children"]
                )
            else:
                patched_model["borders"].append(
                    {
                        "type": "border",
                        "location": "right",
                        "size": 300,
                        "selected": 0,
                        "children": [new_tab],
                    }
                )
            return patched_model, no_update, dff.columns

        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("rename-column-apply-btn", "n_clicks"),
            State("rename-column-select", "value"),
            State("new-column-name-input", "value"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True,
        )
        def rename_column(n_clicks, old_name, new_name, columnDefs):
            if n_clicks is None or not old_name or not new_name:
                raise exceptions.PreventUpdate
            if new_name in [col["field"] for col in columnDefs]:
                return [dbpc.Toast(message=f"Column already exists")], no_update
            try:
                SSDF.dataframe = SSDF.dataframe.rename({old_name: new_name})
                patched_columnDefs = Patch()
                for i, columnDef in enumerate(columnDefs):
                    if columnDef["field"] == old_name:
                        patched_columnDefs[i] = generate_column_definition(
                            new_name, SSDF.dataframe[new_name]
                        )
                return no_update, patched_columnDefs
            except Exception as e:
                return [
                    dbpc.Toast(message=f"{str(e)}", intent="danger", icon="error")
                ], no_update

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
                    [
                        dbpc.Toast(
                            message=f"No Dataframe loaded",
                            intent="warning",
                            icon="warning-sign",
                        )
                    ],
                    [],
                )
            right_border_index = next(
                (
                    i
                    for i, b in enumerate(current_model["borders"])
                    if b["location"] == "right"
                ),
                None,
            )
            if right_border_index is not None:
                existing_tabs = current_model["borders"][right_border_index].get(
                    "children", []
                )
                tab_exists = any(
                    tab.get("id") == "col-concat-tab" for tab in existing_tabs
                )
                if tab_exists:
                    patched_model = Patch()
                    tab_index = next(
                        i
                        for i, tab in enumerate(existing_tabs)
                        if tab.get("id") == "col-concat-tab"
                    )
                    patched_model["borders"][right_border_index]["selected"] = tab_index
                    return patched_model, no_update, no_update
            new_tab = {
                "type": "tab",
                "name": "Concat Column",
                "component": "button",
                "enableClose": True,
                "id": "col-concat-tab",
            }
            patched_model = Patch()
            if right_border_index is not None:
                patched_model["borders"][right_border_index]["children"].append(new_tab)
                patched_model["borders"][right_border_index]["selected"] = len(
                    current_model["borders"][right_border_index]["children"]
                )
            else:
                patched_model["borders"].append(
                    {
                        "type": "border",
                        "location": "right",
                        "size": 300,
                        "selected": 0,
                        "children": [new_tab],
                    }
                )
            return patched_model, no_update, dff.columns

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
        def handle_apply_find_replace(
            n_clicks, column, find_value, replace_value, use_regex
        ):
            if n_clicks is None or not column:
                raise exceptions.PreventUpdate

            if find_value is None or find_value.strip() == "":
                return [
                    dbpc.Toast(message=f"Find value empty", intent="warning")
                ], no_update

            replace_value = "" if replace_value is None else replace_value
            try:
                is_string_column = isinstance(SSDF.dataframe[column].dtype, pl.Utf8)

                if is_string_column:
                    if use_regex:
                        SSDF.dataframe = SSDF.dataframe.with_columns(
                            pl.col(column)
                            .str.replace_all(rf"{find_value}", replace_value)
                            .alias(column)
                        )
                    else:
                        SSDF.dataframe = SSDF.dataframe.with_columns(
                            pl.col(column)
                            .str.replace_all(find_value, replace_value)
                            .alias(column)
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
                return no_update, updated_columnDefs
            except Exception as e:
                return [
                    dbpc.Toast(message=f"{str(e)}", intent="danger", icon="error")
                ], no_update

    def _register_hier_count_callback(self, app):
        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("hier-count-apply-btn", "n_clicks"),
            State("hier-count-column-select", "value"),
            State("hier-count-delimiter-input", "value"),
            prevent_initial_call=True,
        )
        def handle_apply_hier_count(n_clicks, selected_column, delimiter):
            if n_clicks is None or not selected_column:
                return no_update, no_update
            try:
                df = SSDF.dataframe
                df = df.with_columns(
                    pl.col(selected_column)
                    .str.split(delimiter)
                    .list.len()
                    .alias("hier_count")
                )
                SSDF.dataframe = df
                updated_columnDefs = generate_column_definitions(df)
                return [dbpc.Toast(message=f"Hier column added ")], updated_columnDefs
            except Exception as e:
                return [dbpc.Toast(message=f"{str(e)}")], no_update
