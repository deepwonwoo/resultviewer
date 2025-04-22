import re
import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, no_update, exceptions, ctx

from utils.data_processing import displaying_df
from utils.db_management import SSDF
from components.grid.dag.column_definitions import generate_column_definitions, SYSTEM_COLUMNS
from components.menu.edit.utils import find_tab_in_layout

class AddColumn:
    def __init__(self):
        self.data_types = [
            {"label": "자동 감지", "value": "auto"},
            {"label": "문자열 (String)", "value": "str"},
            {"label": "정수 (Integer)", "value": "int"},
            {"label": "실수 (Float)", "value": "float"},
            {"label": "불리언 (Boolean)", "value": "bool"}
        ]
        self.boolean_true = ["true", "1", "yes", "y", "ok", "o", "O"]
        self.boolean_false = ["false", "0", "no", "n", "no", "x", "X"]
        
    def button_layout(self):
        return dbpc.Button(
            "Add Column", 
            id="add-column-btn", 
            icon="add-column-left", 
            minimal=True, 
            outlined=True
        )


    def tab_layout(self):
        return dmc.Paper(
            children=[
                dmc.Group([
                    dbpc.EntityTitle(
                        title="Add Column", 
                        heading="H5", 
                        icon="add-column-left"
                    )
                ], grow=True),
                dmc.Space(h=10),
                # Header input
                dmc.TextInput(
                    id="add-column-header-input",
                    value="",
                    size="sm",
                    placeholder="새 컬럼 이름 입력",
                    label="New Column Name",
                    required=True,
                    description="컬럼 이름은 공백 없이 영문자, 숫자, 언더스코어(_)만 사용 가능합니다",
                    leftSection=dbpc.Icon(icon="widget-header"),
                ),
                dmc.Space(h=15),
                
                # Input method selection tabs
                dmc.Tabs(
                    id="add-column-tabs",
                    variant="outline",
                    value="default",
                    children=[
                        dmc.TabsList([
                            dmc.TabsTab("Default Value", value="default", leftSection=dbpc.Icon(icon="edit")),
                            dmc.TabsTab("Copy Column", value="copy", leftSection=dbpc.Icon(icon="th-derived"))
                        ]),
                        
                        # Default value input tab panel
                        dmc.TabsPanel(
                            value="default",
                            children=[
                                dmc.Space(h=10),
                                dmc.Select(
                                    id="add-column-datatype",
                                    label="Data Type",
                                    description="새 컬럼의 데이터 타입을 선택하세요",
                                    data=self.data_types,
                                    value="auto",
                                    size="sm",
                                ),
                                dmc.Space(h=10),
                                dmc.TextInput(
                                    id="add-column-value-input",
                                    size="sm",
                                    value="",
                                    label="Default Value",
                                    placeholder="모든 행에 적용될 기본값 입력",
                                    leftSection=dbpc.Icon(icon="edit"),
                                ),
                                dmc.Space(h=5),
                                # Value preview
                                dmc.Text(
                                    id="add-column-value-preview",
                                    size="sm",
                                    c="dimmed",
                                    style={"fontStyle": "italic"}
                                )
                            ]
                        ),
                        
                        # Column copy tab panel
                        dmc.TabsPanel(
                            value="copy",
                            children=[
                                dmc.Space(h=10),
                                dmc.Select(
                                    id="add-column-copy-select",
                                    label="Source Column",
                                    description="복사할 원본 컬럼을 선택하세요",
                                    data=[],
                                    leftSection=dbpc.Icon(icon="th-derived"),
                                    searchable=True,
                                    nothingFoundMessage="일치하는 컬럼이 없습니다",
                                    size="sm",
                                ),
                                dmc.Space(h=10),
                                dmc.Checkbox(
                                    id="add-column-transform-checkbox",
                                    label="Apply Transform Function",
                                    description="원본 컬럼 값에 변환 함수를 적용할 수 있습니다",
                                ),
                                dmc.Space(h=10),
                                # Transform function selection (only shown when checkbox is selected)
                                html.Div(
                                    id="add-column-transform-container",
                                    style={"display": "none"},
                                    children=[
                                        dmc.Select(
                                            id="add-column-transform-select",
                                            label="변환 함수",
                                            data=[
                                                {"label": "대문자로 변환", "value": "upper"},
                                                {"label": "소문자로 변환", "value": "lower"},
                                                {"label": "첫 글자만 대문자로", "value": "title"},
                                                {"label": "공백 제거", "value": "strip"},
                                                {"label": "숫자에 10 곱하기", "value": "multiply_10"},
                                                {"label": "숫자에 100 곱하기", "value": "multiply_100"},
                                                {"label": "숫자에 1000 곱하기", "value": "multiply_1000"},
                                            ],
                                            size="sm",
                                        ),
                                        dmc.Space(h=5),
                                        # Transform result preview
                                        dmc.Text(
                                            id="add-column-transform-preview",
                                            size="sm",
                                            c="dimmed",
                                            style={"fontStyle": "italic"}
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                
                dmc.Space(h=15),
                dmc.Group([
                    dbpc.Button(
                        "Apply(left)", 
                        id="add-column-apply-left-btn", 
                        outlined=True,
                        icon="add-column-left",
                        intent="primary"
                    ),
                    dbpc.Button(
                        "Apply(right)", 
                        id="add-column-apply-right-btn", 
                        outlined=True,
                        icon="add-column-right",
                        intent="primary"
                    ),
                ], align="center", grow=True),
                
                # Help section
                dmc.Space(h=20),
                dmc.Accordion(
                    value="",
                    children=[
                        dmc.AccordionItem(
                            [
                                dmc.AccordionControl("도움말"),
                                dmc.AccordionPanel([
                                    dmc.Text("1. 기본값 설정: 모든 행에 동일한 값을 가진 새 컬럼을 추가합니다."),
                                    dmc.Text("2. 컬럼 복사: 기존 컬럼을 복사하여 새 컬럼을 만듭니다."),
                                    dmc.Text("3. 변환 함수: 원본 데이터에 특정 변환을 적용할 수 있습니다.")
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
            Input("add-column-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True
        )
        def handle_add_column_button_click(n_clicks, current_model):
            if n_clicks is None:
                raise exceptions.PreventUpdate

            dff = displaying_df()
            if dff is None:
                return no_update, [dbpc.Toast(message=f"데이터가 로드되지 않았습니다", intent="warning", icon="warning-sign")]

            # 기존 탭 검색
            tab_search_result = find_tab_in_layout(current_model, "col-add-tab")
            
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
                "name": "Add Column",
                "component": "button",
                "enableClose": True,
                "id": "col-add-tab"
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
            Output("add-column-copy-select", "data"),
            Input("add-column-tabs", "value"),
            State("aggrid-table", "columnDefs")
        )
        def update_column_list(tab_value, columnDefs):
            """탭 변경 시 컬럼 목록 업데이트"""
            if tab_value != "copy" or not columnDefs:
                return []
                
            column_data = [
                {"label": col["field"], "value": col["field"]} 
                for col in columnDefs if col["field"] != "waiver" and col["field"] != "uniqid"
            ]
            return column_data
            
        @app.callback(
            Output("add-column-transform-container", "style"),
            Input("add-column-transform-checkbox", "checked")
        )
        def toggle_transform_options(checked):
            """변환 함수 체크박스 상태에 따라 변환 옵션 표시/숨김"""
            if checked:
                return {"display": "block"}
            return {"display": "none"}
            
        @app.callback(
            Output("add-column-value-preview", "children"),
            Input("add-column-value-input", "value"),
            Input("add-column-datatype", "value")
        )
        def update_value_preview(value, datatype):
            """입력된 값과 데이터 타입에 따라 미리보기 업데이트"""
            if not value:
                return "미리보기: (값이 입력되지 않음)"
                
            try:
                if datatype == "auto":
                    # 자동 타입 감지
                    if value.isdigit():
                        preview = f"미리보기: {int(value)} (정수)"
                    elif value.replace(".", "", 1).isdigit():
                        preview = f"미리보기: {float(value)} (실수)"
                    elif value.lower() in ["true", "false"]:
                        preview = f"미리보기: {value.lower() == 'true'} (불리언)"
                    else:
                        preview = f"미리보기: '{value}' (문자열)"
                elif datatype == "int":
                    preview = f"미리보기: {int(value)} (정수)"
                elif datatype == "float":
                    preview = f"미리보기: {float(value)} (실수)"
                elif datatype == "bool":
                    # 불리언 타입 처리 (true/false, 1/0 등을 처리)
                    if value.lower() in self.boolean_true:
                        preview = "미리보기: True (불리언)"
                    elif value.lower() in self.boolean_false:
                        preview = "미리보기: False (불리언)"
                    else:
                        preview = "미리보기: 유효하지 않은 불리언 값"
                else:  # str
                    preview = f"미리보기: '{value}' (문자열)"
                    
                return preview
            except Exception as e:
                return f"미리보기: 변환 오류 ({str(e)})"
                
        @app.callback(
            Output("add-column-transform-preview", "children"),
            Input("add-column-transform-select", "value"),
            Input("add-column-copy-select", "value")
        )
        def update_transform_preview(transform, column):
            """변환 함수와 선택된 컬럼에 따라 변환 결과 미리보기"""
            if not transform or not column or column not in SSDF.dataframe.columns:
                return "미리보기: (변환 함수나 컬럼이 선택되지 않음)"
                
            try:
                # 선택된 컬럼의 첫 번째 비null 값 찾기
                first_value = None
                for val in SSDF.dataframe[column]:
                    if val is not None and val != "":
                        first_value = val
                        break
                        
                if first_value is None:
                    return "미리보기: (원본 컬럼에 유효한 값이 없음)"
                    
                # 선택된 변환 함수 적용
                if transform == "upper":
                    result = str(first_value).upper()
                elif transform == "lower":
                    result = str(first_value).lower()
                elif transform == "title":
                    result = str(first_value).title()
                elif transform == "strip":
                    result = str(first_value).strip()
                elif transform == "multiply_10":
                    result = float(first_value) * 10
                elif transform == "multiply_100":
                    result = float(first_value) * 100
                elif transform == "multiply_1000":
                    result = float(first_value) * 1000
                else:
                    result = first_value
                    
                return f"미리보기: '{first_value}' → '{result}'"
            except Exception as e:
                return f"미리보기: 변환 오류 ({str(e)})"


        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("add-column-header-input", "value"),
            Output("add-column-value-input", "value"),
            Output("add-column-copy-select", "value"),
            Output("add-column-transform-checkbox", "checked"),
            Input("add-column-apply-left-btn", "n_clicks"),
            Input("add-column-apply-right-btn", "n_clicks"),
            State("add-column-header-input", "value"),
            State("add-column-tabs", "value"),
            State("add-column-datatype", "value"),
            State("add-column-value-input", "value"),
            State("add-column-copy-select", "value"),
            State("add-column-transform-checkbox", "checked"),
            State("add-column-transform-select", "value"),
            prevent_initial_call=True
        )
        def handle_add_column_submission(
            left_clicks, right_clicks, header, tab_value, datatype, default_value, 
            copy_column, apply_transform, transform_function
        ):
            """컬럼 추가 로직 실행"""
            if not left_clicks and not right_clicks:
                raise exceptions.PreventUpdate
                
            # Determine which button was clicked using ctx.triggered_id
            button_clicked = ctx.triggered_id
            add_to_left = button_clicked == "add-column-apply-left-btn"
                
            # 헤더 이름 검증
            if not header:
                return ([dbpc.Toast(
                    message="컬럼 이름을 입력해주세요",
                    intent="warning",
                    icon="warning-sign"
                )], no_update, no_update, no_update, no_update, no_update)
                
            # 특수문자 및 공백 검증 (언더스코어는 허용)
            
            if not re.match(r'^[a-zA-Z0-9_]+$', header):
                return ([dbpc.Toast(
                    message="컬럼 이름은 영문자, 숫자, 언더스코어(_)만 사용 가능합니다",
                    intent="warning",
                    icon="warning-sign"
                )], no_update, no_update, no_update, no_update, no_update)

            # 중복 이름 검증
            if header in SSDF.dataframe.columns:
                return ([dbpc.Toast(
                    message=f"'{header}' 컬럼이 이미 존재합니다",
                    intent="warning",
                    icon="warning-sign"
                )], no_update, no_update, no_update, no_update, no_update)

            # 보호된 컬럼 검증
            if header in SYSTEM_COLUMNS:
                if header in ["waiver", "user"]:
                    pass  # 추가 가능하므로 계속 진행
                else:
                    return ([dbpc.Toast(message=f"'{header}'는 시스템 예약 컬럼입니다. 다른 이름을 사용해주세요.", 
                            intent="warning", icon="warning-sign")], 
                            no_update, no_update, no_update, no_update, no_update)


            try:
                rows_count = len(SSDF.dataframe)
                
                if tab_value == "default":
                    # 기본값 모드 - 데이터 타입에 따라 변환
                    if not default_value and default_value != "0":
                        # 빈 값이면 null로 설정
                        new_column = pl.Series(header, [None] * rows_count)
                    else:
                        try:
                            if datatype == "auto":
                                # 자동 타입 감지
                                if default_value.isdigit():
                                    new_column = pl.Series(header, [int(default_value)] * rows_count)
                                elif default_value.replace(".", "", 1).isdigit():
                                    new_column = pl.Series(header, [float(default_value)] * rows_count)
                                elif default_value.lower() in ["true", "false"]:
                                    new_column = pl.Series(header, [default_value.lower() == "true"] * rows_count)
                                else:
                                    new_column = pl.Series(header, [str(default_value)] * rows_count)
                            elif datatype == "int":
                                new_column = pl.Series(header, [int(default_value)] * rows_count)
                            elif datatype == "float":
                                new_column = pl.Series(header, [float(default_value)] * rows_count)
                            elif datatype == "bool":
                                bool_value = default_value.lower() in self.boolean_true
                                new_column = pl.Series(header, [bool_value] * rows_count)
                            else:  # str
                                new_column = pl.Series(header, [str(default_value)] * rows_count)
                        except ValueError as e:
                            return ([dbpc.Toast(
                                message=f"값 변환 오류: {str(e)}",
                                intent="danger",
                                icon="error"
                            )], no_update, no_update, no_update, no_update, no_update)
                    
                    # 컬럼 추가
                    if add_to_left:
                        # 왼쪽에 컬럼 추가
                        new_df = pl.DataFrame({header: new_column})
                        SSDF.dataframe = pl.concat([new_df, SSDF.dataframe], how="horizontal")
                    else:
                        # 오른쪽에 컬럼 추가
                        SSDF.dataframe = SSDF.dataframe.with_columns([new_column])
                    
                    # 성공 메시지
                    position = "왼쪽" if add_to_left else "오른쪽"
                    toast_message = f"'{header}' 컬럼이 {position}에 추가되었습니다 (기본값: {default_value})"
                    
                else:  # copy 모드
                    # 원본 컬럼 검증
                    if not copy_column:
                        return ([dbpc.Toast(
                            message="복사할 원본 컬럼을 선택해주세요",
                            intent="warning",
                            icon="warning-sign"
                        )], no_update, no_update, no_update, no_update, no_update)
                        
                    if copy_column not in SSDF.dataframe.columns:
                        return ([dbpc.Toast(
                            message=f"선택한 컬럼 '{copy_column}'을 찾을 수 없습니다",
                            intent="warning",
                            icon="warning-sign"
                        )], no_update, no_update, no_update, no_update, no_update)
                        
                    # 변환 함수 적용
                    if apply_transform and transform_function:
                        try:
                            if transform_function == "upper":
                                new_column = pl.col(copy_column).cast(pl.Utf8).str.to_uppercase().alias(header)
                            elif transform_function == "lower":
                                new_column = pl.col(copy_column).cast(pl.Utf8).str.to_lowercase().alias(header)
                            elif transform_function == "title":
                                # 첫 글자만 대문자로 변환 (polars에 직접적인 함수가 없어 문자열 연산으로 구현)
                                new_column = (
                                    pl.col(copy_column).cast(pl.Utf8)
                                    .str.slice(0, 1).str.to_uppercase() + 
                                    pl.col(copy_column).cast(pl.Utf8).str.slice(1).str.to_lowercase()
                                ).alias(header)
                            elif transform_function == "strip":
                                new_column = pl.col(copy_column).cast(pl.Utf8).str.strip_chars().alias(header)
                            elif transform_function == "multiply_10":
                                new_column = (pl.col(copy_column).cast(pl.Float64) * 10).alias(header)
                            elif transform_function == "multiply_100":
                                new_column = (pl.col(copy_column).cast(pl.Float64) * 100).alias(header)
                            elif transform_function == "multiply_1000":
                                new_column = (pl.col(copy_column).cast(pl.Float64) * 1000).alias(header)
                            else:
                                # 기본: 단순 복사
                                new_column = pl.col(copy_column).alias(header)
                        except Exception as e:
                            return ([dbpc.Toast(
                                message=f"변환 함수 적용 오류: {str(e)}",
                                intent="danger",
                                icon="error"
                            )], no_update, no_update, no_update, no_update, no_update)
                    else:
                        # 단순 복사
                        new_column = pl.col(copy_column).alias(header)
                        
                    # 컬럼 추가
                    if add_to_left:
                        # 왼쪽에 컬럼 추가
                        new_df = pl.DataFrame({header: SSDF.dataframe.select(new_column).to_series()})
                        SSDF.dataframe = pl.concat([new_df, SSDF.dataframe], how="horizontal")
                    else:
                        # 오른쪽에 컬럼 추가
                        SSDF.dataframe = SSDF.dataframe.with_columns(new_column)
                    
                    # 성공 메시지
                    position = "왼쪽" if add_to_left else "오른쪽"
                    transform_text = f", 변환: {transform_function}" if apply_transform else ""
                    toast_message = f"'{header}' 컬럼이 {position}에 추가되었습니다 (원본: {copy_column}{transform_text})"
                
                # 컬럼 정의 업데이트
                updated_columnDefs = generate_column_definitions(SSDF.dataframe)
                
                # 성공 토스트 메시지
                toast = dbpc.Toast(
                    message=toast_message,
                    intent="success",
                    icon="endorsed",
                    timeout=4000
                )
                
                # 폼 초기화
                return [toast], updated_columnDefs, "", "", None, False
                
            except Exception as e:
                # 오류 메시지
                return ([dbpc.Toast(
                    message=f"컬럼 추가 실패: {str(e)}",
                    intent="danger",
                    icon="error"
                )], no_update, no_update, no_update, no_update, no_update)