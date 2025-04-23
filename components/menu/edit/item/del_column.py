import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, no_update, exceptions, dcc

from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions, SYSTEM_COLUMNS
from components.menu.edit.utils import find_tab_in_layout


class DelColumn:
    def __init__(self):
        self.protected_columns = ["uniqid", "group", "childCount"]
        self.warning_columns = ["waiver", "user"]

        
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
                    "waiver, user 컬럼은 삭제할 수 있지만 특별한 목적을 가진 컬럼이므로 주의가 필요합니다.",
                    title="주의", 
                    color="yellow", 
                    withCloseButton=True,
                    id="delete-column-protected-info"
                ),
                dmc.Space(h=15),
                # 선택된 컬럼 정보 표시 영역
                html.Div(id="delete-column-selection-info"),
                dmc.Space(h=15),
                # 삭제 확인 체크박스
                dmc.Checkbox(
                    id="delete-column-confirm", 
                    label="삭제를 확인합니다. 이 작업은 되돌릴 수 없습니다.", 
                    size="sm"
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
                ),
                # 상태 저장용 Store
                dcc.Store(id="delete-column-warned-columns", data=[]),
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
            column_data = []
            for col in columnDefs:
                field = col.get("field")
                if field not in self.protected_columns:
                    # 경고 컬럼인 경우 표시 추가
                    if field in self.warning_columns:
                        column_data.append({"label": f"{field} (주의: 특수 목적 컬럼)", "value": field})
                    else:
                        column_data.append({"label": field, "value": field})

            return column_data


        @app.callback(
            Output("delete-column-selection-info", "children"),
            Input("delete-column-select", "value"),
            prevent_initial_call=True
        )
        def update_selection_info(selected_columns):
            """선택된 컬럼에 대한 정보 표시"""
            if not selected_columns:
                return dmc.Alert(
                    "컬럼을 선택하면 추가 정보가 표시됩니다.", 
                    color="blue", 
                    variant="light",
                    withCloseButton=False
                )
            
            # 선택된 컬럼 중 경고 컬럼 확인
            warning_selected = [col for col in selected_columns if col in self.warning_columns]
            
            if warning_selected:
                return dmc.Alert(
                    children=[
                        dmc.Text(f"선택된 컬럼 중 {', '.join(warning_selected)}은(는) 특수 목적 컬럼입니다!", w=700),
                        dmc.Space(h=5),
                        dmc.Text("이 컬럼들은 Signoff ResultViewer의 중요 기능에 사용됩니다. 삭제 시 관련 기능이 정상 작동하지 않을 수 있습니다.", size="sm"),
                        dmc.Space(h=5),
                        dmc.Text(f"총 {len(selected_columns)}개 컬럼이 선택되었습니다.", size="sm")
                    ],
                    title="주의 필요!", 
                    color="orange", 
                    variant="light",
                    withCloseButton=False
                )
            else:
                return dmc.Alert(
                    f"총 {len(selected_columns)}개 컬럼이 선택되었습니다.", 
                    color="blue", 
                    variant="light",
                    withCloseButton=False
                )


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
                
            # 시스템 보호 컬럼이 포함되었는지 확인
            protected_selected = [col for col in selected_columns if col in self.protected_columns]
            if protected_selected:
                return True  # 보호 컬럼이 있으면 버튼 비활성화
                
            return False



        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("delete-column-select", "value"),
            Output("delete-column-confirm", "checked"),
            Output("delete-column-warned-columns", "data", allow_duplicate=True),
            Output("delete-column-select", "data", allow_duplicate=True),  # 컬럼 목록 업데이트를 위해 추가
            Input("delete-column-apply-btn", "n_clicks"),
            [
                State("delete-column-select", "value"),
                State("delete-column-warned-columns", "data"),
                State("aggrid-table", "columnDefs")  # 현재 컬럼 정의를 가져오기 위해 추가
            ],
            prevent_initial_call=True
        )
        def handle_delete_column_submission(n_clicks, selected_columns, warned_columns, columnDefs):
            """컬럼 삭제 로직 실행"""
            if not n_clicks or not selected_columns:
                raise exceptions.PreventUpdate

            try:
                # 시스템 보호 컬럼 체크
                protected_selected = [col for col in selected_columns if col in self.protected_columns]
                if protected_selected:
                    return ([dbpc.Toast(message=f"다음 시스템 컬럼은 삭제할 수 없습니다: {', '.join(protected_selected)}", intent="warning", icon="warning-sign")], 
                            no_update, no_update, no_update, no_update, no_update)

                # 경고 컬럼 확인 및 처리
                warning_selected = [col for col in selected_columns if col in self.warning_columns]
                
                # 이전에 경고하지 않은 경고 컬럼이 있는 경우 첫 번째 경고 표시
                new_warnings = [col for col in warning_selected if col not in warned_columns]
                if new_warnings and len(new_warnings) > 0:
                    warned_columns.extend(new_warnings)
                    return ([dbpc.Toast(
                        message=f"주의: {', '.join(new_warnings)} 컬럼은 특수 목적 컬럼입니다. 정말 삭제하시겠습니까? 삭제하려면 다시 Delete 버튼을 클릭하세요.", 
                        intent="warning", 
                        icon="warning-sign",
                        timeout=10000
                    )], no_update, selected_columns, True, warned_columns, no_update)

                # 모든 경고 확인이 완료되거나 경고 대상이 없는 경우 실제 삭제 수행
                # 백업 컬럼 데이터 (오류 발생 시 복구용)
                backup_data = {}
                for col in selected_columns:
                    if col in SSDF.dataframe.columns:
                        backup_data[col] = SSDF.dataframe[col]

                # 컬럼 삭제 실행
                try:
                    SSDF.dataframe = SSDF.dataframe.drop(selected_columns)
                except Exception as e:
                    # 오류 발생 시 원래 상태로 복원 시도
                    logger.error(f"컬럼 삭제 실패: {str(e)}")
                    
                    try:
                        # 복원 시도
                        for col, data in backup_data.items():
                            SSDF.dataframe = SSDF.dataframe.with_columns(data)
                    except Exception as restore_err:
                        logger.error(f"상태 복원 실패: {str(restore_err)}")
                        
                    return ([dbpc.Toast(message=f"컬럼 삭제 실패: {str(e)}", intent="danger", icon="error")], 
                            no_update, no_update, no_update, warned_columns, no_update)

                # 컬럼 정의 업데이트
                updated_columnDefs = generate_column_definitions(SSDF.dataframe)

                # 삭제된 컬럼 중 경고 컬럼이 있는 경우 특별 메시지 추가
                toast_message = f"{len(selected_columns)}개 컬럼이 삭제되었습니다: {', '.join(selected_columns)}"
                if warning_selected:
                    toast_message += f"\n주의: {', '.join(warning_selected)} 특수 목적 컬럼이 삭제되었습니다."

                # 성공 토스트 메시지
                toast = dbpc.Toast(message=toast_message, intent="success", icon="endorsed", timeout=4000)
                
                # 경고 컬럼 목록 초기화
                warned_columns = []
                
                # 업데이트된 컬럼 선택 목록 생성
                updated_column_data = []
                for col in updated_columnDefs:
                    field = col.get("field")
                    if field not in self.protected_columns:
                        # 경고 컬럼인 경우 표시 추가
                        if field in self.warning_columns:
                            updated_column_data.append({"label": f"{field} (주의: 특수 목적 컬럼)", "value": field})
                        else:
                            updated_column_data.append({"label": field, "value": field})

                # 폼 초기화 및 업데이트된 컬럼 목록 반환
                return [toast], updated_columnDefs, [], False, warned_columns, updated_column_data

            except Exception as e:
                # 오류 메시지
                logger.error(f"컬럼 삭제 실패: {str(e)}")
                return ([dbpc.Toast(message=f"컬럼 삭제 실패: {str(e)}", intent="danger", icon="error")], 
                        no_update, no_update, no_update, warned_columns, no_update)
