import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, no_update, exceptions, ctx, ALL

from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions, SYSTEM_COLUMNS
from components.menu.edit.utils import find_tab_in_layout


class RenameHeaders:
    def __init__(self):
        pass
        
    def button_layout(self):
        return dbpc.Button("Rename Headers", id="rename-headers-btn", icon="edit", minimal=True, outlined=True)
        
    def tab_layout(self):
        return dmc.Paper(
            children=[
                dmc.Group([dbpc.EntityTitle(title="Rename Column Headers", heading="H5", icon="edit")], grow=True),
                dmc.Space(h=10),
                
                # 도움말 메시지
                dmc.Alert(
                    "컬럼 헤더 이름을 변경합니다. 시스템 컬럼(uniqid, group, childCount)은 변경할 수 없습니다.",
                    title="안내",
                    color="blue",
                    variant="light",
                    mb=15,
                ),
                
                # 컬럼 선택 및 헤더 이름 변경 입력 영역
                html.Div(id="rename-headers-inputs-container"),
                
                dmc.Space(h=20),
                
                # 적용 버튼
                dmc.Group([
                    dbpc.Button("Apply", id="rename-headers-apply-btn", outlined=True, icon="tick", intent="primary")
                ], justify="center"),
                
                # 도움말 섹션
                dmc.Space(h=20),
                dmc.Accordion(
                    value="",
                    children=[
                        dmc.AccordionItem([
                            dmc.AccordionControl("도움말"),
                            dmc.AccordionPanel([
                                dmc.Text("1. 변경하고자 하는 컬럼의 새 이름을 입력하세요."),
                                dmc.Text("2. 새 이름은 영문자, 숫자, 언더스코어(_)만 사용 가능합니다."),
                                dmc.Text("3. 입력하지 않은 컬럼은 이름이 변경되지 않습니다."),
                                dmc.Text("4. Apply 버튼을 클릭하면 변경이 적용됩니다."),
                                dmc.Text("5. 시스템 컬럼(uniqid, group, childCount)은 변경할 수 없습니다.")
                            ])
                        ], value="help")
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
            Input("rename-headers-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True
        )
        def handle_rename_headers_button_click(n_clicks, current_model):
            """Rename Headers 버튼 클릭 시 우측 패널에 탭 추가"""
            if n_clicks is None:
                raise exceptions.PreventUpdate
                
            dff = displaying_df()
            if dff is None:
                return no_update, [dbpc.Toast(message=f"데이터가 로드되지 않았습니다", intent="warning", icon="warning-sign")]
                
            # 기존 탭 검색
            tab_search_result = find_tab_in_layout(current_model, "rename-headers-tab")
            
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
            right_border_index = next((i for i, b in enumerate(current_model["borders"]) if b["location"] == "right"), None)
            
            # 새로운 탭 정의
            new_tab = {"type": "tab", "name": "Rename Headers", "component": "button", "enableClose": True, "id": "rename-headers-tab"}
            
            patched_model = Patch()
            
            if right_border_index is not None:
                # 기존 right border 수정
                patched_model["borders"][right_border_index]["children"].append(new_tab)
                patched_model["borders"][right_border_index]["selected"] = len(current_model["borders"][right_border_index]["children"])
            else:
                # right border가 없으면 새로 추가
                patched_model["borders"].append({"type": "border", "location": "right", "size": 400, "selected": 0, "children": [new_tab]})
                
            return patched_model, no_update
            
        @app.callback(
            Output("rename-headers-inputs-container", "children"),
            Input("rename-headers-btn", "n_clicks"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True
        )
        def create_rename_inputs(n_clicks, columnDefs):
            """컬럼 이름 변경을 위한 입력 필드 생성"""
            if n_clicks is None or not columnDefs:
                return []
                
            input_fields = []
            
            # 헤더 행 추가
            input_fields.append(
                dmc.Grid(
                    [
                        dmc.GridCol(dmc.Text("현재 컬럼명", w="bold"), span=5),
                        dmc.GridCol(dmc.Text("새 컬럼명", w="bold"), span=7),
                    ],
                    mb=10
                )
            )
            
            # 각 컬럼에 대한 입력 필드 생성
            for col in columnDefs:
                field = col.get("field")
                if field and field not in SYSTEM_COLUMNS:
                    input_field = dmc.Grid(
                        [
                            dmc.GridCol(
                                dmc.Text(
                                    field, 
                                    style={"overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap"}
                                ), 
                                span=5
                            ),
                            dmc.GridCol(
                                dmc.TextInput(
                                    id={"type": "rename-header-input", "column": field},
                                    placeholder=f"새 이름 입력",
                                    value="",
                                    style={"width": "100%"}
                                ),
                                span=7
                            ),
                        ],
                        mb=10
                    )
                    input_fields.append(input_field)
            
            if not input_fields:
                return dmc.Alert("변경 가능한 컬럼이 없습니다.", color="yellow", variant="light")
                
            # 스크롤 가능한 컨테이너에 입력 필드들 배치
            return dmc.Paper(
                children=input_fields,
                style={"maxHeight": "400px", "overflow": "auto"},
                p="sm",
                withBorder=True
            )
            
        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("rename-headers-apply-btn", "n_clicks"),
            State({"type": "rename-header-input", "column": ALL}, "id"),
            State({"type": "rename-header-input", "column": ALL}, "value"),
            prevent_initial_call=True
        )
        def apply_header_changes(n_clicks, input_ids, input_values):
            """헤더 이름 변경 적용"""
            if not n_clicks:
                raise exceptions.PreventUpdate
                
            # 입력 값이 없는 경우
            if not input_ids or not input_values:
                return [dbpc.Toast(message=f"변경할 컬럼이 선택되지 않았습니다.", intent="warning", icon="warning-sign")], no_update
                
            try:
                # 키-값 매핑 생성
                column_mapping = {}
                for i, input_id in enumerate(input_ids):
                    original_name = input_id.get("column")
                    new_name = input_values[i].strip() if input_values[i] else ""
                    
                    # 새 이름이 입력된 경우만 처리
                    if new_name and new_name != original_name:
                        # 이름 유효성 검사 (영문자, 숫자, 언더스코어만 허용)
                        import re
                        if not re.match(r"^[a-zA-Z0-9_]+$", new_name):
                            return [dbpc.Toast(
                                message=f"컬럼명 '{new_name}'은(는) 유효하지 않습니다. 영문자, 숫자, 언더스코어(_)만 사용 가능합니다.",
                                intent="warning",
                                icon="warning-sign"
                            )], no_update
                            
                        # 이미 존재하는 컬럼명 확인
                        if new_name in SSDF.dataframe.columns:
                            return [dbpc.Toast(
                                message=f"컬럼명 '{new_name}'은(는) 이미 존재합니다. 다른 이름을 사용해주세요.",
                                intent="warning", 
                                icon="warning-sign"
                            )], no_update
                            
                        # 유효한 매핑 추가
                        column_mapping[original_name] = new_name
                
                # 변경할 컬럼이 없는 경우
                if not column_mapping:
                    return [dbpc.Toast(message=f"변경할 컬럼명이 없습니다.", intent="warning", icon="warning-sign")], no_update
                
                # 데이터프레임 컬럼 이름 변경
                df = SSDF.dataframe
                for old_name, new_name in column_mapping.items():
                    df = df.rename({old_name: new_name})
                
                SSDF.dataframe = df
                
                # 컬럼 정의 업데이트
                updated_columnDefs = generate_column_definitions(df)
                
                # 성공 메시지
                changed_count = len(column_mapping)
                column_list = ", ".join([f"'{old}' → '{new}'" for old, new in column_mapping.items()])
                
                return [dbpc.Toast(
                    message=f"{changed_count}개 컬럼명 변경 완료: {column_list}",
                    intent="success", 
                    icon="endorsed",
                    timeout=4000
                )], updated_columnDefs
                
            except Exception as e:
                # 오류 처리
                logger.error(f"컬럼명 변경 오류: {str(e)}")
                return [dbpc.Toast(message=f"컬럼명 변경 오류: {str(e)}", intent="danger", icon="error")], no_update