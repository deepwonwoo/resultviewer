# components/menu/analyze/item/ai.py
import os
import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, dcc, no_update, exceptions, ctx, callback, ALL
import uuid
from datetime import datetime

from utils.data_processing import displaying_df
from utils.db_management import SSDF
from components.menu.edit.utils import find_tab_in_layout

class AIAssistant:
    def __init__(self):
        # 대화 기록을 위한 초기화
        self.conversation_id = str(uuid.uuid4())
        self.messages = []
        
    def button_layout(self):
        return dbpc.Button(
            "AI 어시스턴트", 
            id="ai-assistant-btn", 
            icon="snowflake", 
            minimal=True, 
            outlined=True
        )

    def tab_layout(self):
        return dmc.Paper(
            children=[
                # 상단 타이틀 및 설정 영역
                dmc.Group(
                    [
                        dbpc.EntityTitle(
                            title="AI 어시스턴트", 
                            heading="H5", 
                            icon="ai"
                        ),
                        dmc.Menu(
                            [
                                dmc.MenuTarget(
                                    dbpc.Button("설정", icon="settings", minimal=True, small=True)
                                ),
                                dmc.MenuDropdown([
                                    dmc.MenuItem(
                                        "대화 초기화", 
                                        id="ai-clear-chat-btn", 
                                        leftSection=dbpc.Icon(icon="clean"),
                                    ),
                                    dmc.MenuItem(
                                        "모델 설정", 
                                        id="ai-model-settings-btn",
                                        leftSection=dbpc.Icon(icon="cog"),
                                    ),
                                ])
                            ]
                        )
                    ],
                    justify="flex-apart",
                    mb="md"
                ),
                
                # 대화 내역 표시 영역
                dmc.Paper(
                    children=[
                        html.Div(
                            id="ai-chat-history",
                            style={
                                "height": "calc(100vh - 250px)",
                                "overflowY": "auto",
                                "padding": "10px"
                            },
                            children=[]
                        )
                    ],
                    withBorder=True,
                    style={"marginBottom": "10px"}
                ),
                
                # 메시지 입력 영역
                dmc.Group(
                    [
                        dmc.TextInput(
                            id="ai-user-input",
                            placeholder="AI 어시스턴트에게 질문하세요...",
                            style={"flexGrow": 1},
                            rightSection=dbpc.Button(
                                id="ai-submit-btn",
                                icon="arrow-right",
                                minimal=True
                            )
                        )
                    ],
                    justify="center",
                    align="center",
                    style={"width": "100%"}
                ),
                
                # 데이터 변환 적용 모달
                dmc.Modal(
                    id="ai-result-detail-modal",
                    title="분석 결과 상세보기",
                    centered=True,
                    size="70%",
                    children=[
                        dmc.Tabs(
                            [
                                dmc.TabsList(
                                    [
                                        dmc.TabsTab("결과", value="result"),
                                        dmc.TabsTab("코드", value="code"),
                                    ]
                                ),
                                dmc.TabsPanel(
                                    children=[],
                                    id="ai-modal-result-content",
                                    value="result",
                                    p="md",
                                    style={"maxHeight": "60vh", "overflowY": "auto"}
                                ),
                                dmc.TabsPanel(
                                    children=[],
                                    id="ai-modal-code-content",
                                    value="code",
                                    p="md",
                                    style={"maxHeight": "60vh", "overflowY": "auto"}
                                ),
                            ],
                            value="result"
                        ),
                        dmc.Group(
                            [
                                dmc.Button(
                                    "이 변환 적용하기", 
                                    id="ai-apply-transformation-btn",
                                    leftSection=dbpc.Icon(icon="tick")
                                ),
                                dmc.Button(
                                    "닫기", 
                                    id="ai-close-modal-btn",
                                    color="gray",
                                    variant="outline"
                                )
                            ],
                            justify="right",
                            mt="md"
                        )
                    ]
                ),
                
                # 상태 저장용 컴포넌트
                dcc.Store(id="ai-current-conversation-id"),
                dcc.Store(id="ai-chat-state"),
                dcc.Store(id="ai-last-result"),
                dcc.Store(id="ai-last-code"),
            ],
            p="md",
            shadow="sm",
            radius="xs",
            withBorder=True,
        )
    
    def _create_user_message_ui(self, message):
        """사용자 메시지 UI 생성"""
        return dmc.Group(
            [
                dmc.Avatar(
                    color="blue",
                    radius="xl"
                ),
                dmc.Paper(
                    children=[
                        dmc.Text(message, size="sm")
                    ],
                    p="sm",
                    withBorder=True,
                    style={"maxWidth": "80%", "backgroundColor": "#f1f3f5", "borderRadius": "15px 15px 15px 0"}
                )
            ],
            justify="left",
            mb="md",
            align="flex-end"
        )
    
    def _create_ai_message_ui(self, message, result_type=None, result_id=None):
        """AI 메시지 UI 생성"""
        message_content = [dmc.Text(message, size="sm")]
        
        # 결과 유형에 따른 추가 컨텐츠 (데이터프레임 또는 차트)
        if result_type in ["dataframe", "chart"]:
            message_content.append(
                dmc.Button(
                    "결과 자세히 보기",
                    variant="subtle",
                    size="xs",
                    mt="xs",
                    id={"type": "ai-view-detail-btn", "index": result_id or 0},
                    leftSection=dbpc.Icon(icon="torch")
                )
            )
        
        return dmc.Group(
            [
                dmc.Paper(
                    children=message_content,
                    p="sm",
                    withBorder=True,
                    style={"maxWidth": "80%", "backgroundColor": "#e9f5ff", "borderRadius": "15px 15px 0 15px"}
                ),
                dmc.Avatar(
                    "AI",
                    color="indigo",
                    radius="xl",
                )
            ],
            justify="flex-end",
            mb="md",
        )

    def register_callbacks(self, app):
        # AI 어시스턴트 탭 열기 콜백
        @app.callback(
            Output("flex-layout", "model", allow_duplicate=True),
            Output("toaster", "toasts", allow_duplicate=True),
            Input("ai-assistant-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True
        )
        def handle_ai_assistant_button_click(n_clicks, current_model):
            if n_clicks is None:
                raise exceptions.PreventUpdate

            dff = displaying_df()
            if dff is None:
                return no_update, [dbpc.Toast(message=f"데이터가 로드되지 않았습니다", intent="warning", icon="warning-sign")]

            # 기존 탭 검색
            tab_search_result = find_tab_in_layout(current_model, "ai-assistant-tab")
            
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
                "name": "AI 어시스턴트",
                "component": "button",
                "enableClose": True,
                "id": "ai-assistant-tab"
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
            
        # 대화 초기화 콜백
        @app.callback(
            Output("ai-chat-history", "children"),
            Output("ai-chat-state", "data"),
            Output("ai-current-conversation-id", "data"),
            Input("ai-clear-chat-btn", "n_clicks"),
            prevent_initial_call=True
        )
        def clear_chat(n_clicks):
            # 새 대화 ID 생성
            new_conversation_id = str(uuid.uuid4())
            msg = "안녕하세요! 데이터 분석을 도와드릴 AI 어시스턴트입니다. 데이터에 대해 궁금한 점이 있으시면 물어보세요."
            # 웰컴 메시지 추가
            welcome_message = self._create_ai_message_ui(msg)
            
            # 초기 채팅 상태
            initial_state = {
                "messages": [{"role": "assistant", "content": msg}],
                "results": []
            }
            
            return [welcome_message], initial_state, new_conversation_id
        
        # 채팅 입력 및 응답 콜백
        @app.callback(
            Output("ai-chat-history", "children", allow_duplicate=True),
            Output("ai-user-input", "value"),
            Output("ai-chat-state", "data", allow_duplicate=True),
            Output("ai-last-result", "data"),
            Output("ai-last-code", "data"),
            Input("ai-submit-btn", "n_clicks"),
            Input("ai-user-input", "n_submit"),
            State("ai-user-input", "value"),
            State("ai-chat-history", "children"),
            State("ai-chat-state", "data"),
            prevent_initial_call=True
        )
        def process_user_input(n_clicks, n_submit, user_input, chat_history, chat_state):
            # 입력이 없는 경우 처리 안함
            if not user_input or (not n_clicks and not n_submit):
                raise exceptions.PreventUpdate
                
            # 현재 대화 기록이 없다면 초기화
            if not chat_state:
                chat_state = {
                    "messages": [
                        {"role": "assistant", "content": "안녕하세요! 데이터 분석을 도와드릴 AI 어시스턴트입니다. 데이터에 대해 궁금한 점이 있으시면 물어보세요."}
                    ],
                    "results": []
                }
            
            # 사용자 메시지 UI 추가
            user_message_ui = self._create_user_message_ui(user_input)
            updated_chat_history = chat_history + [user_message_ui] if chat_history else [user_message_ui]
            
            # 채팅 상태에 사용자 메시지 추가
            chat_state["messages"].append({"role": "user", "content": user_input})
            
            # 여기서 실제로는 PandasAI를 호출하여 응답을 받아야 하지만,
            # 지금은 간단한 더미 응답으로 대체
            
            # 더미 응답 생성
            result_id = str(uuid.uuid4())
            result_type = None
            dummy_response = ""
            
            # 특정 키워드에 따라 다른 응답 유형 반환
            if "평균" in user_input or "평균값" in user_input or "mean" in user_input.lower():
                dummy_response = "데이터의 평균값은 42.5입니다."
                result_type = "number"
            elif "그래프" in user_input or "차트" in user_input or "plot" in user_input.lower():
                dummy_response = "데이터를 그래프로 시각화했습니다. 자세히 보기를 클릭하면 전체 차트를 확인할 수 있습니다."
                result_type = "chart"
            elif "데이터" in user_input or "표" in user_input:
                dummy_response = "데이터프레임을 필터링했습니다. 자세히 보기를 클릭하면 결과를 확인할 수 있습니다."
                result_type = "dataframe"
            else:
                dummy_response = f"'{user_input}'에 대한 분석을 수행했습니다. 데이터에서 어떤 특정 정보를 찾고 계신가요?"
            
            # 더미 코드 생성
            dummy_code = """
            # 분석을 위한 샘플 코드
            import polars as pl
            
            # 데이터 필터링
            filtered_df = df.filter(pl.col("column_name") > 10)
            
            # 결과 계산
            result = filtered_df.select(pl.mean("value_column"))
            """
            
            # AI 응답 UI 생성
            ai_message_ui = self._create_ai_message_ui(dummy_response, result_type, result_id)
            updated_chat_history.append(ai_message_ui)
            
            # 채팅 상태에 AI 응답 추가
            chat_state["messages"].append({"role": "assistant", "content": dummy_response})
            
            # 결과 저장 (실제 구현에서는 PandasAI의 결과)
            dummy_result = {
                "id": result_id,
                "type": result_type,
                "content": dummy_response,
                "timestamp": datetime.now().isoformat()
            }
            
            chat_state["results"].append(dummy_result)
            
            return updated_chat_history, "", chat_state, dummy_result, dummy_code

        # # 결과 세부 보기 버튼 콜백
        # @app.callback(
        #     Output("ai-result-detail-modal", "opened"),
        #     Output("ai-modal-result-content", "children"),
        #     Output("ai-modal-code-content", "children"),
        #     Input({"type": "ai-view-detail-btn", "index": ALL}, "n_clicks"),
        #     State("ai-chat-state", "data"),
        #     State("ai-last-result", "data"),
        #     State("ai-last-code", "data"),
        #     prevent_initial_call=True
        # )
        # def open_result_detail(n_clicks, chat_state, last_result, last_code):
        #     # 클릭이 없으면 처리 안함
        #     if not n_clicks or all(n is None for n in n_clicks):
        #         raise exceptions.PreventUpdate
            
        #     # 결과 타입에 따른 UI 생성
        #     result_content = []
        #     if last_result["type"] == "dataframe":
        #         # 데이터프레임 표시 (더미 데이터)
        #         dummy_df = pl.DataFrame({
        #             "Column1": [1, 2, 3, 4, 5],
        #             "Column2": ["A", "B", "C", "D", "E"],
        #             "Column3": [10.5, 20.6, 30.7, 40.8, 50.9]
        #         })
                
        #         # Polars 데이터프레임을 HTML 표로 변환
        #         table_rows = []
        #         # 헤더 추가
        #         header_cells = [dmc.TableTh(col) for col in dummy_df.columns]
        #         table_rows.append(dmc.TableTr(header_cells))
                
        #         # 데이터 행 추가
        #         for row in dummy_df.rows():
        #             row_cells = [dmc.TableTd(str(cell)) for cell in row]
        #             table_rows.append(dmc.TableTr(row_cells))
                
        #         result_content = [
        #             dmc.Text("데이터프레임 결과:", weight=500, mb="md"),
        #             dmc.Table(
        #                 table_rows,
        #                 striped=True,
        #                 highlightOnHover=True,
        #                 withBorder=True,
        #                 withColumnBorders=True
        #             )
        #         ]
            
        #     elif last_result["type"] == "chart":
        #         # 차트 표시 (더미 이미지)
        #         result_content = [
        #             dmc.Text("차트 결과:", weight=500, mb="md"),
        #             dmc.Image(
        #                 src="https://via.placeholder.com/800x400?text=Sample+Chart",
        #                 alt="Sample Chart",
        #                 style={"maxWidth": "100%"}
        #             )
        #         ]
            
        #     else:
        #         # 일반 텍스트 결과
        #         result_content = [
        #             dmc.Text("분석 결과:", weight=500, mb="md"),
        #             dmc.Text(last_result["content"])
        #         ]
            
        #     # 코드 내용 표시
        #     code_content = [
        #         dmc.Text("생성된 코드:", weight=500, mb="md"),
        #         dmc.Prism(
        #             language="python",
        #             children=last_code,
        #             withLineNumbers=True,
        #             colorScheme="dark"
        #         )
        #     ]
            
        #     return True, result_content, code_content
        
        # # 모달 닫기 콜백
        # @app.callback(
        #     Output("ai-result-detail-modal", "opened", allow_duplicate=True),
        #     Input("ai-close-modal-btn", "n_clicks"),
        #     prevent_initial_call=True
        # )
        # def close_modal(n_clicks):
        #     return False
        
        # # 변환 적용 콜백
        # @app.callback(
        #     Output("aggrid-table", "columnDefs", allow_duplicate=True),
        #     Output("toaster", "toasts", allow_duplicate=True),
        #     Input("ai-apply-transformation-btn", "n_clicks"),
        #     State("ai-last-code", "data"),
        #     State("ai-result-detail-modal", "opened"),
        #     prevent_initial_call=True
        # )
        # def apply_transformation(n_clicks, code, modal_opened):
        #     if not n_clicks or not modal_opened:
        #         raise exceptions.PreventUpdate
            
        #     # 실제 구현에서는 여기서 코드를 실행하고 데이터프레임에 적용
        #     try:
        #         # 지금은 더미 메시지만 반환
        #         return no_update, [dbpc.Toast(
        #             message="변환이 성공적으로 적용되었습니다!",
        #             intent="success",
        #             icon="endorsed"
        #         )]
        #     except Exception as e:
        #         return no_update, [dbpc.Toast(
        #             message=f"변환 적용 중 오류가 발생했습니다: {str(e)}",
        #             intent="danger",
        #             icon="error"
        #         )]
        
        # # 채팅 초기화 콜백 (탭이 열릴 때 자동으로 호출)
        # app.clientside_callback(
        #     """
        #     function initializeChat(n_clicks) {
        #         if (n_clicks > 0) {
        #             return window.dash_clientside.no_update;
        #         }
        #         return window.dash_clientside.trigger_callback(
        #             "ai-clear-chat-btn.n_clicks",
        #             1
        #         );
        #     }
        #     """,
        #     Output("ai-clear-chat-btn", "n_clicks"),
        #     Input("ai-assistant-btn", "n_clicks"),
        #     prevent_initial_call=True
        # )