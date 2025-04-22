import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, no_update, exceptions, ctx

from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions, SYSTEM_COLUMNS
from components.menu.edit.utils import find_tab_in_layout


class DelColumn:
    def __init__(self):
        pass
        
    def button_layout(self):
        return dbpc.Button(
            "Delete Column", 
            id="delete-column-btn", 
            icon="remove-column", 
            minimal=True, 
            outlined=True
        )


    def tab_layout(self):
        return dmc.Paper(
            children=[
                dmc.Group([
                    dbpc.EntityTitle(
                        title="Delete Column", 
                        heading="H5", 
                        icon="remove-column"
                    )
                ], grow=True),
                dmc.Space(h=10),
                # 컬럼 선택 MultiSelect
                dmc.MultiSelect(
                    id="delete-column-select",
                    label="Select Column",
                    description="삭제할 컬럼을 선택하세요 (복수 선택 가능)",
                    placeholder="컬럼 선택...",
                    required=True,
                    searchable=True,
                    clearable=True,
                    data=[],
                    size="md",
                    leftSection=dbpc.Icon(icon="remove-column"),
                ),
                
                dmc.Space(h=20),
                
                # 필수 컬럼 보호 알림
                dmc.Alert(
                    "주의: 'uniqid'와 같은 시스템 컬럼과 현재 사용 중인 필수 컬럼은 삭제할 수 없습니다.",
                    title="주의",
                    color="yellow",
                    withCloseButton=True,
                ),
                
                dmc.Space(h=20),
                
                # 삭제 확인 체크박스
                dmc.Checkbox(
                    id="delete-column-confirm",
                    label="삭제를 확인합니다. 이 작업은 되돌릴 수 없습니다.",
                    size="sm",
                ),
                
                dmc.Space(h=15),
                
                # 삭제 버튼
                dmc.Group([
                    dbpc.Button(
                        "Delete", 
                        id="delete-column-apply-btn", 
                        outlined=True,
                        icon="trash",
                        intent="danger",
                        disabled=True
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
                                    dmc.Text("1. 삭제할 컬럼을 하나 이상 선택하세요."),
                                    dmc.Text("2. 삭제 확인 체크박스를 클릭하세요."),
                                    dmc.Text("3. Delete 버튼을 클릭하면 선택한 컬럼이 삭제됩니다."),
                                    dmc.Text("4. 시스템 및 필수 컬럼은 삭제할 수 없습니다.")
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
            Input("delete-column-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True
        )
        def handle_delete_column_button_click(n_clicks, current_model):
            """Delete Column 버튼 클릭 시 우측 패널에 탭 추가"""
            if n_clicks is None:
                raise exceptions.PreventUpdate
            dff = displaying_df()
            if dff is None:
                return no_update, [dbpc.Toast(message=f"데이터가 로드되지 않았습니다", intent="warning", icon="warning-sign")]

            # 기존 탭 검색
            tab_search_result = find_tab_in_layout(current_model, "col-del-tab")
            
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
                    # 메인 레이아웃에 있다면 경고 메시지 출력하고 새 탭 생성 시 고유 ID 사용
                    return no_update, [dbpc.Toast(message=f"기존 탭이 레이아웃에 있습니다.", intent="warning", icon="info-sign")]
            
            # 탭이 존재하지 않으면 정상적으로 진행
            right_border_index = next(
                (i for i, b in enumerate(current_model["borders"]) if b["location"] == "right"), 
                None
            )
            
            # 새로운 탭 정의
            new_tab = {
                "type": "tab",
                "name": "Delete Column",
                "component": "button",
                "enableClose": True,
                "id": "col-del-tab"
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
            Output("delete-column-select", "data"),
            Input("delete-column-btn", "n_clicks"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True
        )
        def update_column_list(n_clicks, columnDefs):
            """Delete Column 버튼 클릭 시 컬럼 목록 로드"""
            if n_clicks is None or not columnDefs:
                return []
            
            column_data = [
                {"label": col["field"], "value": col["field"]} 
                for col in columnDefs if col["field"] not in SYSTEM_COLUMNS
            ]
            
            return column_data
            
        @app.callback(
            Output("delete-column-apply-btn", "disabled"),
            [
                Input("delete-column-select", "value"),
                Input("delete-column-confirm", "checked")
            ]
        )
        def toggle_delete_button(selected_columns, confirmed):
            """선택된 컬럼과 확인 체크박스 상태에 따라 삭제 버튼 활성화/비활성화"""
            if not selected_columns or not confirmed:
                return True
            return False
            
        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("delete-column-select", "value"),
            Output("delete-column-confirm", "checked"),
            Input("delete-column-apply-btn", "n_clicks"),
            State("delete-column-select", "value"),
            prevent_initial_call=True
        )
        def handle_delete_column_submission(n_clicks, selected_columns):
            """컬럼 삭제 로직 실행"""
            if not n_clicks or not selected_columns:
                raise exceptions.PreventUpdate
                
            try:                
                protected_selected = [col for col in selected_columns if col in SYSTEM_COLUMNS]
                if protected_selected:
                    return ([dbpc.Toast(
                        message=f"다음 시스템 컬럼은 삭제할 수 없습니다: {', '.join(protected_selected)}",
                        intent="warning",
                        icon="warning-sign"
                    )], no_update, no_update, no_update)
                
                # 컬럼 삭제 실행
                SSDF.dataframe = SSDF.dataframe.drop(selected_columns)
                
                # 컬럼 정의 업데이트
                updated_columnDefs = generate_column_definitions(SSDF.dataframe)
                
                # 성공 토스트 메시지
                toast = dbpc.Toast(
                    message=f"{len(selected_columns)}개 컬럼이 삭제되었습니다: {', '.join(selected_columns)}",
                    intent="success",
                    icon="endorsed",
                    timeout=4000
                )
                
                # 폼 초기화
                return [toast], updated_columnDefs, [], False
                
            except Exception as e:
                # 오류 메시지
                logger.error(f"컬럼 삭제 실패: {str(e)}")
                return ([dbpc.Toast(
                    message=f"컬럼 삭제 실패: {str(e)}",
                    intent="danger",
                    icon="error"
                )], no_update, no_update, no_update)