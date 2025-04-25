import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, no_update, exceptions, ctx, ALL
from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions, SYSTEM_COLUMNS
from components.menu.edit.utils import find_tab_in_layout, handle_tab_button_click


class FillNanValues:
    def __init__(self):
        # 대체 방법 옵션
        self.fill_methods = [
            {"value": "value", "label": "특정 값으로 대체"},
            {"value": "zero", "label": "0으로 대체"},
            {"value": "mean", "label": "평균값으로 대체 (숫자 컬럼만)"},
            {"value": "median", "label": "중앙값으로 대체 (숫자 컬럼만)"},
            {"value": "mode", "label": "최빈값으로 대체"},
            {"value": "forward", "label": "앞의 값으로 대체 (forward fill)"},
            {"value": "backward", "label": "뒤의 값으로 대체 (backward fill)"},
            {"value": "empty_string", "label": "빈 문자열로 대체 (문자열 컬럼만)"}
        ]

    def button_layout(self):
        return dbpc.Button("Fill NaN Values", id="fill-nan-btn", icon="edit", minimal=True, outlined=True)

    def tab_layout(self):
        return dmc.Paper(
            children=[
                dmc.Group([dbpc.EntityTitle(title="Fill NaN Values", heading="H5", icon="edit")], grow=True),
                dmc.Space(h=10),
                # 컬럼 선택 MultiSelect
                dmc.MultiSelect(
                    id="fill-nan-column-select",
                    label="컬럼 선택",
                    description="NaN 또는 Null 값을 채울 컬럼을 선택하세요 (복수 선택 가능)",
                    placeholder="컬럼 선택...",
                    required=True,
                    searchable=True,
                    clearable=True,
                    data=[],
                    size="md",
                    leftSection=dbpc.Icon(icon="properties"),
                ),
                dmc.Space(h=20),
                # 컬럼 정보 표시 영역
                html.Div(id="fill-nan-info-container"),
                dmc.Space(h=20),
                # 대체 방법 선택
                dmc.Select(
                    id="fill-nan-method",
                    label="대체 방법",
                    description="NaN/Null 값을 어떤 방식으로 대체할지 선택하세요",
                    placeholder="대체 방법 선택...",
                    data=self.fill_methods,
                    value="value",
                    size="md",
                    leftSection=dbpc.Icon(icon="polygon-filter"),
                ),
                dmc.Space(h=15),
                # 대체값 입력 필드 (method가 'value'일 때만 표시)
                html.Div(
                    id="fill-nan-value-container",
                    children=[
                        dmc.TextInput(
                            id="fill-nan-value-input",
                            label="대체할 값",
                            description="NaN/Null 값을 대체할 값을 입력하세요",
                            placeholder="대체값 입력...",
                            size="sm",
                        )
                    ],
                ),
                dmc.Space(h=20),
                # 미리보기 영역
                dmc.Paper(
                    id="fill-nan-preview-container",
                    withBorder=True,
                    p="sm",
                    style={"maxHeight": "200px", "overflow": "auto"},
                    children=[
                        dmc.Text(
                            "미리보기: 컬럼과 대체 방법을 선택하면 변환 예시가 표시됩니다.",
                            size="sm",
                            c="dimmed",
                        )
                    ],
                ),
                dmc.Space(h=20),
                # 필터링된 데이터만 적용 옵션
                dmc.Checkbox(
                    id="fill-nan-filtered-only",
                    label="필터링된 데이터에만 적용",
                    description="현재 필터링된 데이터에만 NaN/Null 대체를 적용합니다",
                    size="sm",
                ),
                dmc.Space(h=20),
                # 적용 버튼
                dmc.Group(
                    [
                        dbpc.Button(
                            "Apply",
                            id="fill-nan-apply-btn",
                            outlined=True,
                            icon="tick",
                            intent="primary",
                        )
                    ],
                    justify="center",
                ),
                # 도움말 섹션
                dmc.Space(h=20),
                dmc.Accordion(
                    value="",
                    children=[
                        dmc.AccordionItem(
                            [
                                dmc.AccordionControl("도움말"),
                                dmc.AccordionPanel(
                                    [
                                        dmc.Text("1. NaN/Null 값을 채울 컬럼을 하나 이상 선택하세요."),
                                        dmc.Text("2. 대체 방법을 선택하세요:"),
                                        dmc.Text("   - 특정 값으로 대체: 사용자가 입력한 값으로 대체합니다."),
                                        dmc.Text("   - 0으로 대체: 모든 NaN/Null 값을 0으로 대체합니다."),
                                        dmc.Text("   - 평균값/중앙값: 숫자형 컬럼의 경우 해당 통계값으로 대체합니다."),
                                        dmc.Text("   - 최빈값: 가장 빈번하게 나타나는 값으로 대체합니다."),
                                        dmc.Text("   - 앞/뒤의 값: 이전/이후의 유효한 값으로 대체합니다."),
                                        dmc.Text("   - 빈 문자열: 문자열 컬럼의 경우 빈 문자열로 대체합니다."),
                                        dmc.Text("3. 미리보기를 확인하고 Apply 버튼을 클릭하세요."),
                                    ]
                                ),
                            ],
                            value="help",
                        )
                    ],
                ),
            ],
            p="md",
            shadow="sm",
            radius="xs",
            withBorder=True,
        )

    def register_callbacks(self, app):
        """콜백 함수 등록"""

        @app.callback(
            Output("flex-layout", "model", allow_duplicate=True),
            Output("toaster", "toasts", allow_duplicate=True),
            Input("fill-nan-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True,
        )
        def handle_fill_nan_button_click(n_clicks, current_model):
            """Fill NaN Values 버튼 클릭 시 우측 패널에 탭 추가"""
            return handle_tab_button_click(n_clicks, current_model, "fill-nan-tab", "Fill NaN Values")

        @app.callback(
            Output("fill-nan-column-select", "data"),
            Input("fill-nan-btn", "n_clicks"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True,
        )
        def update_column_list(n_clicks, columnDefs):
            """Fill NaN Values 버튼 클릭 시 컬럼 목록 로드"""
            if n_clicks is None or not columnDefs:
                return []

            # 컬럼 필터링 (보호할 컬럼 제외)
            column_data = [
                {"label": col["field"], "value": col["field"]}
                for col in columnDefs
                if col["field"] not in SYSTEM_COLUMNS
            ]

            return column_data

        @app.callback(
            Output("fill-nan-info-container", "children"),
            Input("fill-nan-column-select", "value"),
            prevent_initial_call=True,
        )
        def display_column_nan_info(selected_columns):
            """선택한 컬럼의 NaN/Null 정보 표시"""
            if not selected_columns:
                return dmc.Text("컬럼을 선택하세요", size="sm", c="dimmed")

            df = SSDF.dataframe
            info_components = []

            for col in selected_columns:
                try:
                    # 컬럼 데이터 타입 확인
                    dtype = df[col].dtype

                    # 사람이 읽기 쉬운 타입명 생성
                    readable_type = "알 수 없음"
                    type_color = "gray"

                    if dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                        readable_type = "정수 (Integer)"
                        type_color = "blue"
                    elif dtype in [pl.Float64, pl.Float32]:
                        readable_type = "실수 (Float)"
                        type_color = "cyan"
                    elif dtype == pl.Boolean:
                        readable_type = "불리언 (Boolean)"
                        type_color = "green"
                    elif dtype in [pl.Utf8, pl.String]:
                        readable_type = "문자열 (String)"
                        type_color = "orange"
                    elif dtype == pl.Categorical:
                        readable_type = "카테고리 (Categorical)"
                        type_color = "pink"

                    # 컬럼의 NaN/Null 값 정보
                    null_count = df[col].null_count()
                    nan_count = 0
                    
                    # -99999 값 (현재 대체되고 있는 NaN/Null) 개수 확인
                    temp_neg_count = 0
                    if dtype in [pl.Float64, pl.Float32, pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                        temp_neg_count = df.filter(pl.col(col) == -99999).height
                    
                    total_count = len(df[col])
                    missing_percent = ((null_count + nan_count + temp_neg_count) / total_count * 100) if total_count > 0 else 0

                    # 컬럼 정보 컴포넌트 생성
                    info_component = dmc.Paper(
                        withBorder=True,
                        p="xs",
                        mb="xs",
                        children=[
                            dmc.Group(
                                [
                                    dmc.Text(f"컬럼: {col}", w=500),
                                    dmc.Badge(readable_type, color=type_color),
                                ],
                                justify="apart",
                            ),
                            dmc.Text(
                                f"Null 값: {null_count}, 임시값(-99999): {temp_neg_count}, 전체 행: {total_count} (비율: {missing_percent:.1f}%)",
                                size="xs",
                                c="dimmed",
                            ),
                        ],
                    )

                    info_components.append(info_component)

                except Exception as e:
                    logger.error(f"컬럼 {col} 정보 표시 오류: {str(e)}")
                    info_components.append(
                        dmc.Alert(
                            f"컬럼 '{col}' 정보를 가져올 수 없습니다: {str(e)}",
                            color="red",
                            variant="light",
                            mb="xs",
                        )
                    )

            return info_components

        @app.callback(
            Output("fill-nan-value-container", "style"),
            Input("fill-nan-method", "value"),
            prevent_initial_call=True,
        )
        def toggle_value_input(method):
            """대체 방법에 따라 값 입력 필드 표시/숨김"""
            if method == "value":
                return {"display": "block"}
            return {"display": "none"}

        @app.callback(
            Output("fill-nan-preview-container", "children"),
            [
                Input("fill-nan-column-select", "value"),
                Input("fill-nan-method", "value"),
                Input("fill-nan-value-input", "value"),
            ],
            prevent_initial_call=True,
        )
        def update_preview(selected_columns, method, value):
            """선택한 컬럼과 대체 방법에 따라 미리보기 표시"""
            if not selected_columns or not method:
                return [
                    dmc.Text(
                        "미리보기: 컬럼과 대체 방법을 선택하면 변환 예시가 표시됩니다.",
                        size="sm",
                        c="dimmed",
                    )
                ]

            df = SSDF.dataframe
            preview_content = []

            # 첫 번째 선택된 컬럼에 대해서만 미리보기 제공
            col = selected_columns[0]

            try:
                # 원본 컬럼 데이터 타입 확인
                dtype = df[col].dtype

                # 최대 5개의 샘플 값 선택 (최소 하나 이상의 NaN/Null 값 포함)
                sample_rows = []
                
                # NaN/-99999 값이 포함된 행 먼저 찾기
                if dtype in [pl.Float64, pl.Float32, pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                    nan_rows = df.filter((pl.col(col).is_null()) | (pl.col(col) == -99999)).head(3)
                    if len(nan_rows) > 0:
                        sample_rows.extend(nan_rows.to_dicts())
                else:
                    nan_rows = df.filter(pl.col(col).is_null()).head(3)
                    if len(nan_rows) > 0:
                        sample_rows.extend(nan_rows.to_dicts())
                
                # 일반 값이 포함된 행 추가
                normal_rows = df.filter(~pl.col(col).is_null() & (pl.col(col) != -99999)).head(2)
                if len(normal_rows) > 0:
                    sample_rows.extend(normal_rows.to_dicts())
                
                # 샘플 행이 없으면 일반 행만 표시
                if not sample_rows:
                    sample_rows = df.head(5).to_dicts()

                # 대체 함수 선택
                replacement_value = self._get_replacement_value(method, value, df, col)

                # 미리보기 생성 - 원본 값과 대체 후 값 표시
                transformed_values = []
                for row in sample_rows:
                    orig_value = row.get(col)
                    # NULL, -99999 또는 NaN인 경우 대체
                    if orig_value is None or orig_value == -99999:
                        new_value = replacement_value
                        status = "변경"
                    else:
                        new_value = orig_value
                        status = "유지"
                    
                    transformed_values.append((orig_value, new_value, status))

                # 미리보기 테이블 생성
                header = [
                    dmc.TableThead(
                        dmc.TableTr(
                            [
                                dmc.TableTh("원본 값", style={"width": "40%"}),
                                dmc.TableTh("대체 후 값", style={"width": "40%"}),
                                dmc.TableTh("상태", style={"width": "20%"}),
                            ]
                        )
                    )
                ]

                rows = [
                    dmc.TableTr(
                        [
                            dmc.TableTd(str(orig) if orig is not None else "NULL"),
                            dmc.TableTd(str(new) if new is not None else "NULL"),
                            dmc.TableTd(
                                dmc.Badge(
                                    status,
                                    color="green" if status == "변경" else "gray",
                                    variant="light",
                                    size="sm",
                                )
                            ),
                        ]
                    )
                    for orig, new, status in transformed_values
                ]

                preview_table = dmc.Table(
                    [*header, dmc.TableTbody(rows)],
                    striped=True,
                    highlightOnHover=True,
                    withTableBorder=True,
                    withColumnBorders=True,
                )

                preview_content = [
                    dmc.Text(f"컬럼 '{col}'의 NaN/Null 값 대체 미리보기:", size="sm", w=500, mb="xs"),
                    preview_table,
                ]

            except Exception as e:
                logger.error(f"미리보기 생성 오류: {str(e)}")
                preview_content = [
                    dmc.Alert(
                        f"미리보기를 생성할 수 없습니다: {str(e)}",
                        color="red",
                        variant="light",
                    )
                ]

            return preview_content

        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            [Input("fill-nan-apply-btn", "n_clicks")],
            [
                State("fill-nan-column-select", "value"),
                State("fill-nan-method", "value"),
                State("fill-nan-value-input", "value"),
                State("fill-nan-filtered-only", "checked"),
            ],
            prevent_initial_call=True,
        )
        def apply_fill_nan(n_clicks, selected_columns, method, value, filtered_only):
            """NaN/Null 값 대체 적용"""
            if not n_clicks or not selected_columns or not method:
                raise exceptions.PreventUpdate

            try:
                # 원본 데이터프레임 복사
                df = SSDF.dataframe.clone()

                # 필터링된 데이터만 처리하는 경우
                filtered_ids = None
                if filtered_only:
                    from components.grid.dag.SSRM.apply_filter import apply_filters

                    filtered_df = apply_filters(df, SSDF.request)
                    if "uniqid" in filtered_df.columns:
                        filtered_ids = filtered_df["uniqid"]

                # 각 컬럼에 대해 NaN/Null 값 대체 수행
                failed_columns = []
                successful_columns = []
                replaced_counts = {}

                for col in selected_columns:
                    try:
                        # 컬럼 데이터 타입 확인
                        dtype = df[col].dtype
                        
                        # 대체값 계산
                        replacement_value = self._get_replacement_value(method, value, df, col)

                        # 변환 및 적용
                        if filtered_only and filtered_ids is not None:
                            # 필터링된 행에만 적용
                            if dtype in [pl.Float64, pl.Float32, pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                                # 숫자 컬럼의 경우 NaN, Null, -99999 처리
                                condition = (pl.col("uniqid").is_in(filtered_ids)) & ((pl.col(col).is_null()) | (pl.col(col) == -99999))
                            else:
                                # 비숫자 컬럼의 경우 Null만 처리
                                condition = (pl.col("uniqid").is_in(filtered_ids)) & (pl.col(col).is_null())
                            
                            # 교체 전에 개수 확인
                            replace_count = df.filter(condition).height
                            replaced_counts[col] = replace_count
                            
                            # 조건에 맞는 값 대체
                            df = df.with_columns([
                                pl.when(condition)
                                .then(pl.lit(replacement_value))
                                .otherwise(pl.col(col))
                                .alias(col)
                            ])
                        else:
                            # 전체 적용
                            if dtype in [pl.Float64, pl.Float32, pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                                # 숫자 컬럼의 경우 NaN, Null, -99999 처리
                                condition = (pl.col(col).is_null()) | (pl.col(col) == -99999)
                            else:
                                # 비숫자 컬럼의 경우 Null만 처리
                                condition = pl.col(col).is_null()
                            
                            # 교체 전에 개수 확인
                            replace_count = df.filter(condition).height
                            replaced_counts[col] = replace_count
                            
                            # 조건에 맞는 값 대체
                            df = df.with_columns([
                                pl.when(condition)
                                .then(pl.lit(replacement_value))
                                .otherwise(pl.col(col))
                                .alias(col)
                            ])

                        successful_columns.append(col)

                    except Exception as e:
                        logger.error(f"컬럼 '{col}' NaN/Null 값 대체 실패: {str(e)}")
                        failed_columns.append((col, str(e)))

                # 실패한 컬럼이 있는 경우
                if failed_columns:
                    error_messages = "\n".join([f"- {col}: {err}" for col, err in failed_columns])

                    # 일부 컬럼만 성공한 경우
                    if successful_columns:
                        SSDF.dataframe = df
                        updated_columnDefs = generate_column_definitions(df)

                        return (
                            [
                                dbpc.Toast(
                                    message=f"{len(successful_columns)}개 컬럼 처리 성공, {len(failed_columns)}개 실패\n{error_messages}",
                                    intent="warning",
                                    icon="warning-sign",
                                    timeout=4000,
                                )
                            ],
                            updated_columnDefs,
                        )
                    else:
                        # 모든 컬럼 변환 실패
                        return (
                            [
                                dbpc.Toast(
                                    message=f"모든 컬럼 처리 실패:\n{error_messages}",
                                    intent="danger",
                                    icon="error",
                                    timeout=4000,
                                )
                            ],
                            no_update,
                        )

                # 모든 컬럼 변환 성공
                SSDF.dataframe = df
                updated_columnDefs = generate_column_definitions(df)
                
                # 대체 방법 설명 텍스트 생성
                method_text = {
                    "value": f"사용자 값({value})",
                    "zero": "0",
                    "mean": "평균값",
                    "median": "중앙값",
                    "mode": "최빈값",
                    "forward": "앞의 값",
                    "backward": "뒤의 값",
                    "empty_string": "빈 문자열"
                }.get(method, method)
                
                # 대체된 값 개수 정보 생성
                replacement_info = ", ".join([f"{col}: {count}개" for col, count in replaced_counts.items() if count > 0])
                if not replacement_info:
                    replacement_info = "대체된 값 없음"

                return (
                    [
                        dbpc.Toast(
                            message=f"{len(successful_columns)}개 컬럼의 NaN/Null 값이 {method_text}로 대체되었습니다. ({replacement_info})",
                            intent="success",
                            icon="endorsed",
                            timeout=3000,
                        )
                    ],
                    updated_columnDefs,
                )

            except Exception as e:
                # 전체 처리 오류
                logger.error(f"NaN/Null 값 대체 처리 오류: {str(e)}")
                return (
                    [
                        dbpc.Toast(
                            message=f"NaN/Null 값 대체 처리 오류: {str(e)}",
                            intent="danger",
                            icon="error",
                        )
                    ],
                    no_update,
                )


    def _get_replacement_value(self, method, value, df, col):
        """대체 방법에 따른 대체값 계산"""
        dtype = df[col].dtype

        # 특정 값으로 대체
        if method == "value":
            if value is None:
                return ""
            
            # 데이터 타입에 맞게 변환
            try:
                if dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                    return int(value)
                elif dtype in [pl.Float64, pl.Float32]:
                    return float(value)
                elif dtype == pl.Boolean:
                    return value.lower() in ["true", "1", "yes", "y", "t"]
                else:
                    return value
            except:
                # 변환 실패 시 원래 값 그대로 반환
                return value
        
        # 0으로 대체
        elif method == "zero":
            if dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                return 0
            elif dtype in [pl.Float64, pl.Float32]:
                return 0.0
            elif dtype == pl.Boolean:
                return False
            else:
                return "0"
        
        # 평균값으로 대체 (숫자 컬럼만)
        elif method == "mean":
            if dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64, pl.Float64, pl.Float32]:
                # -99999 값 제외하고 평균 계산
                filtered_df = df.filter(pl.col(col) != -99999)
                mean_value = filtered_df[col].mean()
                
                # 정수형이면 반올림
                if dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                    return int(round(mean_value))
                return mean_value
            else:
                return ""
        
        # 중앙값으로 대체 (숫자 컬럼만)
        elif method == "median":
            if dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64, pl.Float64, pl.Float32]:
                # -99999 값 제외하고 중앙값 계산
                filtered_df = df.filter(pl.col(col) != -99999)
                median_value = filtered_df[col].median()
                
                # 정수형이면 반올림
                if dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                    return int(round(median_value))
                return median_value
            else:
                return ""
        
        # 최빈값으로 대체
        elif method == "mode":
            try:
                # -99999 값 제외하고 최빈값 계산
                if dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64, pl.Float64, pl.Float32]:
                    filtered_df = df.filter((pl.col(col) != -99999) & (~pl.col(col).is_null()))
                else:
                    filtered_df = df.filter(~pl.col(col).is_null())
                
                # 값 빈도 계산
                value_counts = filtered_df[col].value_counts()
                if len(value_counts) > 0:
                    # 가장 많이 나타나는 값 찾기
                    max_count_idx = value_counts["count"].argmax()
                    mode_value = value_counts[col][max_count_idx]
                    return mode_value
                else:
                    # 유효한 값이 없으면 기본값 반환
                    if dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                        return 0
                    elif dtype in [pl.Float64, pl.Float32]:
                        return 0.0
                    elif dtype == pl.Boolean:
                        return False
                    else:
                        return ""
            except:
                # 오류 발생 시 기본값 반환
                if dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                    return 0
                elif dtype in [pl.Float64, pl.Float32]:
                    return 0.0
                elif dtype == pl.Boolean:
                    return False
                else:
                    return ""
        
        # 빈 문자열로 대체 (문자열 컬럼만)
        elif method == "empty_string":
            if dtype in [pl.Utf8, pl.String, pl.Categorical]:
                return ""
            else:
                # 숫자형이면 0 반환
                if dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                    return 0
                elif dtype in [pl.Float64, pl.Float32]:
                    return 0.0
                elif dtype == pl.Boolean:
                    return False
                else:
                    return ""
        
        # 앞의 값으로 대체 (forward fill) 및 뒤의 값으로 대체 (backward fill)
        # 이 두 방법은 미리보기에서는 간단한 값으로 표시하고, 실제 적용 시 fill_null 메서드를 사용
        elif method == "forward" or method == "backward":
            # 미리보기용 대체값 - 실제 적용 시에는 다른 방식 사용
            non_null_values = df.filter(~pl.col(col).is_null() & (pl.col(col) != -99999))[col]
            if len(non_null_values) > 0:
                sample_value = non_null_values[0]
                return sample_value
            else:
                # 유효한 값이 없으면 기본값 반환
                if dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                    return 0
                elif dtype in [pl.Float64, pl.Float32]:
                    return 0.0
                elif dtype == pl.Boolean:
                    return False
                else:
                    return ""
        
        # 기본 대체값
        else:
            if dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                return 0
            elif dtype in [pl.Float64, pl.Float32]:
                return 0.0
            elif dtype == pl.Boolean:
                return False
            else:
                return ""