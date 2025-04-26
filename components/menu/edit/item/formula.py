import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, no_update, exceptions, ctx, dcc, ALL
import re


from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions
from components.menu.edit.utils import handle_tab_button_click

class Formula:

    def __init__(self):
        # 함수 카테고리 및 함수 정의
        self.supported_operations = {
            "산술 연산": [
                {"value": "add", "label": "더하기 (+)"},
                {"value": "subtract", "label": "빼기 (-)"},
                {"value": "multiply", "label": "곱하기 (*)"},
                {"value": "divide", "label": "나누기 (/)"},
                {"value": "power", "label": "거듭제곱 (^)"}
            ],
            "통계 함수": [
                {"value": "sum", "label": "합계 (SUM)"},
                {"value": "average", "label": "평균 (AVERAGE)"},
                {"value": "min", "label": "최소값 (MIN)"},
                {"value": "max", "label": "최대값 (MAX)"}
            ],
            "조건 함수": [
                {"value": "if_greater", "label": "큰 경우 (IF >)"},
                {"value": "if_less", "label": "작은 경우 (IF <)"},
                {"value": "if_equal", "label": "같은 경우 (IF =)"},
                {"value": "if_not_equal", "label": "다른 경우 (IF ≠)"},
                {"value": "if_greater_equal", "label": "크거나 같은 경우 (IF >=)"},
                {"value": "if_less_equal", "label": "작거나 같은 경우 (IF <=)"},
                {"value": "if_null", "label": "NULL인 경우"},
                {"value": "if_not_null", "label": "NULL이 아닌 경우"},
                {"value": "if_contains", "label": "포함하는 경우 (문자열)"},
                {"value": "if_not_contains", "label": "포함하지 않는 경우 (문자열)"}
            ],
            "변환 함수": [
                {"value": "abs", "label": "절대값 (ABS)"},
                {"value": "round", "label": "반올림 (ROUND)"},
                {"value": "log", "label": "로그 (LOG)"}
            ],
            "텍스트 함수": [
                {"value": "concat", "label": "문자 연결 (CONCATENATE)"},
                {"value": "left", "label": "왼쪽 문자 추출 (LEFT)"},
                {"value": "right", "label": "오른쪽 문자 추출 (RIGHT)"},
                {"value": "length", "label": "문자열 길이 (LENGTH)"},
                {"value": "count_char", "label": "특정 문자 개수 (COUNT CHAR)"},
                {"value": "count_substring", "label": "특정 문자열 개수 (COUNT SUBSTRING)"}
            ]
        }
        
    def button_layout(self):
        return dbpc.Button(
            "Formula", 
            id="formula-btn", 
            icon="function", 
            minimal=True, 
            outlined=True
        )

    def tab_layout(self):
        return dmc.Paper(
            children=[
                dmc.Group([
                    dbpc.EntityTitle(
                        title="Spreadsheet Formula", 
                        heading="H5", 
                        icon="function"
                    )
                ], grow=True),
                dmc.Space(h=15),
                
                # 새 컬럼 이름 입력
                dmc.TextInput(
                    id="formula-column-name",
                    label="새로운 컬럼 이름",
                    description="계산 결과를 저장할 컬럼 이름을 입력하세요",
                    placeholder="새 컬럼 이름",
                    required=True,
                ),
                
                dmc.Space(h=20),
                
                # 연산 유형 선택
                dmc.Select(
                    id="formula-operation-type",
                    label="연산 유형 선택",
                    description="어떤 종류의 연산을 수행할지 선택하세요",
                    data=[
                        {"value": "arithmetic", "label": "산술 연산 (더하기, 빼기 등)"},
                        {"value": "statistical", "label": "통계 함수 (평균, 합계 등)"},
                        {"value": "conditional", "label": "조건 함수 (IF 문)"},
                        {"value": "transform", "label": "변환 함수 (반올림, 절대값 등)"},
                        {"value": "text", "label": "텍스트 함수 (연결, 추출 등)"}
                    ],
                    clearable=False,
                ),
                
                # 연산 선택 (연산 유형에 따라 동적으로 변경)
                dmc.Select(
                    id="formula-operation",
                    label="연산 선택",
                    description="수행할 연산을 선택하세요",
                    data=[],
                    disabled=True,
                    clearable=False,
                ),
                
                # 연산에 따른 입력 필드 (동적으로 생성됨)
                html.Div(id="formula-inputs-container"),
                
                dmc.Space(h=20),
                
                # 미리보기 영역
                dmc.Paper(
                    id="formula-preview-container",
                    withBorder=True,
                    p="sm",
                    style={"maxHeight": "200px", "overflow": "auto"},
                    children=[
                        dmc.Text("미리보기: 연산을 선택하면 결과 예시가 표시됩니다.", size="sm", c="dimmed"),
                    ],
                ),
                
                dmc.Space(h=20),
                
                # 수식 추가 버튼
                dmc.Group([
                    dbpc.Button(
                        "Apply", 
                        id="formula-apply-btn", 
                        outlined=True,
                        icon="tick",
                        intent="primary",
                        disabled=True
                    ),
                ], justify="center"),
                
                # 도움말 섹션
                dmc.Space(h=20),
                dmc.Accordion(
                    value="help",
                    children=[
                        dmc.AccordionItem(
                            [
                                dmc.AccordionControl("사용 방법"),
                                dmc.AccordionPanel([
                                    dmc.Text("1. 결과를 저장할 새 컬럼 이름을 입력하세요.", size="sm"),
                                    dmc.Text("2. 연산 유형을 선택하세요 (산술, 통계 등).", size="sm"),
                                    dmc.Text("3. 구체적인 연산을 선택하세요 (더하기, 평균 등).", size="sm"),
                                    dmc.Text("4. 필요한 입력값을 제공하세요 (컬럼, 상수 등).", size="sm"),
                                    dmc.Text("5. 미리보기를 확인하고 Apply 버튼을 클릭하세요.", size="sm"),
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
            Input("formula-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True
        )
        def handle_formula_button_click(n_clicks, current_model):
            """Add Row 버튼 클릭 시 우측 패널에 탭 추가"""
            return handle_tab_button_click(n_clicks, current_model, "formula-tab", "Formula")


        @app.callback(
            Output("formula-operation", "data"),
            Output("formula-operation", "disabled"),
            Input("formula-operation-type", "value"),
            prevent_initial_call=True
        )
        def update_operations(operation_type):
            """선택된 연산 유형에 따라 연산 목록 업데이트"""
            if not operation_type:
                return [], True
                
            if operation_type == "arithmetic":
                operations = self.supported_operations["산술 연산"]
            elif operation_type == "statistical":
                operations = self.supported_operations["통계 함수"]
            elif operation_type == "conditional":
                operations = self.supported_operations["조건 함수"]
            elif operation_type == "transform":
                operations = self.supported_operations["변환 함수"]
            elif operation_type == "text":
                operations = self.supported_operations["텍스트 함수"]
            else:
                operations = []
                
            return operations, False
            
        @app.callback(
            Output("formula-inputs-container", "children"),
            [
                Input("formula-operation-type", "value"),
                Input("formula-operation", "value")
            ],
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True
        )
        def update_formula_inputs(operation_type, operation, columnDefs):
            """연산에 따라 필요한 입력 필드 생성"""
            if not operation_type or not operation:
                return []
                
            # 보호할 컬럼 리스트 (시스템 컬럼)
            protected_columns = ["uniqid", "group", "childCount"]
            
            # 컬럼 목록 (보호할 컬럼 제외)
            columns_data = [
                {"value": col["field"], "label": col["field"]} 
                for col in columnDefs if col["field"] not in protected_columns
            ]
            
            inputs = []
            
            # 산술 연산
            if operation_type == "arithmetic":
                inputs.append(
                    dmc.Select(
                        id={"type": "formula-input", "index": 0},
                        label="첫 번째 컬럼",
                        data=columns_data,
                        required=True,
                        clearable=False,
                        mb=10
                    )
                )
                
                if operation == "add":
                    op_text = "더할"
                elif operation == "subtract":
                    op_text = "뺄"
                elif operation == "multiply":
                    op_text = "곱할"
                elif operation == "divide":
                    op_text = "나눌"
                else:
                    op_text = "계산할"
                    
                inputs.append(
                    dmc.RadioGroup(
                        id={"type": "formula-input", "index": 1},
                        label=f"두 번째 값 ({op_text} 값)",
                        value="column",
                        mb=10,
                        children=[
                            dmc.Radio("컬럼 선택", value="column"),
                            dmc.Radio("상수 입력", value="constant")
                        ]
                    )
                )
                
                inputs.append(
                    html.Div(
                        id="formula-second-input-container",
                        children=[
                            dmc.Select(
                                id={"type": "formula-input", "index": 2},
                                label="두 번째 컬럼",
                                data=columns_data,
                                required=True,
                                clearable=False,
                                mb=10
                            )
                        ]
                    )
                )
                
            # 통계 함수
            elif operation_type == "statistical":
                inputs.append(
                    dmc.MultiSelect(
                        id={"type": "formula-input", "index": 0},
                        label="계산할 컬럼 선택 (여러 개 선택 가능)",
                        data=columns_data,
                        required=True,
                        mb=10
                    )
                )
                
            # 조건 함수
            elif operation_type == "conditional":
                inputs.append(
                    dmc.Select(
                        id={"type": "formula-input", "index": 0},
                        label="조건을 확인할 컬럼",
                        data=columns_data,
                        required=True,
                        clearable=False,
                        mb=10
                    )
                )
                inputs.append(
                    dmc.RadioGroup(
                        id={"type": "formula-input", "index": 1},
                        label="비교 값 타입",
                        value="number",
                        mb=10,
                        children=[
                            dmc.Radio("숫자", value="number"),
                            dmc.Radio("텍스트", value="text")
                        ]
                    )
                )


                inputs.append(
                    html.Div(
                        id="conditional-compare-value-container",
                        children=[
                            dmc.NumberInput(
                                id={"type": "formula-input", "index": 2},
                                label="비교할 숫자 값",
                                required=True,
                                mb=10
                            )
                        ]
                    )
                )
                
                # 참일 때 값 타입 선택
                inputs.append(
                    dmc.RadioGroup(
                        id={"type": "formula-input", "index": 3},
                        label="조건이 참일 때 값 타입",
                        value="number",
                        mb=10,
                        children=[
                            dmc.Radio("숫자", value="number"),
                            dmc.Radio("텍스트", value="text")
                        ]
                    )
                )
                
                # 참일 때 값 입력 컨테이너
                inputs.append(
                    html.Div(
                        id="conditional-true-value-container",
                        children=[
                            dmc.NumberInput(
                                id={"type": "formula-input", "index": 4},
                                label="참일 때 값 (숫자)",
                                required=True,
                                mb=10
                            )
                        ]
                    )
                )
                
                # 거짓일 때 값 타입 선택
                inputs.append(
                    dmc.RadioGroup(
                        id={"type": "formula-input", "index": 5},
                        label="조건이 거짓일 때 값 타입",
                        value="number",
                        mb=10,
                        children=[
                            dmc.Radio("숫자", value="number"),
                            dmc.Radio("텍스트", value="text")
                        ]
                    )
                )
                
                # 거짓일 때 값 입력 컨테이너
                inputs.append(
                    html.Div(
                        id="conditional-false-value-container",
                        children=[
                            dmc.NumberInput(
                                id={"type": "formula-input", "index": 6},
                                label="거짓일 때 값 (숫자)",
                                required=True,
                                mb=10
                            )
                        ]
                    )
                )
                
            # 변환 함수
            elif operation_type == "transform":
                inputs.append(
                    dmc.Select(
                        id={"type": "formula-input", "index": 0},
                        label="변환할 컬럼",
                        data=columns_data,
                        required=True,
                        clearable=False,
                        mb=10
                    )
                )
                
                if operation == "round":
                    inputs.append(
                        dmc.NumberInput(
                            id={"type": "formula-input", "index": 1},
                            label="소수점 자릿수",
                            value=0,
                            min=0,
                            max=10,
                            mb=10
                        )
                    )
                    
            # 텍스트 함수
            elif operation_type == "text":

                if operation == "count_char":
                    inputs.append(
                        dmc.Select(
                            id={"type": "formula-input", "index": 0},
                            label="대상 컬럼",
                            data=columns_data,
                            required=True,
                            clearable=False,
                            mb=10
                        )
                    )
                    inputs.append(
                        dmc.TextInput(
                            id={"type": "formula-input", "index": 1},
                            label="찾을 문자",
                            description="개수를 셀 문자를 입력하세요 (예: '.')",
                            placeholder="예: .",
                            required=True,
                            mb=10
                        )
                    )
                elif operation == "count_substring":
                    inputs.append(
                        dmc.Select(
                            id={"type": "formula-input", "index": 0},
                            label="대상 컬럼",
                            data=columns_data,
                            required=True,
                            clearable=False,
                            mb=10
                        )
                    )
                    inputs.append(
                        dmc.TextInput(
                            id={"type": "formula-input", "index": 1},
                            label="찾을 문자열",
                            description="개수를 셀 문자열을 입력하세요",
                            placeholder="예: .com",
                            required=True,
                            mb=10
                        )
                    )

                elif operation == "concat":
                    inputs.append(
                        dmc.MultiSelect(
                            id={"type": "formula-input", "index": 0},
                            label="연결할 컬럼 선택 (여러 개 선택 가능)",
                            data=columns_data,
                            required=True,
                            mb=10
                        )
                    )
                    
                    inputs.append(
                        dmc.TextInput(
                            id={"type": "formula-input", "index": 1},
                            label="구분자 (컬럼 사이에 들어갈 문자)",
                            value=" ",
                            mb=10
                        )
                    )
                    
                elif operation in ["left", "right"]:
                    inputs.append(
                        dmc.Select(
                            id={"type": "formula-input", "index": 0},
                            label="추출할 텍스트 컬럼",
                            data=columns_data,
                            required=True,
                            clearable=False,
                            mb=10
                        )
                    )
                    
                    inputs.append(
                        dmc.NumberInput(
                            id={"type": "formula-input", "index": 1},
                            label="추출할 문자 수",
                            value=1,
                            min=1,
                            max=100,
                            mb=10
                        )
                    )
                    
            return inputs


        @app.callback(
            Output("conditional-compare-value-container", "children"),
            Input({"type": "formula-input", "index": 1}, "value"),
            prevent_initial_call=True
        )
        def update_compare_value_input(value_type):
            """비교 값 입력 필드 타입 변경"""
            if value_type == "number":
                return [
                    dmc.NumberInput(
                        id={"type": "formula-input", "index": 2},
                        label="비교할 숫자 값",
                        required=True,
                        mb=10
                    )
                ]
            else:
                return [
                    dmc.TextInput(
                        id={"type": "formula-input", "index": 2},
                        label="비교할 텍스트 값",
                        required=True,
                        mb=10
                    )
                ]

        @app.callback(
            Output("conditional-true-value-container", "children"),
            Input({"type": "formula-input", "index": 3}, "value"),
            prevent_initial_call=True
        )
        def update_true_value_input(value_type):
            """참일 때 값 입력 필드 타입 변경"""
            if value_type == "number":
                return [
                    dmc.NumberInput(
                        id={"type": "formula-input", "index": 4},
                        label="참일 때 값 (숫자)",
                        required=True,
                        mb=10
                    )
                ]
            else:
                return [
                    dmc.TextInput(
                        id={"type": "formula-input", "index": 4},
                        label="참일 때 값 (텍스트)",
                        required=True,
                        mb=10
                    )
                ]

        @app.callback(
            Output("conditional-false-value-container", "children"),
            Input({"type": "formula-input", "index": 5}, "value"),
            prevent_initial_call=True
        )
        def update_false_value_input(value_type):
            """거짓일 때 값 입력 필드 타입 변경"""
            if value_type == "number":
                return [
                    dmc.NumberInput(
                        id={"type": "formula-input", "index": 6},
                        label="거짓일 때 값 (숫자)",
                        required=True,
                        mb=10
                    )
                ]
            else:
                return [
                    dmc.TextInput(
                        id={"type": "formula-input", "index": 6},
                        label="거짓일 때 값 (텍스트)",
                        required=True,
                        mb=10
                    )
                ]


        @app.callback(
            Output("formula-second-input-container", "children"),
            Input({"type": "formula-input", "index": 1}, "value"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True
        )
        def update_second_input(input_type, columnDefs):
            """두 번째 입력 필드 유형 (컬럼 또는 상수) 변경"""
            if input_type == "column":
                # 컬럼 선택 드롭다운
                protected_columns = ["uniqid", "group", "childCount"]
                columns_data = [
                    {"value": col["field"], "label": col["field"]} 
                    for col in columnDefs if col["field"] not in protected_columns
                ]
                
                return [
                    dmc.Select(
                        id={"type": "formula-input", "index": 2},
                        label="두 번째 컬럼",
                        data=columns_data,
                        required=True,
                        clearable=False,
                        mb=10
                    )
                ]
            else:
                # 상수 입력 필드
                return [
                    dmc.NumberInput(
                        id={"type": "formula-input", "index": 2},
                        label="상수 값",
                        required=True,
                        mb=10
                    )
                ]
                
        @app.callback(
            Output("formula-preview-container", "children"),
            Output("formula-apply-btn", "disabled"),
            [
                Input("formula-column-name", "value"),
                Input("formula-operation-type", "value"),
                Input("formula-operation", "value"),
                Input({"type": "formula-input", "index": ALL}, "value")
            ],
            prevent_initial_call=True
        )
        def update_preview(column_name, operation_type, operation, input_values):
            """입력값에 따른 미리보기 및 Apply 버튼 활성화"""
            # 입력값 검증
            if not column_name or not operation_type or not operation:
                return [dmc.Text("미리보기: 필수 입력값을 모두 입력하세요.", size="sm", c="dimmed")], True
                
            # 컬럼 이름 유효성 검사 (영문자로 시작)
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', column_name):
                return [dmc.Text("오류: 컬럼 이름은 영문자로 시작하고, 영문자, 숫자, 언더스코어(_)만 사용 가능합니다.", c="red")], True
            
            # input_values에 None이 있으면 아직 모든 필드가 채워지지 않음
            if None in input_values or not input_values:
                return [dmc.Text("미리보기: 필수 입력값을 모두 입력하세요.", size="sm", c="dimmed")], True
            
            try:
                # 기존 컬럼 이름 중복 확인
                df = SSDF.dataframe
                if column_name in df.columns:
                    return [dmc.Text(f"오류: 이미 '{column_name}' 컬럼이 존재합니다. 다른 이름을 입력하세요.", c="red")], True
                
                # 수식 생성 및 계산 시도
                polars_expr = self._create_polars_expression(operation_type, operation, input_values)
                
                # 효율적인 샘플링
                sample_size = min(5, df.height)
                sample_df = df.slice(0, sample_size)
                
                try:
                    # 수식 계산 시도
                    with pl.Config(tbl_rows=sample_size):  # 표시 행 수 제한
                        result_series = sample_df.select(polars_expr.alias("result"))["result"]
                                    
                    # 결과 미리보기 테이블 생성
                    header = [
                        dmc.TableThead(
                            dmc.TableTr([
                                dmc.TableTh("행 번호", style={"width": "20%"}),
                                dmc.TableTh(column_name, style={"width": "80%"})
                            ])
                        )
                    ]
                    
                    rows = [
                        dmc.TableTr([
                            dmc.TableTd(str(i+1)),
                            dmc.TableTd(str(result_series[i]))
                        ])
                        for i in range(len(result_series))
                    ]
                    
                    preview_table = dmc.Table(
                        [*header, dmc.TableTbody(rows)],
                        striped=True,
                        highlightOnHover=True,
                        withTableBorder=True,
                        withColumnBorders=True,
                    )

                    preview_content = [
                        dmc.Text(f"수식 결과 미리보기:", size="sm", w=500, mb="xs"),
                        preview_table
                    ]
                    
                    # 모든 검증을 통과하면 Apply 버튼 활성화
                    return preview_content, False

                except Exception as e:
                    # 계산 오류 메시지 개선
                    error_message = str(e)
                    if "division by zero" in error_message.lower():
                        error_message = "0으로 나누기 연산이 포함되어 있습니다"
                    elif "overflow" in error_message.lower():
                        error_message = "연산 결과가 너무 큽니다"
                        
                    return [dmc.Alert(f"결과 계산 중 오류가 발생했습니다: {error_message}", color="red", variant="light")], True
                    
            except Exception as e:
                # 수식 생성 오류
                return [dmc.Alert(f"수식 생성 중 오류가 발생했습니다: {str(e)}", color="orange", variant="light")], True


        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("formula-column-name", "value"),
            [
                Input("formula-apply-btn", "n_clicks")
            ],
            [
                State("formula-column-name", "value"),
                State("formula-operation-type", "value"),
                State("formula-operation", "value"),
                State({"type": "formula-input", "index": ALL}, "value")
            ],
            prevent_initial_call=True
        )
        def apply_formula(n_clicks, column_name, operation_type, operation, input_values):
            """수식 적용"""
            if not n_clicks:
                raise exceptions.PreventUpdate
                
            try:
                # 수식 생성
                polars_expr = self._create_polars_expression(operation_type, operation, input_values)
                
                # 새 컬럼 계산 및 추가
                SSDF.dataframe = SSDF.dataframe.with_columns(polars_expr.alias(column_name))
                
                # 컬럼 정의 업데이트
                updated_columnDefs = generate_column_definitions(SSDF.dataframe)
                
                # 성공 메시지
                operation_label = next((op["label"] for op in self.supported_operations.get(self._get_operation_category(operation_type), []) if op["value"] == operation), operation)
                
                toast = dbpc.Toast(
                    message=f"'{column_name}' 컬럼이 '{operation_label}' 연산으로 추가되었습니다.",
                    intent="success",
                    icon="endorsed",
                    timeout=4000
                )
                
                # 입력 필드 초기화
                return [toast], updated_columnDefs, ""
                
            except Exception as e:
                # 오류 처리
                logger.error(f"수식 적용 오류: {str(e)}")
                return [dbpc.Toast(
                    message=f"수식 적용 오류: {str(e)}",
                    intent="danger",
                    icon="error"
                )], no_update, no_update
                
    def _get_operation_category(self, operation_type):
        """연산 유형에 따른 카테고리 반환"""
        if operation_type == "arithmetic":
            return "산술 연산"
        elif operation_type == "statistical":
            return "통계 함수"
        elif operation_type == "conditional":
            return "조건 함수"
        elif operation_type == "transform":
            return "변환 함수"
        elif operation_type == "text":
            return "텍스트 함수"
        return ""
    
    def _safe_cast_value(self, value, value_type):
        """값의 안전한 타입 변환"""
        try:
            if value_type == "number":
                return pl.lit(float(value))
            else:
                return pl.lit(str(value))
        except Exception:
            # 변환 실패 시 문자열로 처리
            return pl.lit(str(value))

    def _create_polars_expression(self, operation_type, operation, input_values):
        """입력값에 따라 Polars 표현식 생성"""
        try:
            # 산술 연산
            if operation_type == "arithmetic":
                col1 = input_values[0]
                input_type = input_values[1]
                second_value = input_values[2]
                
                # 첫 번째 컬럼
                expr = pl.col(col1)
                
                # 두 번째 값 (컬럼 또는 상수)
                second_expr = pl.col(second_value) if input_type == "column" else pl.lit(second_value)
                
                # 연산 적용
                if operation == "add":
                    return expr + second_expr
                elif operation == "subtract":
                    return expr - second_expr
                elif operation == "multiply":
                    return expr * second_expr
                
                elif operation == "divide":
                    # 안전한 나누기 - 0과 infinity 처리
                    safe_division = (
                        pl.when(second_expr == 0)
                        .then(None)
                        .otherwise(expr / second_expr)
                    )
                    
                    # 결과가 infinity인 경우 처리
                    return (
                        pl.when(safe_division.is_infinite())
                        .then(None)
                        .otherwise(safe_division)
                    )

                elif operation == "power":
                    return expr.pow(second_expr)
                    
            # 통계 함수
            elif operation_type == "statistical":
                columns = input_values[0]
                
                if not columns:
                    raise ValueError("하나 이상의 컬럼을 선택하세요.")
                    
                # 컬럼 목록 생성
                column_exprs = [pl.col(col) for col in columns]
                
                # 연산 적용
                if operation == "sum":
                    return pl.sum_horizontal(column_exprs)
                elif operation == "average":
                    return pl.mean_horizontal(column_exprs)
                elif operation == "min":
                    return pl.min_horizontal(column_exprs)
                elif operation == "max":
                    return pl.max_horizontal(column_exprs)

            # 조건 함수
            elif operation_type == "conditional":

                

                column = input_values[0]
                expr = pl.col(column)
                
                # NULL 관련 연산인 경우 특별 처리
                if operation in ["if_null", "if_not_null"]:
                    true_type = input_values[1]
                    true_value = input_values[2]
                    false_type = input_values[3]
                    false_value = input_values[4]
                    
                    condition = expr.is_null() if operation == "if_null" else ~expr.is_null()
                else:
                    # 일반 조건 연산
                    compare_type = input_values[1]
                    compare_value = input_values[2]
                    true_type = input_values[3]
                    true_value = input_values[4]
                    false_type = input_values[5]
                    false_value = input_values[6]
                    
                    # 비교값 타입 변환
                    if compare_type == "number":
                        compare_value = float(compare_value)
                    else:
                        compare_value = str(compare_value)


                    # 연산 적용
                    if operation == "if_greater":
                        condition = expr > compare_value
                    elif operation == "if_less":
                        condition = expr < compare_value
                    elif operation == "if_equal":
                        condition = expr == compare_value
                    elif operation == "if_not_equal":
                        condition = expr != compare_value
                    elif operation == "if_greater_equal":
                        condition = expr >= compare_value
                    elif operation == "if_less_equal":
                        condition = expr <= compare_value
                    elif operation == "if_null":
                        condition = expr.is_null()
                        # NULL 검사의 경우 비교값은 무시됨
                    elif operation == "if_not_null":
                        condition = ~expr.is_null()
                        # NULL 검사의 경우 비교값은 무시됨
                    elif operation == "if_contains":
                        # 문자열 처리
                        condition = expr.cast(pl.Utf8).str.contains(str(compare_value))
                    elif operation == "if_not_contains":
                        # 문자열 처리
                        condition = ~expr.cast(pl.Utf8).str.contains(str(compare_value))
                    else:
                        raise ValueError(f"지원하지 않는 조건 연산입니다: {operation}")

                # 결과값 처리 - 타입 안전성 강화
                true_result = self._safe_cast_value(true_value, true_type)
                false_result = self._safe_cast_value(false_value, false_type)
                
                # NULL 안전 처리
                safe_condition = condition.fill_null(False)
                
                return pl.when(safe_condition).then(true_result).otherwise(false_result)


            # 변환 함수
            elif operation_type == "transform":
                column = input_values[0]
                
                # 컬럼 표현식
                expr = pl.col(column)
                
                # 연산 적용
                if operation == "abs":
                    return expr.abs()
                elif operation == "round":
                    decimals = int(input_values[1]) if len(input_values) > 1 else 0
                    return expr.round(decimals)
                elif operation == "log":
                    return expr.log()
                    
            # 텍스트 함수
            elif operation_type == "text":

                if operation == "count_char":
                    column = input_values[0]
                    char_to_count = input_values[1]
                    
                    if not char_to_count:
                        raise ValueError("찾을 문자를 입력해주세요.")
                    
                    # Polars의 str.count_matches 사용
                    return pl.col(column).cast(pl.Utf8).str.count_matches(pl.lit(re.escape(char_to_count)))
                    
                elif operation == "count_substring":
                    column = input_values[0]
                    substring = input_values[1]
                    
                    if not substring:
                        raise ValueError("찾을 문자열을 입력해주세요.")
                    
                    # 문자열 카운트
                    return pl.col(column).cast(pl.Utf8).str.count_matches(pl.lit(re.escape(substring)))
                    
                elif operation == "length":
                    column = input_values[0]
                    return pl.col(column).cast(pl.Utf8).str.len_chars()

                elif operation == "concat":
                    columns = input_values[0]
                    separator = input_values[1] if len(input_values) > 1 else " "
                    
                    if not columns:
                        raise ValueError("하나 이상의 컬럼을 선택하세요.")
                        
                    try:
                        # 방법 1: concat_str 함수 사용 (Polars 최신 버전)
                        column_exprs = [pl.col(col).cast(pl.Utf8) for col in columns]
                        return pl.concat_str(column_exprs, separator=separator)
                    except AttributeError:
                        # 방법 2: 개별 처리 (이전 버전 Polars 호환)
                        if len(columns) == 1:
                            return pl.col(columns[0]).cast(pl.Utf8)
                            
                        # 직접 구현
                        exprs = [pl.col(col).cast(pl.Utf8) for col in columns]
                        result = exprs[0]
                        
                        for expr in exprs[1:]:
                            # separator를 직접 문자열로 전달
                            result = result.str.concat(separator).str.concat(expr)
                            
                        return result
                        
                elif operation == "left":
                    column = input_values[0]
                    n_chars = int(input_values[1])
                    
                    return pl.col(column).cast(pl.Utf8).str.slice(0, n_chars)
                    
                elif operation == "right":
                    column = input_values[0]
                    n_chars = int(input_values[1])
                    
                    return pl.col(column).cast(pl.Utf8).str.slice(-n_chars, None)


                    
            # 지원하지 않는 연산
            raise ValueError(f"지원하지 않는 연산입니다: {operation_type} - {operation}")

        except Exception as e:
            logger.error(f"수식 생성 오류: {str(e)}")
            raise ValueError(f"수식 생성 중 오류가 발생했습니다: {str(e)}")



    def _handle_conditional_operation(self, operation, column, input_values):
        """조건 함수 처리 로직"""
        
        # 기본 파라미터 설정
        expr = pl.col(column)
        
        # 각 연산에 맞는 조건 생성
        if operation in ["if_null", "if_not_null"]:
            # NULL 검사는 비교값 없이 수행
            if operation == "if_null":
                condition = expr.is_null()
            else:  # if_not_null
                condition = ~expr.is_null()
            
            # 참/거짓 값 설정
            true_value = input_values[1]
            false_value = input_values[2]
            true_type = "auto"
            false_type = "auto"
        else:
            # 일반 비교 조건
            compare_value = input_values[1]
            compare_type = self._detect_value_type(compare_value)
            
            # 비교값 변환
            if compare_type == "number":
                compare_value = float(compare_value)
            
            # 조건 생성
            if operation == "if_greater":
                condition = expr > compare_value
            elif operation == "if_less":
                condition = expr < compare_value
            elif operation == "if_equal":
                condition = expr == compare_value
            elif operation == "if_not_equal":
                condition = expr != compare_value
            elif operation == "if_greater_equal":
                condition = expr >= compare_value
            elif operation == "if_less_equal":
                condition = expr <= compare_value
            elif operation == "if_contains":
                # 문자열 처리
                condition = expr.cast(pl.Utf8).str.contains(str(compare_value))
            elif operation == "if_not_contains":
                # 문자열 처리
                condition = ~expr.cast(pl.Utf8).str.contains(str(compare_value))
            else:
                raise ValueError(f"지원하지 않는 조건 연산입니다: {operation}")
            
            # 참/거짓 값 설정
            true_value = input_values[2]
            false_value = input_values[3]
            true_type = self._detect_value_type(true_value)
            false_type = self._detect_value_type(false_value)
        
        # 값 변환
        true_val = float(true_value) if true_type == "number" else str(true_value)
        false_val = float(false_value) if false_type == "number" else str(false_value)
        
        # 결과 타입 추론
        result_type = pl.Float64 if true_type == "number" and false_type == "number" else pl.Utf8
        
        # NULL 값 처리
        condition = condition.fill_null(False)  # NULL은 거짓으로 처리
        
        # 결과 생성
        result = pl.when(condition).then(true_val).otherwise(false_val)
        
        # 필요시 타입 변환
        return result.cast(result_type)

    def _detect_value_type(self, value):
        """값의 타입 감지 (숫자 또는 텍스트)"""
        try:
            float(value)
            return "number"
        except (ValueError, TypeError):
            return "text"
