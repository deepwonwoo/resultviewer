import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, no_update, exceptions, ctx, dcc, ALL
import re

from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions
from components.menu.edit.utils import find_tab_in_layout

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
                {"value": "if_not_equal", "label": "다른 경우 (IF ≠)"}
            ],
            "변환 함수": [
                {"value": "abs", "label": "절대값 (ABS)"},
                {"value": "round", "label": "반올림 (ROUND)"},
                {"value": "log", "label": "로그 (LOG)"}
            ],
            "텍스트 함수": [
                {"value": "concat", "label": "문자 연결 (CONCATENATE)"},
                {"value": "left", "label": "왼쪽 문자 추출 (LEFT)"},
                {"value": "right", "label": "오른쪽 문자 추출 (RIGHT)"}
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
            """Formula 버튼 클릭 시 우측 패널에 탭 추가"""
            if n_clicks is None:
                raise exceptions.PreventUpdate
                
            dff = displaying_df()
            if dff is None:
                return no_update, [dbpc.Toast(message=f"데이터가 로드되지 않았습니다", intent="warning", icon="warning-sign")]

            # 기존 탭 검색
            tab_search_result = find_tab_in_layout(current_model, "formula-tab")
            
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
                "name": "Formula",
                "component": "button",
                "enableClose": True,
                "id": "formula-tab"
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
                    dmc.NumberInput(
                        id={"type": "formula-input", "index": 1},
                        label="비교 값",
                        required=True,
                        mb=10
                    )
                )
                
                inputs.append(
                    dmc.TextInput(
                        id={"type": "formula-input", "index": 2},
                        label="조건이 참일 때 값",
                        required=True,
                        mb=10
                    )
                )
                
                inputs.append(
                    dmc.TextInput(
                        id={"type": "formula-input", "index": 3},
                        label="조건이 거짓일 때 값",
                        required=True,
                        mb=10
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
                if operation == "concat":
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
            ctx_triggered = ctx.triggered_id
            
            # 입력값 검증
            if not column_name or not operation_type or not operation:
                return [dmc.Text("미리보기: 필수 입력값을 모두 입력하세요.", size="sm", c="dimmed")], True
                
            # input_values에 None이 있으면 아직 모든 필드가 채워지지 않음
            if None in input_values or not input_values:
                return [dmc.Text("미리보기: 필수 입력값을 모두 입력하세요.", size="sm", c="dimmed")], True
                
            try:
                # 수식 생성 및 계산 시도
                polars_expr = self._create_polars_expression(operation_type, operation, input_values)
                
                # 계산 결과 미리보기 생성
                df = SSDF.dataframe
                
                # 기존 컬럼 이름 중복 확인
                if column_name in df.columns:
                    return [dmc.Text(f"오류: 이미 '{column_name}' 컬럼이 존재합니다. 다른 이름을 입력하세요.", c="red")], True
                
                # 컬럼 이름 유효성 검사
                import re
                if not re.match(r'^[a-zA-Z0-9_]+$', column_name):
                    return [dmc.Text("오류: 컬럼 이름은 영문자, 숫자, 언더스코어(_)만 사용 가능합니다.", c="red")], True
                
                # 처음 5개의 행만 사용하여 계산 (미리보기 용도)
                sample_df = df.head(5)
                
                try:
                    # 수식 계산 시도
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
                    # 계산 오류
                    return [
                        dmc.Alert(
                            f"결과 계산 중 오류가 발생했습니다: {str(e)}",
                            color="red",
                            variant="light"
                        )
                    ], True
                    
            except Exception as e:
                # 수식 생성 오류
                return [
                    dmc.Alert(
                        f"수식 생성 중 오류가 발생했습니다: {str(e)}",
                        color="orange",
                        variant="light"
                    )
                ], True
                
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
    
    def _create_polars_expression(self, operation_type, operation, input_values):
        """입력값에 따라 Polars 표현식 생성"""
        # 산술 연산
        if operation_type == "arithmetic":
            col1 = input_values[0]
            input_type = input_values[1]
            second_value = input_values[2]
            
            # 첫 번째 컬럼
            expr = pl.col(col1)
            
            # 두 번째 값 (컬럼 또는 상수)
            if input_type == "column":
                second_expr = pl.col(second_value)
            else:
                second_expr = pl.lit(second_value)
            
            # 연산 적용
            if operation == "add":
                return expr + second_expr
            elif operation == "subtract":
                return expr - second_expr
            elif operation == "multiply":
                return expr * second_expr
            elif operation == "divide":
                return expr / second_expr
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
            compare_value = input_values[1]
            true_value = input_values[2]
            false_value = input_values[3]
            
            # 컬럼 표현식
            expr = pl.col(column)
            
            # 비교값이 숫자면 숫자로, 아니면 문자열로 처리
            try:
                compare_value = float(compare_value)
            except:
                compare_value = str(compare_value)
                
            # true_value와 false_value가 숫자면 숫자로, 아니면 문자열로 처리
            try:
                true_value = float(true_value)
            except:
                true_value = str(true_value)
                
            try:
                false_value = float(false_value)
            except:
                false_value = str(false_value)
            
            # 연산 적용
            if operation == "if_greater":
                return pl.when(expr > compare_value).then(true_value).otherwise(false_value)
            elif operation == "if_less":
                return pl.when(expr < compare_value).then(true_value).otherwise(false_value)
            elif operation == "if_equal":
                return pl.when(expr == compare_value).then(true_value).otherwise(false_value)
            elif operation == "if_not_equal":
                return pl.when(expr != compare_value).then(true_value).otherwise(false_value)
                
        # 변환 함수
        elif operation_type == "transform":
            column = input_values[0]
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
            if operation == "concat":
                columns = input_values[0]
                separator = input_values[1] if len(input_values) > 1 else " "
                
                if not columns:
                    raise ValueError("하나 이상의 컬럼을 선택하세요.")
                    
                # 컬럼 표현식 리스트
                column_exprs = [pl.col(col).cast(pl.Utf8) for col in columns]
                
                # 구분자로 모든 컬럼 연결
                result = column_exprs[0]
                for expr in column_exprs[1:]:
                    result = result.str.concat(pl.lit(separator)).str.concat(expr)
                    
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
