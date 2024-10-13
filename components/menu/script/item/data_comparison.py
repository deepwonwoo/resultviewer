import polars as pl
import dash_mantine_components as dmc
from dash import Input, Output, State, html, dcc, no_update, ALL
from utils.component_template import get_icon, create_notification
from utils.db_management import SSDF
from utils.data_processing import displaying_df, validate_df
from utils.config import CONFIG
from components.menu.home.item.workspace_explore import FileExplorer
from components.grid.dag.column_definitions import (
    generate_column_definition,
    generate_column_definitions,
)
import subprocess


def compare(df1, df2, keys, values, tolerances):
    # test_case1_result = compare(df1, df2,  ["key1", "key2", "key3"], ["value1", "value2", "value3", "value4"], [0, 0, 0, 0])
    # print("testcase #1")
    # display(test_case1_result)
    #
    # test_case2_result = compare(df1, df2,  ["key1", "key2", "key3"], ["value1", "value2", "value3", "value4"], [0, 2, 0, 0])
    # print("testcase #2")
    # display(test_case2_result)
    #
    # test_case3_result = compare(df1, df2, ["key1", "key2"], ["value1", "value2"], [0, 0])
    # print("testcase #3")
    # display(test_case3_result)
    #
    # test_case4_result = compare(df1, df3, ["key1", "key2", "key3"], ["value1", "value2", "value3", "value4"], [0, 0, 0, 0])
    # print("testcase #4")
    # display(test_case4_result)

    def preprocessing_target_df(df2, keys, values):
        df2_preprocess = df2.select(keys + values)
        # 각 키 조합에 대해 값들이 일관된지 확인
        df2_preprocess = df2_preprocess.group_by(keys).agg(
            [pl.min(values).name.suffix("_min"), pl.max(values).name.suffix("_max")]
        )
        # 최소값과 최대값이 모두 동일한 경우 "same", 그렇지 않으면 "duplicated"
        for value in values:
            min_col = f"{value}_min"
            max_col = f"{value}_max"
            df2_preprocess = df2_preprocess.with_columns(
                pl.when(pl.col(min_col) == pl.col(max_col))
                .then(pl.lit("same"))
                .otherwise(pl.lit("duplicated"))
                .alias(f"{value}_compare")
            )
        compare_condition = pl.all_horizontal(
            [pl.col(f"{value}_compare") == pl.lit("same") for value in values]
        )
        compare_column = (
            pl.when(compare_condition)
            .then(pl.lit("same"))
            .otherwise(pl.lit("duplicated"))
        )

        df2_preprocess = df2_preprocess.with_columns(compare_column.alias("compare"))

        # `keys`와 `values`를 기반으로 동적으로 컬럼 선택 및 조건부 로직을 적용
        dynamic_select = (
            [
                # 모든 키 컬럼을 선택
                pl.col(key)
                for key in keys
            ]
            + [
                # 모든 값 컬럼에 대해 compare가 "same"이면 min 값을, 아니면 None을 선택
                pl.when(pl.col(f"{value}_compare") == "same")
                .then(pl.col(f"{value}_min"))
                .otherwise(None)
                .alias(value)
                for value in values
            ]
            + [pl.col("compare")]
        )

        return df2_preprocess.select(dynamic_select)

    df2 = preprocessing_target_df(df2, keys, values)

    df_joined = df1.join(df2, on=keys, how="left", suffix="_df2")
    # Prepare columns to add
    columns_to_add = []

    all_null_condition = pl.all_horizontal(
        [pl.col(f"{value}_is_null") for value in values]
    )
    any_null_condition = pl.all_horizontal(
        [pl.col(f"{value}_is_null") for value in values]
    )

    # Calculate deltas and add them as new columns
    for value, tolerance in zip(values, tolerances):
        delta = (df_joined[value] - df_joined[f"{value}_df2"]).abs()
        delta_name = f"delta_{value}"
        columns_to_add.append(delta.alias(delta_name))

    # Calculate the "compare" column
    # Start by assuming all rows match ("same")
    compare_column = pl.lit("same")

    # df_joined에 대한 모든 values에 대해 결측값 여부를 확인하고 compare_column 업데이트
    values_null_checks = [
        pl.col(f"{value}_df2").is_null().alias(f"{value}_is_null") for value in values
    ]
    df_joined = df_joined.with_columns(values_null_checks)

    # 모든 값이 null일 경우 "not found", 하나라도 null이 있는 경우 "duplicated", 모두 null이 아니면 기존 compare 값을 사용

    compare_column = (
        pl.when(all_null_condition)
        .then(pl.lit("not found"))
        .when(any_null_condition)
        .then(pl.lit("duplicated"))
        .otherwise(pl.col("compare"))
        .alias("compare")
    )

    for i, value in enumerate(values):
        delta_name = f"delta_{value}"
        # Check if the delta exceeds the tolerance
        condition = pl.col(delta_name) > tolerances[i]
        # If any delta exceeds the tolerance, mark as "diff"
        compare_column = (
            pl.when(condition).then(pl.lit("diff")).otherwise(compare_column)
        )

    # 최종 DataFrame 업데이트
    df_joined = df_joined.with_columns(columns_to_add)
    df_joined = df_joined.with_columns(compare_column.alias("compare"))

    final_df = df_joined.drop([f"{value}_is_null" for value in values])

    # 불필요한 *_df2 열 제거
    drop_columns = [f"{value}_df2" for value in values] + ["name_df2"]
    final_df = final_df.drop(drop_columns)

    # # Check for rows in df1 that are not found in df2
    # not_found_condition = df_joined[f"{values[0]}_df2"].is_null()
    # compare_column = pl.when(not_found_condition).then(pl.lit("not found")).otherwise(compare_column)

    # # Add the compare column and all delta columns to the df_joined DataFrame
    # df_joined = df_joined.with_columns(columns_to_add)
    # final_df = df_joined.with_columns(compare_column.alias('compare'))

    # # Drop the *_df2 columns to clean up the DataFrame
    # drop_columns = [f"{value}_df2" for value in values] + ["name_df2"]
    # final_df = final_df.drop(drop_columns)

    return final_df


