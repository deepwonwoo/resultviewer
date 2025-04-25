import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, no_update, exceptions, ctx, ALL

from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions, SYSTEM_COLUMNS
from components.menu.edit.utils import handle_tab_button_click

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
        """개선된 타입 변경 탭 레이아웃"""
        return dmc.Paper(
        children=[
            dmc.Group([dbpc.EntityTitle(title="Type Changes", heading="H5", icon="data-lineage")], grow=True),
            dmc.Space(h=10),
            
            # 컬럼 선택 영역 (UI 개선)
            dmc.Paper(
                withBorder=True,
                p="md",
                style={"marginBottom": "15px"},
                children=[
                    dmc.Text("1. 변환할 컬럼 선택", fw=700, mb=5),
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
                        leftSection=dbpc.Icon(icon="properties")
                    ),
                    dmc.Space(h=10),
                    html.Div(id="type-changes-info-container"),
                ]
            ),
            
            # 타입 변환 영역 (UI 개선)
            dmc.Paper(
                withBorder=True,
                p="md",
                style={"marginBottom": "15px"},
                children=[
                    dmc.Text("2. 데이터 타입 변환 설정", fw=700, mb=5),
                    
                    # 대상 타입 선택 (아이콘 추가)
                    dmc.Select(
                        id="type-changes-target-type", 
                        label="변환할 데이터 타입", 
                        description="선택한 컬럼을 어떤 타입으로 변환할지 선택하세요", 
                        placeholder="데이터 타입 선택...",
                        data=[
                            {"label": "📝 문자열 (String)", "value": "str"},
                            {"label": "🔢 정수 (Integer)", "value": "int"},
                            {"label": "📊 실수 (Float)", "value": "float"},
                            {"label": "✓✗ 불리언 (Boolean)", "value": "bool"}
                        ], 
                        size="md",
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
                        disabled=True
                    ),
                    
                    # 현재 선택한 변환 옵션에 대한 설명
                    html.Div(id="type-changes-option-description", style={"marginTop": "10px"}),
                    
                    dmc.Space(h=15),
                    
                    # 변환 실패 처리 옵션
                    dmc.RadioGroup(
                        id="type-changes-fail-option", 
                        label="변환 실패 시 처리 방법", 
                        description="변환할 수 없는 값이 있을 경우 어떻게 처리할지 선택하세요", 
                        value="null", 
                        size="sm", 
                        children=[
                            dmc.Radio(value="null", label="Null 값으로 대체"), 
                            dmc.Radio(value="default", label="기본값으로 대체"), 
                            dmc.Radio(value="error", label="오류 발생 (변환 취소)")
                        ]
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
                                size="sm"
                            )
                        ]
                    ),
                ]
            ),
            
            # 미리보기 영역
            dmc.Space(h=10),
            dmc.Text("3. 변환 미리보기", fw=700, mb=5),
            dmc.Paper(
                id="type-changes-preview-container", 
                withBorder=True, 
                p="sm", 
                style={"maxHeight": "300px", "overflow": "auto"}, 
                children=[
                    dmc.Text("미리보기: 컬럼과 타입을 선택하면 변환 예시가 표시됩니다.", size="sm", c="dimmed")
                ]
            ),
            
            dmc.Space(h=20),
            
            # 변환 실행 버튼
            dmc.Group(
                [
                    dbpc.Button(
                        "Apply", 
                        id="type-changes-apply-btn", 
                        outlined=True, 
                        icon="tick", 
                        intent="primary",
                        loading=False,  # 로딩 상태 추가
                    )
                ], 
                justify="center"
            ),
            
            # 도움말 섹션 
            dmc.Space(h=20),
            dmc.Accordion(
                value="", 
                children=[
                    dmc.AccordionItem(
                        [
                            dmc.AccordionControl("도움말"), 
                            dmc.AccordionPanel([
                                dmc.Text("1. 타입을 변경할 컬럼을 하나 이상 선택하세요.", size="sm"),
                                dmc.Text("2. 변환할 데이터 타입을 선택하세요.", size="sm"),
                                dmc.Text("3. 필요한 경우 변환 옵션과 실패 처리 방법을 설정하세요.", size="sm"),
                                dmc.Text("4. 미리보기를 확인하고 Apply 버튼을 클릭하세요.", size="sm"),
                                dmc.Space(h=10),
                                dmc.Text("💡 타입 변환 주의사항:", size="sm", fw=700),
                                dmc.Text("- 문자열 → 숫자 변환: 숫자 형식이 아닌 문자열은 변환에 실패합니다. (예: 'abc' → 숫자 변환 불가)", size="sm"),
                                dmc.Text("- 소수점 → 정수 변환: 소수점은 반올림/내림/올림 옵션에 따라 처리됩니다.", size="sm"),
                                dmc.Text("- 불리언 변환: 'true', 'yes', '1', 'y'는 True로, 'false', 'no', '0', 'n'은 False로 변환됩니다.", size="sm"),
                                dmc.Text("- 시스템 컬럼(uniqid, group, childCount 등)은 변경할 수 없습니다.", size="sm"),
                            ])
                        ], 
                        value="help"
                    )
                ]
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
            Input("add-row-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True
        )
        def handle_add_row_button_click(n_clicks, current_model):
            """Add Row 버튼 클릭 시 우측 패널에 탭 추가"""
            return handle_tab_button_click(n_clicks, current_model, "type-changes-tab", "Type Changes")

            
        @app.callback(
            Output("type-changes-column-select", "data"),
            Input("type-changes-btn", "n_clicks"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True
        )
        def update_column_list(n_clicks, columnDefs):
            """Type Changes 버튼 클릭 시 컬럼 목록 로드 - 보호 컬럼 필터링 강화"""
            if n_clicks is None or not columnDefs:
                return []
            # 컬럼 필터링 (보호할 컬럼 제외)
            column_data = []
            
            df = SSDF.dataframe
            for col in columnDefs:
                col_field = col.get("field", "")
                if col_field not in SYSTEM_COLUMNS:
                    # 컬럼 데이터 타입 확인 및 아이콘 추가
                    col_type = "unknown"
                    type_icon = "❓"
                    
                    if col_field in df.columns:
                        dtype = df[col_field].dtype
                        if dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                            col_type = "integer"
                            type_icon = "🔢"
                        elif dtype in [pl.Float64, pl.Float32]:
                            col_type = "float"
                            type_icon = "📊"
                        elif dtype == pl.Boolean:
                            col_type = "boolean"
                            type_icon = "✓✗"
                        elif dtype in [pl.Utf8, pl.String, pl.Categorical]:
                            col_type = "string"
                            type_icon = "📝"
                            
                    column_data.append({
                        "label": f"{type_icon} {col_field} ({col_type})",
                        "value": col_field
                    })

            return column_data


        @app.callback(
            Output("type-changes-info-container", "children"),
            Input("type-changes-column-select", "value"),
            prevent_initial_call=True
        )
        def display_column_type_info(selected_columns):
            """선택한 컬럼의 현재 데이터 타입 정보 표시 - 시각적 개선"""
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
                    type_icon = "❓"

                    if dtype == pl.Int64 or dtype == pl.Int32 or dtype == pl.UInt32 or dtype == pl.UInt64:
                        readable_type = "정수 (Integer)"
                        type_color = "blue"
                        type_icon = "🔢"
                    elif dtype == pl.Float64 or dtype == pl.Float32:
                        readable_type = "실수 (Float)"
                        type_color = "cyan"
                        type_icon = "📊"
                    elif dtype == pl.Boolean:
                        readable_type = "불리언 (Boolean)"
                        type_color = "green"
                        type_icon = "✓✗"
                    elif dtype == pl.Utf8 or dtype == pl.String:
                        readable_type = "문자열 (String)"
                        type_color = "orange"
                        type_icon = "📝"
                    elif dtype == pl.Categorical:
                        readable_type = "카테고리 (Categorical)"
                        type_color = "pink"
                        type_icon = "🏷️"
                    elif dtype == pl.Date:
                        readable_type = "날짜 (Date)"
                        type_color = "violet"
                        type_icon = "📅"
                    elif dtype == pl.Datetime:
                        readable_type = "날짜/시간 (Datetime)"
                        type_color = "indigo"
                        type_icon = "⏰"

                    # 샘플 값 표시 (최대 1개)
                    sample_values = []
                    sample = df[col].drop_nulls().head(1)
                    
                    if len(sample) > 0:
                        sample_values.append(str(sample[0]))
                    
                    sample_text = ", ".join(sample_values) if sample_values else "값 없음"
                        
                    # 고유값 개수 계산 (최대 1000개 샘플에서)
                    sample_size = min(1000, df.height)
                    sample_df = df.slice(0, sample_size)
                    unique_count = len(sample_df[col].unique())
                    
                    # Null 값 정보 (최대 1000개 샘플에서)
                    null_count = sample_df[col].null_count()
                    total_count = len(sample_df)
                    null_percent = (null_count / total_count * 100) if total_count > 0 else 0

                    # 컬럼 정보 컴포넌트 생성
                    info_component = dmc.Paper(
                        withBorder=True, 
                        p="xs", 
                        mb="xs", 
                        children=[
                            dmc.Group([
                                dmc.Group([
                                    dmc.Text(type_icon, size="xl", mr=0), 
                                    dmc.Text(f"컬럼: {col}", w=500)
                                ], gap="xs"),
                                dmc.Badge(readable_type, color=type_color, size="lg")
                            ], justify="apart"),
                            
                            dmc.Divider(my="xs"),
                            
                            # 데이터 요약 정보
                            dmc.SimpleGrid(
                                cols=2,
                                spacing="xs",
                                children=[
                                    dmc.Text(f"Null 값: {null_count}/{total_count} ({null_percent:.1f}%)", size="xs"),
                                    dmc.Text(f"고유값: {unique_count}개", size="xs"),
                                ]
                            ),
                            
                            # 샘플 값 표시
                            dmc.Text("샘플 값: " + sample_text, size="xs", c="dimmed", mt="xs"),
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
            Output("type-changes-option-description", "children"),
            [Input("type-changes-target-type", "value"), Input("type-changes-conversion-option", "value")],
            prevent_initial_call=True
        )
        def update_option_description(target_type, conversion_option):
            """선택된 변환 옵션에 대한 설명 표시"""
            if not target_type or not conversion_option or conversion_option == "default":
                return []
            
            descriptions = {
                "str": {
                    "lowercase": "모든 문자를 소문자로 변환합니다. (예: 'ABC' → 'abc')",
                    "uppercase": "모든 문자를 대문자로 변환합니다. (예: 'abc' → 'ABC')",
                    "titlecase": "각 단어의 첫 글자를 대문자로 변환합니다. (예: 'hello world' → 'Hello World')"
                },
                "int": {
                    "round": "소수점 값을 반올림하여 정수로 변환합니다. (예: 3.7 → 4)",
                    "floor": "소수점 값을 내림하여 정수로 변환합니다. (예: 3.7 → 3)",
                    "ceil": "소수점 값을 올림하여 정수로 변환합니다. (예: 3.2 → 4)"
                },
                "float": {
                    "2decimal": "소수점 2자리까지 유지하고 반올림합니다. (예: 3.14159 → 3.14)",
                    "4decimal": "소수점 4자리까지 유지하고 반올림합니다. (예: 3.14159 → 3.1416)",
                    "scientific": "과학적 표기법으로 변환합니다. (예: 1000000 → 1.00e+6)"
                },
                "bool": {
                    "string_recognize": "문자열을 불리언으로 해석합니다. 'true', 'yes', '1', 'y'는 True로, 'false', 'no', '0', 'n'은 False로 변환합니다."
                }
            }
            
            description = descriptions.get(target_type, {}).get(conversion_option, "")
            
            if description:
                return dmc.Alert(description, color="blue", variant="light", withCloseButton=False)
            
            return []


        @app.callback(
            Output("type-changes-preview-container", "children"),
            [Input("type-changes-column-select", "value"), 
            Input("type-changes-target-type", "value"), 
            Input("type-changes-conversion-option", "value"),
            Input("type-changes-fail-option", "value"),
            Input("type-changes-default-value", "value")],
            prevent_initial_call=True
        )
        def update_preview(selected_columns, target_type, conversion_option, fail_option, default_value):
            """선택한 컬럼과 타입에 따라 변환 미리보기 표시 - 개선"""
            if not selected_columns or not target_type:
                return [dmc.Text("미리보기: 컬럼과 타입을 선택하면 변환 예시가 표시됩니다.", size="sm", c="dimmed")]

            df = SSDF.dataframe
            preview_content = []

            # 변환 설정 요약
            target_type_name = {
                "str": "문자열 (String)",
                "int": "정수 (Integer)",
                "float": "실수 (Float)",
                "bool": "불리언 (Boolean)"
            }.get(target_type, target_type)
            
            conversion_option_name = "기본 변환"
            if conversion_option and conversion_option != "default":
                conversion_option_names = {
                    "lowercase": "소문자 변환",
                    "uppercase": "대문자 변환",
                    "round": "반올림",
                    "floor": "내림",
                    "ceil": "올림",
                    "2decimal": "소수점 2자리",
                    "4decimal": "소수점 4자리",
                    "scientific": "과학적 표기법",
                    "string_recognize": "문자열 인식"
                }
                conversion_option_name = conversion_option_names.get(conversion_option, conversion_option)
            
            fail_option_name = {
                "null": "Null 값으로 대체",
                "default": f"기본값({default_value})으로 대체" if default_value else "기본값으로 대체",
                "error": "오류 발생 (변환 취소)"
            }.get(fail_option, fail_option)
            
            # 설정 요약 표시
            settings_summary = dmc.Alert(
                title="변환 설정 요약",
                color="blue",
                variant="light",
                mb="md",
                children=[
                    dmc.Text(f"대상 타입: {target_type_name}", size="sm"),
                    dmc.Text(f"변환 방식: {conversion_option_name}", size="sm"),
                    dmc.Text(f"변환 실패 시: {fail_option_name}", size="sm"),
                ]
            )
            
            preview_content.append(settings_summary)

            # 변환 함수 선택
            conversion_func = self._get_conversion_function(target_type, conversion_option)

            # 테이블 헤더 준비
            thead = dmc.TableThead(
                dmc.TableTr([
                    dmc.TableTh("컬럼"),
                    dmc.TableTh("원본 값"),
                    dmc.TableTh("변환 값"),
                    dmc.TableTh("결과")
                ])
            )

            # 테이블 본문 준비
            table_rows = []
            
            # 각 선택된 컬럼에 대해 샘플 값 표시
            for col in selected_columns:
                try:
                    # Null이 아닌 값 찾기
                    sample_values = df[col].drop_nulls().head(1).to_list()
                    
                    if not sample_values:
                        # Null 값이 아닌 샘플을 찾지 못한 경우
                        table_rows.append(
                            dmc.TableTr([
                                dmc.TableTd(col),
                                dmc.TableTd("데이터 없음", colSpan=3, style={"textAlign": "center", "color": "gray"})
                            ])
                        )
                        continue
                        
                    # 첫 번째 샘플 값만 사용
                    value = sample_values[0]
                    
                    try:
                        # 변환 시도
                        converted = conversion_func(value)
                        
                        # 타입 표시를 위한 문자열 변환
                        orig_type = type(value).__name__
                        conv_type = type(converted).__name__
                        
                        orig_display = f"{value} ({orig_type})"
                        conv_display = f"{converted} ({conv_type})"
                        
                        # 행 추가
                        table_rows.append(
                            dmc.TableTr([
                                dmc.TableTd(col),
                                dmc.TableTd(orig_display),
                                dmc.TableTd(conv_display),
                                dmc.TableTd(dmc.Badge("성공", color="green", variant="light", size="sm"))
                                ])
                            )
                    except Exception as e:
                        # 변환 실패
                        error_msg = str(e)
                        
                        # 실패 처리에 따른 결과 표시
                        result_badge = None
                        if fail_option == "null":
                            result_badge = dmc.Badge("Null 대체", color="yellow", variant="light", size="sm")
                            conv_display = "None (NoneType)"
                        elif fail_option == "default" and default_value is not None:
                            result_badge = dmc.Badge("기본값 대체", color="yellow", variant="light", size="sm")
                            try:
                                default_converted = self._prepare_fill_value(default_value, target_type)
                                conv_display = f"{default_converted} ({type(default_converted).__name__})"
                            except:
                                conv_display = f"{default_value} (str)"
                        else:
                            result_badge = dmc.Badge("오류", color="red", variant="light", size="sm")
                            short_error = error_msg[:30] + "..." if len(error_msg) > 30 else error_msg
                            conv_display = f"오류: {short_error}"
                        
                        # 행 추가
                        table_rows.append(
                            dmc.TableTr([
                                dmc.TableTd(col),
                                dmc.TableTd(f"{value} ({type(value).__name__})"),
                                dmc.TableTd(conv_display),
                                dmc.TableTd(result_badge)
                            ])
                        )
                    
                except Exception as e:
                    logger.error(f"미리보기 생성 오류 (컬럼 {col}): {str(e)}")
                    table_rows.append(
                        dmc.TableTr([
                            dmc.TableTd(col),
                            dmc.TableTd(f"오류: {str(e)}", colSpan=3, style={"color": "red"})
                        ])
                    )

            # 테이블 본문
            tbody = dmc.TableTbody(table_rows)
            
            # 최종 테이블
            preview_table = dmc.Table(
                [thead, tbody],
                striped=True,
                highlightOnHover=True,
                withTableBorder=True,
                withColumnBorders=True
            )
            
            preview_content.append(preview_table)
            
            # 주의사항 추가
            if target_type == "int":
                preview_content.append(
                    dmc.Alert(
                        "정수형 변환 시 소수점이 있는 값은 변환 옵션에 따라 반올림/내림/올림됩니다.",
                        color="yellow",
                        variant="light",
                        mt="md"
                    )
                )
            elif target_type == "bool":
                preview_content.append(
                    dmc.Alert(
                        "불리언 변환에서 'true', 'yes', '1', 'y', 't', 'on'은 True로, 'false', 'no', '0', 'n', 'f', 'off'는 False로 변환됩니다.",
                        color="yellow",
                        variant="light",
                        mt="md"
                    )
                )

            return preview_content



        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("type-changes-apply-btn", "loading"),
            Output("type-changes-column-select", "value"),  # 컬럼 선택 초기화를 위한 출력 추가
            [Input("type-changes-apply-btn", "n_clicks")],
            [State("type-changes-column-select", "value"), 
            State("type-changes-target-type", "value"), 
            State("type-changes-conversion-option", "value"), 
            State("type-changes-fail-option", "value"), 
            State("type-changes-default-value", "value")],
            prevent_initial_call=True
        )
        def apply_type_changes(n_clicks, selected_columns, target_type, conversion_option, 
                            fail_option, default_value):
            """타입 변환 적용 - 최적화"""
            if not n_clicks or not selected_columns or not target_type:
                raise exceptions.PreventUpdate

            try:
                # 변환 함수 선택
                conversion_func = self._get_conversion_function(target_type, conversion_option)
                
                # Polars 데이터 타입 매핑
                target_polars_type = self.type_mapping.get(target_type)
                
                if not target_polars_type:
                    return ([dbpc.Toast(message=f"지원하지 않는 데이터 타입입니다: {target_type}", 
                                    intent="danger", icon="error")], no_update, False, no_update)
                
                # 원본 데이터프레임 복사
                df = SSDF.dataframe.clone()
                
                # 각 컬럼에 대해 타입 변환 수행
                failed_columns = []
                successful_columns = []
                
                for col in selected_columns:
                    try:
                        # 변환 실패 처리 옵션에 따른 strict 설정
                        strict = fail_option == "error"
                        
                        # 기본값 설정 (필요한 경우)
                        fill_value = self._prepare_fill_value(default_value, target_type) if fail_option == "default" else None
                        
                        # 변환 적용
                        if conversion_option and conversion_option != "default":
                            # 특별한 변환 옵션이 있는 경우
                            if target_polars_type == pl.Boolean and conversion_option == "string_recognize":
                                # 불리언 문자열 인식 로직
                                df = df.with_columns(
                                    pl.when(pl.col(col).cast(pl.Utf8).str.to_lowercase()
                                            .is_in(["true", "1", "yes", "y", "on", "t"]))
                                    .then(True)
                                    .when(pl.col(col).cast(pl.Utf8).str.to_lowercase()
                                            .is_in(["false", "0", "no", "n", "off", "f"]))
                                    .then(False)
                                    .otherwise(None)
                                    .alias(col)
                                )
                            else:
                                # 사용자 정의 변환 함수 적용
                                df = df.with_columns(
                                    pl.col(col).map_elements(conversion_func, 
                                                        return_dtype=target_polars_type)
                                    .alias(col)
                                )
                        else:
                            # 기본 타입 변환
                            if fail_option == "null":
                                # 변환 실패 시 null 값으로 대체
                                df = df.with_columns(
                                    pl.col(col).cast(target_polars_type, strict=False).alias(col)
                                )
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
                                    # 기본값 적용 실패 시 null로 대체
                                    df = df.with_columns(
                                        pl.col(col).cast(target_polars_type, strict=False).alias(col)
                                    )
                            else:
                                # strict=True로 설정하면 변환 실패 시 예외 발생
                                df = df.with_columns(
                                    pl.col(col).cast(target_polars_type, strict=strict).alias(col)
                                )
                        
                        successful_columns.append(col)
                        
                    except Exception as e:
                        logger.error(f"컬럼 '{col}' 타입 변환 실패: {str(e)}")
                        failed_columns.append((col, str(e)))
                
                # 결과 처리 및 반환
                if failed_columns:
                    # 실패한 컬럼이 있는 경우 처리
                    error_messages = "\n".join([f"- {col}: {err}" for col, err in failed_columns])
                    
                    if successful_columns:
                        # 일부 컬럼만 성공한 경우
                        SSDF.dataframe = df
                        updated_columnDefs = generate_column_definitions(df)
                        return ([dbpc.Toast(message=f"{len(successful_columns)}개 컬럼 변환 성공, {len(failed_columns)}개 실패\n{error_messages}", 
                                        intent="warning", icon="warning-sign", timeout=4000)], 
                            updated_columnDefs, False, [])  # 컬럼 선택 초기화
                    else:
                        # 모든 컬럼 변환 실패
                        return ([dbpc.Toast(message=f"모든 컬럼 변환 실패:\n{error_messages}", 
                                        intent="danger", icon="error", timeout=4000)], 
                            no_update, False, no_update)  # 컬럼 선택 유지
                
                # 모든 컬럼 변환 성공
                SSDF.dataframe = df
                updated_columnDefs = generate_column_definitions(df)
                
                # 변환 타입 이름
                target_type_name = {
                    "str": "문자열 (String)",
                    "int": "정수 (Integer)",
                    "float": "실수 (Float)",
                    "bool": "불리언 (Boolean)"
                }.get(target_type, target_type)
                
                return ([dbpc.Toast(message=f"{len(successful_columns)}개 컬럼의 타입이 '{target_type_name}'으로 변환되었습니다.", 
                                intent="success", icon="endorsed", timeout=3000)], 
                    updated_columnDefs, False, [])  # 컬럼 선택 초기화
                    
            except Exception as e:
                # 전체 처리 오류
                logger.error(f"타입 변환 처리 오류: {str(e)}")
                return ([dbpc.Toast(message=f"타입 변환 처리 오류: {str(e)}", 
                                intent="danger", icon="error")], 
                    no_update, False, no_update)  # 컬럼 선택 유지





        # Apply 버튼 로딩 상태 설정 (버튼 클릭 시)
        app.clientside_callback(
            """
            function updateLoadingState(n_clicks) {
                if (n_clicks) {
                    return true;
                }
                return dash_clientside.no_update;
            }
            """,
            Output("type-changes-apply-btn", "loading", allow_duplicate=True),
            Input("type-changes-apply-btn", "n_clicks"),
            prevent_initial_call=True,
        )

    def _get_conversion_function(self, target_type, conversion_option):
        """타입과 변환 옵션에 따른 변환 함수 반환 - 예외 처리 강화"""

        # 안전한 타입 변환 함수 (예외 처리 포함)
        def safe_int_convert(x):
            if x is None:
                return None
            try:
                # 문자열이면서 소수점이 있는 경우 처리
                if isinstance(x, str) and '.' in x:
                    return int(float(x))
                return int(float(x))  # 실수도 정수로 변환 가능하도록
            except (ValueError, TypeError):
                raise ValueError(f"'{x}'를 정수로 변환할 수 없습니다")

        def safe_float_convert(x):
            if x is None:
                return None
            try:
                # 쉼표가 포함된 숫자 문자열 처리 (예: '1,234.56')
                if isinstance(x, str):
                    x = x.replace(',', '')
                return float(x)
            except (ValueError, TypeError):
                raise ValueError(f"'{x}'를 실수로 변환할 수 없습니다")

        def safe_bool_convert(x):
            if x is None:
                return None
            
            if isinstance(x, bool):
                return x
            
            if isinstance(x, (int, float)):
                return bool(x)
                
            if isinstance(x, str):
                x_lower = x.lower().strip()
                if x_lower in ["true", "1", "yes", "y", "t", "on"]:
                    return True
                if x_lower in ["false", "0", "no", "n", "f", "off"]:
                    return False
                    
            raise ValueError(f"'{x}'를 불리언으로 변환할 수 없습니다")

        def safe_str_convert(x):
            if x is None:
                return ""
            return str(x)

        # 기본 변환 함수 (안전한 타입 캐스팅)
        default_conversion = {
            "str": safe_str_convert,
            "int": safe_int_convert,
            "float": safe_float_convert,
            "bool": safe_bool_convert,
        }

        # 변환 옵션이 없거나 기본 변환인 경우
        if not conversion_option or conversion_option == "default":
            return default_conversion.get(target_type, lambda x: x)

        # 문자열 변환 옵션
        if target_type == "str":
            if conversion_option == "lowercase":
                return lambda x: safe_str_convert(x).lower()
            elif conversion_option == "uppercase":
                return lambda x: safe_str_convert(x).upper()
            elif conversion_option == "titlecase":
                return lambda x: safe_str_convert(x).title()

        # 정수 변환 옵션
        elif target_type == "int":
            if conversion_option == "round":
                return lambda x: int(round(safe_float_convert(x))) if x is not None else None
            elif conversion_option == "floor":
                import math
                return lambda x: int(math.floor(safe_float_convert(x))) if x is not None else None
            elif conversion_option == "ceil":
                import math
                return lambda x: int(math.ceil(safe_float_convert(x))) if x is not None else None

        # 실수 변환 옵션 
        elif target_type == "float":
            if conversion_option == "2decimal":
                return lambda x: round(safe_float_convert(x), 2) if x is not None else None
            elif conversion_option == "4decimal":
                return lambda x: round(safe_float_convert(x), 4) if x is not None else None
            elif conversion_option == "scientific":
                return lambda x: float(f"{safe_float_convert(x):.2e}") if x is not None else None

        # 불리언 변환 옵션
        elif target_type == "bool":
            if conversion_option == "string_recognize":
                return safe_bool_convert

        # 기본 변환 함수 반환
        return default_conversion.get(target_type, lambda x: x)

    def _prepare_fill_value(self, default_value, target_type):
        """기본값을 적절한 타입으로 변환"""
        if default_value is None:
            return None
            
        try:
            if target_type == "int":
                return int(float(default_value))
            elif target_type == "float":
                return float(default_value)
            elif target_type == "bool":
                return default_value.lower() in ["true", "1", "yes", "y", "t", "on"]
            else:
                return default_value
        except:
            # 변환 실패 시 None 반환
            return None