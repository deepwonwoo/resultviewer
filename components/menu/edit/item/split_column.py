import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, no_update, exceptions, ctx, dcc

from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions
from components.menu.edit.utils import handle_tab_button_click

class SplitColumn:
    def __init__(self):
        # 미리 정의된 구분자 옵션
        self.predefined_delimiters = [
            {"value": ",", "label": "쉼표 (,)"},
            {"value": ";", "label": "세미콜론 (;)"},
            {"value": " ", "label": "공백 ( )"},
            {"value": "\t", "label": "탭 (\\t)"},
            {"value": "|", "label": "파이프 (|)"},
            {"value": "-", "label": "하이픈 (-)"},
            {"value": "_", "label": "언더스코어 (_)"},
            {"value": ".", "label": "점 (.)"},
            {"value": ":", "label": "콜론 (:)"},
            {"value": "custom", "label": "직접 입력"}
        ]
        
    def button_layout(self):
        """메뉴에 표시될 버튼 레이아웃"""
        return dbpc.Button(
            "Split Column", 
            id="split-column-btn", 
            icon="segmented-control", 
            minimal=True, 
            outlined=True
        )
        
    def tab_layout(self):
        """분할 기능 탭 레이아웃"""
        return dmc.Paper(
            children=[
                dmc.Group([
                    dbpc.EntityTitle(
                        title="Split Text to Columns", 
                        heading="H5", 
                        icon="segmented-control"
                    )
                ], grow=True),
                dmc.Space(h=10),
                
                # 소스 컬럼 선택
                dmc.Select(
                    id="split-column-source",
                    label="소스 컬럼 선택",
                    description="분할할 텍스트가 포함된 컬럼을 선택하세요",
                    placeholder="컬럼 선택...",
                    searchable=True,
                    clearable=False,
                    data=[],
                    size="md",
                    required=True,
                    leftSection=dbpc.Icon(icon="th-derived"),
                ),
                
                dmc.Space(h=20),
                
                # 구분자 기반 분할 옵션
                html.Div(
                    id="split-column-delimiter-container",
                    children=[
                        dmc.Select(
                            id="split-column-delimiter-select",
                            label="구분자 선택",
                            description="텍스트를 분할할 구분자를 선택하세요",
                            placeholder="구분자 선택...",
                            data=self.predefined_delimiters,
                            value=",",
                            size="sm",
                            searchable=True,
                        ),
                        dmc.Space(h=10),
                        # 직접 입력 필드 (선택한 값이 'custom'일 때만 표시)
                        html.Div(
                            id="split-column-custom-delimiter-container",
                            style={"display": "none"},
                            children=[
                                dmc.TextInput(
                                    id="split-column-custom-delimiter",
                                    label="직접 입력",
                                    description="분할에 사용할 구분자를 직접 입력하세요",
                                    placeholder="예: /, #, => 등",
                                    size="sm",
                                ),
                            ],
                        ),
                    ]
                ),
                
                dmc.Space(h=20),
                
                # 추가 옵션
                dmc.Group([
                    dmc.Checkbox(
                        id="split-column-keep-original",
                        label="원본 컬럼 유지",
                        description="분할 후에도 원본 컬럼을 유지합니다",
                        checked=True,
                        size="sm",
                    ),
                    dmc.Checkbox(
                        id="split-column-skip-empty",
                        label="빈 결과 건너뛰기",
                        description="분할 결과가 빈 문자열인 경우 해당 컬럼을 생성하지 않습니다",
                        checked=True,
                        size="sm",
                    ),
                ]),
                
                dmc.Space(h=20),
                
                # 결과 컬럼 이름 설정
                dmc.RadioGroup(
                    id="split-column-naming-method",
                    label="결과 컬럼 이름 지정 방법",
                    description="분할된 결과 컬럼의 이름 지정 방법을 선택하세요",
                    value="auto",
                    children=[
                        dmc.Radio(value="auto", label="자동 생성 (컬럼명_1, 컬럼명_2, ...)"),
                        dmc.Radio(value="custom", label="직접 입력"),
                    ],
                ),
                
                dmc.Space(h=10),
                
                # 커스텀 컬럼 이름 입력 (naming_method가 'custom'일 때만 표시)
                html.Div(
                    id="split-column-custom-names-container",
                    style={"display": "none"},
                    children=[
                        dmc.TextInput(
                            id="split-column-custom-names",
                            label="커스텀 컬럼 이름",
                            description="쉼표(,)로 구분하여 컬럼 이름을 입력하세요",
                            placeholder="첫번째컬럼,두번째컬럼,세번째컬럼",
                            size="sm",
                        ),
                    ],
                ),
                
                dmc.Space(h=20),
                
                # 미리보기 영역
                dmc.Paper(
                    id="split-column-preview-container",
                    withBorder=True,
                    p="sm",
                    style={"maxHeight": "200px", "overflow": "auto"},
                    children=[
                        dmc.Text("미리보기: 컬럼과 분할 방법을 선택하면 변환 예시가 표시됩니다.", size="sm", c="dimmed"),
                    ],
                ),
                
                dmc.Space(h=20),
                
                # 적용 버튼
                dmc.Group([
                    dbpc.Button(
                        "Apply", 
                        id="split-column-apply-btn", 
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
                                    dmc.Text("1. 분할할 텍스트가 포함된 컬럼을 선택하세요.", size="sm"),
                                    dmc.Text("2. 구분자를 선택하거나 직접 입력하세요.", size="sm"),
                                    dmc.Text("3. 결과 컬럼의 이름 지정 방법을 선택하세요.", size="sm"),
                                    dmc.Text("4. 필요한 추가 옵션을 설정하세요.", size="sm"),
                                    dmc.Text("5. 미리보기를 확인하고 적용 버튼을 클릭하세요.", size="sm"),
                                    dmc.Space(h=10),
                                    dmc.Text("예시:", w=500, size="sm"),
                                    dmc.Text("- 이메일에서 ID와 도메인 분리: '@' (결과: [id, domain])", size="sm"),
                                    dmc.Text("- 날짜 형식 분할: '-' (2023-01-30 → [2023, 01, 30])", size="sm"),
                                    dmc.Text("- IP 주소 분할: '.' (192.168.0.1 → [192, 168, 0, 1])", size="sm"),
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
            withBorder=True
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
            return handle_tab_button_click(n_clicks, current_model, "split-column-tab", "Split Column")


        @app.callback(
            Output("split-column-source", "data"),
            Input("split-column-btn", "n_clicks"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True
        )
        def update_column_list(n_clicks, columnDefs):
            """Split Column 버튼 클릭 시 컬럼 목록 로드"""
            if n_clicks is None or not columnDefs:
                return []
                
            # 보호할 컬럼 리스트 (시스템 컬럼)
            protected_columns = ["uniqid", "group", "childCount"]
            
            # 문자열 타입 컬럼만 필터링
            df = SSDF.dataframe
            text_columns = []
            
            for col in df.columns:
                if col not in protected_columns:
                    col_dtype = df[col].dtype
                    if col_dtype == pl.Utf8 or col_dtype == pl.String or col_dtype == pl.Categorical:
                        text_columns.append({"label": col, "value": col})
            
            return text_columns
                
        @app.callback(
            Output("split-column-custom-delimiter-container", "style"),
            Input("split-column-delimiter-select", "value"),
            prevent_initial_call=True
        )
        def toggle_custom_delimiter_input(delimiter):
            """직접 입력을 선택한 경우 커스텀 구분자 입력 필드 표시"""
            if delimiter == "custom":
                return {"display": "block"}
            return {"display": "none"}
            
        @app.callback(
            Output("split-column-custom-names-container", "style"),
            Input("split-column-naming-method", "value"),
            prevent_initial_call=True
        )
        def toggle_custom_names_input(naming_method):
            """직접 입력을 선택한 경우 커스텀 컬럼 이름 입력 필드 표시"""
            if naming_method == "custom":
                return {"display": "block"}
            return {"display": "none"}
            
        @app.callback(
            Output("split-column-preview-container", "children"),
            [
                Input("split-column-source", "value"),
                Input("split-column-delimiter-select", "value"),
                Input("split-column-custom-delimiter", "value"),
                Input("split-column-naming-method", "value"),
                Input("split-column-custom-names", "value"),
                Input("split-column-skip-empty", "checked")
            ],
            prevent_initial_call=True
        )
        def update_preview(source_column, delimiter_select, custom_delimiter, 
                          naming_method, custom_names, skip_empty):
            """선택한 설정에 따라 미리보기 업데이트"""
            if not source_column:
                return [dmc.Text("미리보기: 소스 컬럼을 선택하세요.", size="sm", c="dimmed")]
                
            try:
                df = SSDF.dataframe
                
                # 소스 컬럼에서 최대 5개의 샘플 값 선택 (null이 아닌 값 중에서)
                sample_values = []
                count = 0
                
                for val in df[source_column]:
                    if val is not None and val != "" and count < 5:
                        sample_values.append(val)
                        count += 1
                        
                if not sample_values:
                    return [dmc.Text("선택한 컬럼에 표시할 샘플 데이터가 없습니다.", size="sm", c="dimmed")]
                
                # 구분자 설정
                actual_delimiter = custom_delimiter if delimiter_select == "custom" else delimiter_select
                if not actual_delimiter and delimiter_select == "custom":
                    return [dmc.Text("미리보기: 직접 입력 구분자를 입력하세요.", size="sm", c="dimmed")]
                
                # 각 샘플 값에 대해 분할 수행
                split_results = []
                for val in sample_values:
                    split_values = str(val).split(actual_delimiter)
                    # 빈 결과 건너뛰기 옵션이 활성화된 경우 빈 문자열 제거
                    if skip_empty:
                        split_values = [v for v in split_values if v]
                    split_results.append((val, split_values))
                
                # 컬럼 이름 생성
                column_names = []
                if naming_method == "auto":
                    # 자동 생성 (최대 분할 개수에 맞춰 생성)
                    max_splits = max(len(split_values) for _, split_values in split_results)
                    column_names = [f"{source_column}_{i+1}" for i in range(max_splits)]
                else:
                    # 사용자 정의 이름
                    if custom_names:
                        column_names = [name.strip() for name in custom_names.split(",")]
                    else:
                        return [dmc.Text("미리보기: 직접 입력 컬럼 이름을 입력하세요.", size="sm", c="dimmed")]
                
                # 미리보기 테이블 생성
                preview_content = []
                
                # 설정 정보 요약
                delimiter_display = actual_delimiter.replace("\t", "\\t").replace(" ", "공백")
                method_info = f"구분자: '{delimiter_display}'"
                
                preview_content.append(
                    dmc.Text(
                        f"컬럼 '{source_column}'의 분할 미리보기 - {method_info}:", 
                        size="sm", 
                        w=500,
                        mb="xs"
                    )
                )
                
                # 각 샘플에 대한 미리보기 테이블 생성
                for i, (original, split_values) in enumerate(split_results):
                    # 헤더 생성
                    header_cells = [
                        dmc.TableTh("원본", style={"width": "30%"}),
                    ]
                    
                    for j, name in enumerate(column_names):
                        if j < len(split_values):
                            header_cells.append(dmc.TableTh(name))
                        else:
                            header_cells.append(dmc.TableTh(f"{name} (빈 값)"))
                    
                    # 데이터 셀 생성
                    data_cells = [
                        dmc.TableTd(original),
                    ]
                    
                    for j, name in enumerate(column_names):
                        if j < len(split_values):
                            data_cells.append(dmc.TableTd(split_values[j]))
                        else:
                            data_cells.append(dmc.TableTd("-", style={"color": "lightgray"}))
                    
                    # 테이블 생성
                    preview_table = dmc.Table(
                        [
                            dmc.TableThead(dmc.TableTr(header_cells)),
                            dmc.TableTbody([dmc.TableTr(data_cells)]),
                        ],
                        striped=True,
                        highlightOnHover=True,
                        withTableBorder=True,
                        withColumnBorders=True,
                        mb="md"
                    )
                    
                    preview_content.append(preview_table)
                
                return preview_content
                
            except Exception as e:
                logger.error(f"미리보기 생성 오류: {str(e)}")
                return [
                    dmc.Alert(
                        f"미리보기를 생성할 수 없습니다: {str(e)}",
                        color="red",
                        variant="light"
                    )
                ]

        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            [
                Input("split-column-apply-btn", "n_clicks")
            ],
            [
                State("split-column-source", "value"),
                State("split-column-delimiter-select", "value"),
                State("split-column-custom-delimiter", "value"),
                State("split-column-naming-method", "value"),
                State("split-column-custom-names", "value"),
                State("split-column-keep-original", "checked"),
                State("split-column-skip-empty", "checked")
            ],
            prevent_initial_call=True
        )
        def apply_split_column(n_clicks, source_column, delimiter_select, custom_delimiter, 
                            naming_method, custom_names, keep_original, skip_empty):
            """분할 적용"""
            if not n_clicks or not source_column:
                raise exceptions.PreventUpdate
                
            try:
                # 원본 데이터프레임 복사
                df = SSDF.dataframe.clone()
                
                # 구분자 설정
                actual_delimiter = custom_delimiter if delimiter_select == "custom" else delimiter_select
                if not actual_delimiter and delimiter_select == "custom":
                    return ([dbpc.Toast(
                        message="직접 입력 구분자를 입력하세요.",
                        intent="warning",
                        icon="warning-sign"
                    )], no_update)
                
                # 분할 함수 정의
                def split_text(text):
                    if text is None or text == "":
                        return []
                    parts = str(text).split(actual_delimiter)
                    if skip_empty:
                        return [p for p in parts if p]
                    return parts
                
                # 각 행에 대해 분할 처리
                split_results = []
                max_splits = 0
                
                # 샘플 데이터로 최대 분할 수 확인 (모든 행을 처리하지 않고 효율적으로)
                sample_size = min(1000, df.height)  # 최대 1000개 행 샘플링
                sample_df = df.slice(0, sample_size)
                
                for val in sample_df[source_column]:
                    split_parts = split_text(val)
                    split_results.append(split_parts)
                    max_splits = max(max_splits, len(split_parts))
                
                # 최대 분할 수가 0인 경우 (모든 결과가 빈 문자열인 경우)
                if max_splits == 0:
                    return ([dbpc.Toast(
                        message=f"분할 결과가 없습니다. 다른 구분자를 시도해보세요.",
                        intent="warning",
                        icon="warning-sign"
                    )], no_update)
                
                # 컬럼 이름 생성
                if naming_method == "auto":
                    # 자동 생성
                    column_names = [f"{source_column}_{i+1}" for i in range(max_splits)]
                else:
                    # 사용자 정의 이름
                    if custom_names:
                        column_names = [name.strip() for name in custom_names.split(",")]
                        # 사용자가 제공한 이름이 충분하지 않은 경우, 나머지는 자동 생성
                        if len(column_names) < max_splits:
                            column_names.extend([f"{source_column}_{i+1}" for i in range(len(column_names), max_splits)])
                    else:
                        column_names = [f"{source_column}_{i+1}" for i in range(max_splits)]
                
                # 이미 존재하는 컬럼명 확인 및 처리
                existing_columns = set(df.columns)
                for i, name in enumerate(column_names):
                    if name in existing_columns:
                        # 중복 이름이 있는 경우 이름 수정
                        j = 1
                        new_name = f"{name}_{j}"
                        while new_name in existing_columns:
                            j += 1
                            new_name = f"{name}_{j}"
                        column_names[i] = new_name
                
                # 각 분할 결과를 새 컬럼으로 추가
                for i, col_name in enumerate(column_names):
                    if i < max_splits:
                        # i번째 요소 추출 함수
                        def get_split_item(text, idx=i):
                            parts = split_text(text)
                            return parts[idx] if idx < len(parts) else None
                        
                        # 새 컬럼 추가
                        df = df.with_columns(
                            pl.col(source_column).map_elements(lambda x: get_split_item(x), return_dtype=pl.Utf8).alias(col_name)
                        )
                
                # 원본 컬럼 제거 (keep_original이 False인 경우)
                if not keep_original:
                    df = df.drop(source_column)
                
                # 성공 메시지 및 변경된 데이터프레임 반영
                SSDF.dataframe = df
                updated_columnDefs = generate_column_definitions(df)
                
                # 구분자 표시 생성
                delimiter_display = actual_delimiter.replace("\t", "\\t").replace(" ", "공백")
                
                return ([dbpc.Toast(
                    message=f"컬럼 '{source_column}'이(가) 구분자 '{delimiter_display}'로 {len(column_names)}개 컬럼으로 분할되었습니다.",
                    intent="success",
                    icon="endorsed",
                    timeout=3000
                )], updated_columnDefs)
                
            except Exception as e:
                # 전체 처리 오류
                logger.error(f"컬럼 분할 처리 오류: {str(e)}")
                return ([dbpc.Toast(
                    message=f"컬럼 분할 처리 오류: {str(e)}",
                    intent="danger",
                    icon="error"
                )], no_update)