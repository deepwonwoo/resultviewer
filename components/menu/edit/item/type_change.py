import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, no_update, exceptions, ctx, ALL

from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions, SYSTEM_COLUMNS
from components.menu.edit.utils import find_tab_in_layout

class TypeChanges:
    def __init__(self):
        # 지원하는 데이터 타입 정의
        self.supported_types = [
            {"label": "문자열 (String)", "value": "str"},
            {"label": "정수 (Integer)", "value": "int"},
            {"label": "실수 (Float)", "value": "float"},
            {"label": "불리언 (Boolean)", "value": "bool"},
        ]
        
        self.type_mapping = {
            "str": pl.Utf8,
            "int": pl.Int64,
            "float": pl.Float64,
            "bool": pl.Boolean,
        }
        
        # 타입별 변환 옵션
        self.conversion_options = {
            "str": [
                {"label": "기본 변환", "value": "default"},
                {"label": "소문자로 변환", "value": "lowercase"},
                {"label": "대문자로 변환", "value": "uppercase"}
            ],
            "int": [
                {"label": "기본 변환", "value": "default"},
                {"label": "반올림", "value": "round"},
                {"label": "내림", "value": "floor"},
                {"label": "올림", "value": "ceil"}
            ],
            "float": [
                {"label": "기본 변환", "value": "default"},
                {"label": "소수점 2자리", "value": "2decimal"},
                {"label": "소수점 4자리", "value": "4decimal"}
            ],
            "bool": [
                {"label": "기본 변환", "value": "default"},
                {"label": "문자열 (true/false, yes/no 등) 인식", "value": "string_recognize"}
            ],
        }
        
    def button_layout(self):
        return dbpc.Button(
            "Type Changes", 
            id="type-changes-btn", 
            icon="data-lineage", 
            minimal=True, 
            outlined=True
        )
        
    def tab_layout(self):
        return dmc.Paper(
            children=[
                dmc.Group([
                    dbpc.EntityTitle(
                        title="Type Changes", 
                        heading="H5", 
                        icon="data-lineage"
                    )
                ], grow=True),
                dmc.Space(h=10),
                
                # 컬럼 선택 MultiSelect
                dmc.MultiSelect(
                    id="type-changes-column-select",
                    label="컬럼 선택",
                    description="타입을 변경할 컬럼을 선택하세요 (복수 선택 가능)",
                    placeholder="컬럼 선택...",
                    required=True,
                    searchable=True,
                    clearable=True,
                    data=[],
                    size="md",
                    leftSection=dbpc.Icon(icon="properties"),
                ),
                
                dmc.Space(h=20),
                
                # 타입 변경 정보 표시 영역
                html.Div(id="type-changes-info-container"),
                
                dmc.Space(h=20),
                
                # 대상 타입 선택
                dmc.Select(
                    id="type-changes-target-type",
                    label="변환할 데이터 타입",
                    description="선택한 컬럼을 어떤 타입으로 변환할지 선택하세요",
                    placeholder="데이터 타입 선택...",
                    data=self.supported_types,
                    size="md",
                    leftSection=dbpc.Icon(icon="polygon-filter"),
                ),
                
                dmc.Space(h=15),
                
                # 변환 옵션 선택 (타입에 따라 동적으로 변경)
                dmc.Select(
                    id="type-changes-conversion-option",
                    label="변환 옵션",
                    description="데이터 변환 방식을 선택하세요",
                    placeholder="변환 옵션 선택...",
                    data=[],
                    size="md",
                    disabled=True,
                ),
                
                dmc.Space(h=15),
                
                # 변환 실패 처리 옵션
                dmc.RadioGroup(
                    id="type-changes-fail-option",
                    label="변환 실패 시 처리 방법",
                    description="변환할 수 없는 값이 있을 경우 어떻게 처리할지 선택하세요",
                    value="null",
                    size="sm",
                    children=[
                        dmc.Radio(
                            value="null", 
                            label="Null 값으로 대체"
                        ),
                        dmc.Radio(
                            value="default", 
                            label="기본값으로 대체"
                        ),
                        dmc.Radio(
                            value="error", 
                            label="오류 발생 (변환 취소)"
                        ),
                    ],
                ),
                
                # 기본값 입력 필드 (fail_option이 'default'일 때만 표시)
                html.Div(
                    id="type-changes-default-value-container",
                    style={"display": "none"},
                    children=[
                        dmc.TextInput(
                            id="type-changes-default-value",
                            label="기본값",
                            description="변환 실패 시 적용할 기본값을 입력하세요",
                            placeholder="기본값 입력...",
                            size="sm",
                        ),
                    ],
                ),
                
                dmc.Space(h=20),
                
                # 미리보기 영역
                dmc.Paper(
                    id="type-changes-preview-container",
                    withBorder=True,
                    p="sm",
                    style={"maxHeight": "200px", "overflow": "auto"},
                    children=[
                        dmc.Text("미리보기: 컬럼과 타입을 선택하면 변환 예시가 표시됩니다.", size="sm", c="dimmed"),
                    ],
                ),
                
                dmc.Space(h=20),
                
                # 필터링된 데이터만 적용 옵션
                dmc.Checkbox(
                    id="type-changes-filtered-only",
                    label="필터링된 데이터에만 적용",
                    description="현재 필터링된 데이터에만 타입 변환을 적용합니다",
                    size="sm",
                ),
                
                dmc.Space(h=20),
                
                # 변환 실행 버튼
                dmc.Group([
                    dbpc.Button(
                        "Apply", 
                        id="type-changes-apply-btn", 
                        outlined=True,
                        icon="tick",
                        intent="primary"
                    ),
                ], justify="center"),
                
                # 도움말 섹션
                dmc.Space(h=20),
                dmc.Accordion(
                    value="",
                    children=[
                        dmc.AccordionItem(
                            [
                                dmc.AccordionControl("도움말"),
                                dmc.AccordionPanel([
                                    dmc.Text("1. 타입을 변경할 컬럼을 하나 이상 선택하세요."),
                                    dmc.Text("2. 변환할 데이터 타입을 선택하세요."),
                                    dmc.Text("3. 필요한 경우 변환 옵션과 실패 처리 방법을 설정하세요."),
                                    dmc.Text("4. 미리보기를 확인하고 Apply 버튼을 클릭하세요."),
                                    dmc.Text("5. 시스템 컬럼(uniqid, group, childCount)은 변경할 수 없습니다.")
                                ])
                            ],
                            value="help"
                        )
                    ]
                )
            ],
            p="md",
            shadow="sm",
            radius="xs",
            withBorder=True
        )


    def register_callbacks(self, app):
        """콜백 함수 등록"""
        
        @app.callback(
            Output("flex-layout", "model", allow_duplicate=True),
            Output("toaster", "toasts", allow_duplicate=True),
            Input("type-changes-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True
        )
        def handle_type_changes_button_click(n_clicks, current_model):
            """Type Changes 버튼 클릭 시 우측 패널에 탭 추가"""
            if n_clicks is None:
                raise exceptions.PreventUpdate
                
            dff = displaying_df()
            if dff is None:
                return no_update, [dbpc.Toast(message=f"데이터가 로드되지 않았습니다", intent="warning", icon="warning-sign")]

            # 기존 탭 검색
            tab_search_result = find_tab_in_layout(current_model, "type-changes-tab")
            
            # 이미 탭이 존재한다면
            if tab_search_result["found"]:
                # borders에 있을 경우 해당 탭으로 이동
                if tab_search_result["location"] == "borders":
                    patched_model = Patch()
                    border_index = tab_search_result["border_index"]
                    tab_index = tab_search_result["tab_index"]
                    patched_model["borders"][border_index]["selected"] = tab_index
                    return patched_model, no_update
                else:
                    # 메인 레이아웃에 있다면 경고 메시지 출력
                    return no_update, [dbpc.Toast(message=f"기존 탭이 레이아웃에 있습니다.", intent="warning", icon="info-sign")]
            
            # 탭이 존재하지 않으면 정상적으로 진행
            right_border_index = next(
                (i for i, b in enumerate(current_model["borders"]) if b["location"] == "right"), 
                None
            )
            
            # 새로운 탭 정의
            new_tab = {
                "type": "tab",
                "name": "Type Changes",
                "component": "button",
                "enableClose": True,
                "id": "type-changes-tab"
            }

            patched_model = Patch()

            if right_border_index is not None:
                # 기존 right border 수정
                patched_model["borders"][right_border_index]["children"].append(new_tab)
                patched_model["borders"][right_border_index]["selected"] = len(current_model["borders"][right_border_index]["children"])
            else:
                # right border가 없으면 새로 추가
                patched_model["borders"].append({
                    "type": "border", 
                    "location": "right", 
                    "size": 400, 
                    "selected": 0, 
                    "children": [new_tab]
                })
                    
            return patched_model, no_update
            
        @app.callback(
            Output("type-changes-column-select", "data"),
            Input("type-changes-btn", "n_clicks"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True
        )
        def update_column_list(n_clicks, columnDefs):
            """Type Changes 버튼 클릭 시 컬럼 목록 로드"""
            if n_clicks is None or not columnDefs:
                return []

            # 컬럼 필터링 (보호할 컬럼 제외)
            column_data = [
                {"label": col["field"], "value": col["field"]} 
                for col in columnDefs if col["field"] not in SYSTEM_COLUMNS
            ]
            
            return column_data
            
        @app.callback(
            Output("type-changes-info-container", "children"),
            Input("type-changes-column-select", "value"),
            prevent_initial_call=True
        )
        def display_column_type_info(selected_columns):
            """선택한 컬럼의 현재 데이터 타입 정보 표시"""
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
                    
                    if dtype == pl.Int64 or dtype == pl.Int32 or dtype == pl.UInt32 or dtype == pl.UInt64:
                        readable_type = "정수 (Integer)"
                        type_color = "blue"
                    elif dtype == pl.Float64 or dtype == pl.Float32:
                        readable_type = "실수 (Float)"
                        type_color = "cyan"
                    elif dtype == pl.Boolean:
                        readable_type = "불리언 (Boolean)"
                        type_color = "green"
                    elif dtype == pl.Utf8 or dtype == pl.String:
                        readable_type = "문자열 (String)"
                        type_color = "orange"
                    elif dtype == pl.Categorical:
                        readable_type = "카테고리 (Categorical)"
                        type_color = "pink"
                    
                    # 컬럼의 고유값 개수와 Null 값 정보 (최대 100개 샘플에서)
                    sample = df[col].head(100)
                    null_count = sample.null_count()
                    total_count = len(sample)
                    null_percent = (null_count / total_count * 100) if total_count > 0 else 0
                    
                    # 고유값 개수 계산 (최대 100개 샘플에서)
                    unique_count = len(sample.unique())
                    
                    # 컬럼 정보 컴포넌트 생성
                    info_component = dmc.Paper(
                        withBorder=True,
                        p="xs",
                        mb="xs",
                        children=[
                            dmc.Group([
                                dmc.Text(f"컬럼: {col}", w=500),
                                dmc.Badge(readable_type, color=type_color),
                            ], justify="apart"),
                            dmc.Text(
                                f"Null 값: {null_count}/{total_count} ({null_percent:.1f}%), 고유값: {unique_count}개",
                                size="xs",
                                c="dimmed"
                            ),
                        ]
                    )
                    
                    info_components.append(info_component)
                    
                except Exception as e:
                    logger.error(f"컬럼 {col} 정보 표시 오류: {str(e)}")
                    info_components.append(
                        dmc.Alert(
                            f"컬럼 '{col}' 정보를 가져올 수 없습니다: {str(e)}",
                            color="red",
                            variant="light",
                            mb="xs"
                        )
                    )
            
            return info_components
            
        @app.callback(
            Output("type-changes-conversion-option", "data"),
            Output("type-changes-conversion-option", "disabled"),
            Input("type-changes-target-type", "value"),
            prevent_initial_call=True
        )
        def update_conversion_options(target_type):
            """선택한 타입에 따라 변환 옵션 업데이트"""
            if not target_type:
                return [], True
                
            options = self.conversion_options.get(target_type, [])
            return options, False
            
        @app.callback(
            Output("type-changes-default-value-container", "style"),
            Input("type-changes-fail-option", "value"),
            prevent_initial_call=True
        )
        def toggle_default_value_input(fail_option):
            """실패 처리 옵션에 따라 기본값 입력 필드 표시/숨김"""
            if fail_option == "default":
                return {"display": "block"}
            return {"display": "none"}
            
        @app.callback(
            Output("type-changes-preview-container", "children"),
            [
                Input("type-changes-column-select", "value"),
                Input("type-changes-target-type", "value"),
                Input("type-changes-conversion-option", "value")
            ],
            prevent_initial_call=True
        )
        def update_preview(selected_columns, target_type, conversion_option):
            """선택한 컬럼과 타입에 따라 변환 미리보기 표시"""
            if not selected_columns or not target_type:
                return [dmc.Text("미리보기: 컬럼과 타입을 선택하면 변환 예시가 표시됩니다.", size="sm", c="dimmed")]
                
            df = SSDF.dataframe
            preview_content = []
            
            # 첫 번째 선택된 컬럼에 대해서만 미리보기 제공
            col = selected_columns[0]
            
            try:
                # 최대 5개의 샘플 값 선택
                sample_values = df[col].head(5).to_list()
                
                # Null이 아닌 값만 필터링
                sample_values = [v for v in sample_values if v is not None]
                
                if not sample_values:
                    return [dmc.Text("선택한 컬럼에 표시할 샘플 데이터가 없습니다.", size="sm", c="dimmed")]
                
                # 변환 함수 선택
                conversion_func = self._get_conversion_function(target_type, conversion_option)
                
                # 샘플 값 변환 시도
                converted_values = []
                for value in sample_values:
                    try:
                        converted = conversion_func(value)
                        converted_values.append((value, converted, "성공"))
                    except Exception as e:
                        converted_values.append((value, str(e), "실패"))
                
                # 미리보기 테이블 생성
                header = [
                    dmc.TableThead(
                        dmc.TableTr([
                            dmc.TableTh("원본 값", style={"width": "40%"}),
                            dmc.TableTh("변환 값", style={"width": "40%"}),
                            dmc.TableTh("결과", style={"width": "20%"})
                        ])
                    )
                ]
                
                rows = [
                    dmc.TableTr([
                        dmc.TableTd(str(orig)),
                        dmc.TableTd(str(conv)),
                        dmc.TableTd(
                            dmc.Badge(
                                status, 
                                color="green" if status == "성공" else "red",
                                variant="light",
                                size="sm"
                            )
                        )
                    ])
                    for orig, conv, status in converted_values
                ]
                
                preview_table = dmc.Table(
                    [*header, dmc.TableTbody(rows)],
                    striped=True,
                    highlightOnHover=True,
                    withTableBorder=True,
                    withColumnBorders=True,
                )
                
                preview_content = [
                    dmc.Text(f"컬럼 '{col}'의 변환 미리보기:", size="sm", w=500, mb="xs"),
                    preview_table
                ]
                
            except Exception as e:
                logger.error(f"미리보기 생성 오류: {str(e)}")
                preview_content = [
                    dmc.Alert(
                        f"미리보기를 생성할 수 없습니다: {str(e)}",
                        color="red",
                        variant="light"
                    )
                ]
                
            return preview_content
            
        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            [
                Input("type-changes-apply-btn", "n_clicks")
            ],
            [
                State("type-changes-column-select", "value"),
                State("type-changes-target-type", "value"),
                State("type-changes-conversion-option", "value"),
                State("type-changes-fail-option", "value"),
                State("type-changes-default-value", "value"),
                State("type-changes-filtered-only", "checked")
            ],
            prevent_initial_call=True
        )
        def apply_type_changes(n_clicks, selected_columns, target_type, conversion_option, 
                             fail_option, default_value, filtered_only):
            """타입 변환 적용"""
            if not n_clicks or not selected_columns or not target_type:
                raise exceptions.PreventUpdate
                
            try:
                # 변환 함수 선택
                conversion_func = self._get_conversion_function(target_type, conversion_option)
                
                # Polars 데이터 타입 매핑
                target_polars_type = self.type_mapping.get(target_type)
                
                if not target_polars_type:
                    return ([dbpc.Toast(
                        message=f"지원하지 않는 데이터 타입입니다: {target_type}",
                        intent="danger",
                        icon="error"
                    )], no_update)
                
                # 원본 데이터프레임 복사
                df = SSDF.dataframe.clone()
                
                # 필터링된 데이터만 처리하는 경우
                filtered_ids = None
                if filtered_only:
                    from components.grid.dag.SSRM.apply_filter import apply_filters
                    filtered_df = apply_filters(df, SSDF.request)
                    if "uniqid" in filtered_df.columns:
                        filtered_ids = filtered_df["uniqid"]
                
                # 각 컬럼에 대해 타입 변환 수행
                failed_columns = []
                successful_columns = []
                
                for col in selected_columns:
                    try:
                        # 변환 실패 처리 옵션에 따른 strict 설정
                        strict = fail_option == "error"
                        
                        # 기본값 설정
                        fill_value = None
                        if fail_option == "default" and default_value is not None:
                            # 타입에 맞게 기본값 변환
                            try:
                                if target_type == "int":
                                    fill_value = int(default_value)
                                elif target_type == "float":
                                    fill_value = float(default_value)
                                elif target_type == "bool":
                                    fill_value = default_value.lower() in ["true", "1", "yes", "y"]
                                else:
                                    fill_value = default_value
                            except:
                                fill_value = None
                        
                        # 변환 및 적용
                        if filtered_only and filtered_ids is not None:
                            # 필터링된 행에만 적용
                            if conversion_option and conversion_option != "default":
                                # 특별한 변환 옵션이 있는 경우
                                converted_values = df.filter(pl.col("uniqid").is_in(filtered_ids))[col].map_elements(
                                    conversion_func, return_dtype=target_polars_type
                                )
                                df = df.with_columns([
                                    pl.when(pl.col("uniqid").is_in(filtered_ids))
                                    .then(converted_values)
                                    .otherwise(pl.col(col))
                                    .alias(col)
                                ])
                            else:
                                # 기본 변환
                                df = df.with_columns([
                                    pl.when(pl.col("uniqid").is_in(filtered_ids))
                                    .then(pl.col(col).cast(target_polars_type, strict=strict))
                                    .otherwise(pl.col(col))
                                    .alias(col)
                                ])
                        else:
                            # 전체 적용
                            if conversion_option and conversion_option != "default":
                                # 특별한 변환 옵션이 있는 경우
                                if target_polars_type == pl.Boolean and conversion_option == "string_recognize":
                                    # 불리언 문자열 인식 로직
                                    df = df.with_columns(
                                        pl.when(pl.col(col).cast(pl.Utf8).str.to_lowercase().is_in(["true", "1", "yes", "y", "on"]))
                                        .then(True)
                                        .when(pl.col(col).cast(pl.Utf8).str.to_lowercase().is_in(["false", "0", "no", "n", "off"]))
                                        .then(False)
                                        .otherwise(None)
                                        .alias(col)
                                    )
                                else:
                                    # 사용자 정의 변환 함수 적용
                                    df = df.with_columns(
                                        pl.col(col).map_elements(conversion_func, return_dtype=target_polars_type).alias(col)
                                    )
                            else:
                                # 기본 타입 변환
                                if fail_option == "null":
                                    df = df.with_columns(pl.col(col).cast(target_polars_type, strict=False).alias(col))
                                elif fail_option == "default" and fill_value is not None:
                                    # 변환 실패 시 기본값으로 대체
                                    try:
                                        df = df.with_columns(
                                            pl.coalesce(
                                                pl.col(col).cast(target_polars_type, strict=False),
                                                pl.lit(fill_value)
                                            ).alias(col)
                                        )
                                    except:
                                        df = df.with_columns(pl.col(col).cast(target_polars_type, strict=False).alias(col))
                                else:
                                    # strict=True로 설정하면 변환 실패 시 예외 발생
                                    df = df.with_columns(pl.col(col).cast(target_polars_type, strict=strict).alias(col))
                        
                        successful_columns.append(col)
                        
                    except Exception as e:
                        logger.error(f"컬럼 '{col}' 타입 변환 실패: {str(e)}")
                        failed_columns.append((col, str(e)))
                
                # 실패한 컬럼이 있는 경우
                if failed_columns:
                    error_messages = "\n".join([f"- {col}: {err}" for col, err in failed_columns])
                    
                    # 일부 컬럼만 성공한 경우
                    if successful_columns:
                        SSDF.dataframe = df
                        updated_columnDefs = generate_column_definitions(df)
                        
                        return ([dbpc.Toast(
                            message=f"{len(successful_columns)}개 컬럼 변환 성공, {len(failed_columns)}개 실패\n{error_messages}",
                            intent="warning",
                            icon="warning-sign",
                            timeout=4000
                        )], updated_columnDefs)
                    else:
                        # 모든 컬럼 변환 실패
                        return ([dbpc.Toast(
                            message=f"모든 컬럼 변환 실패:\n{error_messages}",
                            intent="danger",
                            icon="error",
                            timeout=4000
                        )], no_update)
                
                # 모든 컬럼 변환 성공
                SSDF.dataframe = df
                updated_columnDefs = generate_column_definitions(df)
                
                return ([dbpc.Toast(
                    message=f"{len(successful_columns)}개 컬럼의 타입이 '{target_type}'으로 변환되었습니다.",
                    intent="success",
                    icon="endorsed",
                    timeout=3000
                )], updated_columnDefs)
                
            except Exception as e:
                # 전체 처리 오류
                logger.error(f"타입 변환 처리 오류: {str(e)}")
                return ([dbpc.Toast(
                    message=f"타입 변환 처리 오류: {str(e)}",
                    intent="danger",
                    icon="error"
                )], no_update)
    
    def _get_conversion_function(self, target_type, conversion_option):
        """타입과 변환 옵션에 따른 변환 함수 반환"""
        
        # 기본 변환 함수 (단순 타입 캐스팅)
        default_conversion = {
            "str": lambda x: str(x) if x is not None else "",
            "int": lambda x: int(float(x)) if x is not None else None,
            "float": lambda x: float(x) if x is not None else None,
            "bool": lambda x: bool(x) if x is not None else None,
            "date": lambda x: pd.to_datetime(x).date() if x is not None else None
        }
        
        # 변환 옵션이 없거나 기본 변환인 경우
        if not conversion_option or conversion_option == "default":
            return default_conversion.get(target_type, lambda x: x)
        
        # 문자열 변환 옵션
        if target_type == "str":
            if conversion_option == "lowercase":
                return lambda x: str(x).lower() if x is not None else ""
            elif conversion_option == "uppercase":
                return lambda x: str(x).upper() if x is not None else ""
        
        # 정수 변환 옵션
        elif target_type == "int":
            if conversion_option == "round":
                return lambda x: int(round(float(x))) if x is not None else None
            elif conversion_option == "floor":
                import math
                return lambda x: int(math.floor(float(x))) if x is not None else None
            elif conversion_option == "ceil":
                import math
                return lambda x: int(math.ceil(float(x))) if x is not None else None
        
        # 실수 변환 옵션
        elif target_type == "float":
            if conversion_option == "2decimal":
                return lambda x: round(float(x), 2) if x is not None else None
            elif conversion_option == "4decimal":
                return lambda x: round(float(x), 4) if x is not None else None
        
        # 불리언 변환 옵션
        elif target_type == "bool":
            if conversion_option == "string_recognize":
                return lambda x: str(x).lower() in ["true", "1", "yes", "y", "on"] if x is not None else None
        
        # 날짜 변환 옵션
        elif target_type == "date":
            if conversion_option == "iso":
                import pandas as pd
                return lambda x: pd.to_datetime(x, format="%Y-%m-%d").date() if x is not None else None
        
        # 기본 변환 함수 반환
        return default_conversion.get(target_type, lambda x: x)