class Compare:
    def layout(self):
        return html.Div(
            [
                dmc.Button(
                    "Compare",
                    id="compare-btn",
                    variant="outline",
                    leftSection=get_icon("compare"),
                    color="indigo",
                    size="xs",
                ),
                self.modal(),
            ],
        )

    def modal(self):
        body = dmc.TableTbody(id="table_rows")
        head = dmc.TableThead(
            dmc.TableTr(
                [
                    dmc.TableTh("Keys"),
                    dmc.TableTh("Values"),
                    dmc.TableTh("Tolerences"),
                ]
            )
        )
        caption = dmc.TableCaption("Selected Columns to Compare")

        return dmc.Modal(
            title=dmc.Title(f"Compare", order=3),
            id="compare-modal",
            size="xl",
            opened=False,
            closeOnClickOutside=False,
            children=[
                dmc.Card(
                    children=[
                        dmc.TextInput(
                            label="Upload compare target file path",
                            leftSection=dmc.ActionIcon(
                                get_icon("bx-file-find"),
                                id="upload-compare-file-search",
                                variant="subtle",
                                n_clicks=0,
                            ),
                            rightSection=dmc.Button(
                                "Upload",
                                id="upload-compare-target-btn",
                                style={"width": 100},
                                n_clicks=0,
                            ),
                            rightSectionWidth=100,
                            required=True,
                            id="upload-compare-path-input",
                        ),
                        dmc.MultiSelect(
                            label="Select Columns",
                            placeholder="Select columns to compare!",
                            id="column-multi-select",
                            value=[],
                            # data=df1.columns,
                            mb=10,
                            disabled=True,
                        ),
                        dmc.Table([head, body, caption]),
                        dmc.Button(
                            "Compare",
                            id="run-compare-btn",
                            variant="outline",
                            fullWidth=True,
                            mt=15,
                        ),
                    ],
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                )
            ],
        )

    def register_callbacks(self, app):

        @app.callback(
            Output("compare-modal", "opened", allow_duplicate=True),
            Output("notifications", "children", allow_duplicate=True),
            Input("compare-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def compare_modal_open(nc):
            if displaying_df() is None:
                return no_update, create_notification(
                    message="No Dataframe loaded", position="center"
                )
            return True, None

        @app.callback(
            Output("upload-compare-path-input", "value", allow_duplicate=True),
            Input("upload-compare-file-search", "n_clicks"),
            prevent_initial_call=True,
        )
        def find_FileDialog(n):
            # result = subprocess.run(["python", f"{SCRIPT}/QFileDialog/OpenFileName.py"], capture_output=True, text=True)
            cmd = f"{CONFIG.SCRIPT}/QFileDialog/file_dialog"
            result = subprocess.run([cmd], capture_output=True, text=True)
            file_path = result.stdout.strip()
            return file_path if file_path else no_update

        @app.callback(
            Output("column-multi-select", "data"),
            Output("column-multi-select", "disabled"),
            Output("notifications", "children", allow_duplicate=True),
            Input("upload-compare-target-btn", "n_clicks"),
            State("upload-compare-path-input", "value"),
            prevent_initial_call=True,
        )
        def check_compare_columns(n, compare_target_path):
            try:
                target_df = validate_df(compare_target_path)
            except Exception as e:
                noti = create_notification(
                    message=f"Error loading {compare_target_path}: {e}",
                    position="center",
                )
                return no_update, True, noti

            df_columns = SSDF.dataframe.columns
            df_columns.remove("uniqid")
            target_df_columns = target_df.columns
            common_columns = [col for col in df_columns if col in target_df_columns]

            if common_columns == []:
                noti = create_notification(
                    message="No common columns found between the two dataframes.",
                    position="center",
                )
                return no_update, True, noti

            return common_columns, False, None

        @app.callback(
            Output("table_rows", "children"),
            Input("column-multi-select", "value"),
            prevent_initial_call=True,
        )
        def select_value(selected_list):
            rows = []
            for i, selected in enumerate(selected_list):
                if SSDF.dataframe[selected].dtype.is_numeric():
                    element = dmc.TableTr(
                        [
                            dmc.TableTd(""),
                            dmc.TableTd(
                                dmc.Text(
                                    selected,
                                    id={"type": "value", "index": i},
                                    size="sm",
                                )
                            ),
                            dmc.TableTd(
                                dmc.NumberInput(
                                    value=0,
                                    min=0,
                                    size="xs",
                                    id={"type": "tolerance", "index": i},
                                )
                            ),
                        ]
                    )
                else:
                    element = dmc.TableTr(
                        [
                            dmc.TableTd(
                                dmc.Text(
                                    selected, id={"type": "key", "index": i}, size="sm"
                                )
                            ),
                            dmc.TableTd(""),
                            dmc.TableTd(""),
                        ]
                    )
                rows.append(element)
            return rows

        app.clientside_callback(
            """
            function updateLoadingState(n_clicks) {
                return true
            }
            """,
            Output("run-compare-btn", "loading", allow_duplicate=True),
            Input("run-compare-btn", "n_clicks"),
            prevent_initial_call=True,
        )

        @app.callback(
            Output("compare-modal", "opened", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("run-compare-btn", "loading"),
            Output("notifications", "children", allow_duplicate=True),
            Input("run-compare-btn", "n_clicks"),
            State("upload-compare-path-input", "value"),
            State({"type": "key", "index": ALL}, "children"),
            State({"type": "value", "index": ALL}, "children"),
            State({"type": "tolerance", "index": ALL}, "value"),
            prevent_initial_call=True,
        )
        def run_compare(n, compare_file_path, key_list, value_list, tolerance_list):

            target_df = validate_df(compare_file_path)

            exclude_columns = ["compare"] + [
                col for col in SSDF.dataframe.columns if col.startswith("delta_")
            ]
            SSDF.dataframe = SSDF.dataframe.select(
                [col for col in SSDF.dataframe.columns if col not in exclude_columns]
            )
            current_columnDefs = generate_column_definitions(SSDF.dataframe)

            compare_df = compare(
                SSDF.dataframe, target_df, key_list, value_list, tolerance_list
            )

            SSDF.dataframe = compare_df

            for i, columnDef in enumerate(current_columnDefs.copy()):
                field = columnDef.get("field")
                if field in key_list:
                    current_columnDefs[i]["headerClass"] = "text-primary"

            current_columnDefs.append(
                generate_column_definition("compare", compare_df["compare"])
            )

            cellClassRules = {
                "text-danger": "params.data.compare === 'diff' && params.value != 0"
            }
            for v in value_list:
                current_columnDefs.append(
                    generate_column_definition(
                        f"delta_{v}",
                        compare_df[f"delta_{v}"],
                        cellClassRules=cellClassRules,
                    )
                )

            result = compare_df.group_by("compare").agg(pl.count())
            result_dicts = result.to_dicts()
            msg = ""
            for row in result_dicts:
                msg += "{:<15}: {:<10}\n".format(row["compare"], row["count"])

            return (
                False,
                current_columnDefs,
                False,
                create_notification(
                    title="Compare Applied",
                    message=dcc.Markdown(msg),
                    position="center",
                    icon_name="bx-smile",
                ),
            )
