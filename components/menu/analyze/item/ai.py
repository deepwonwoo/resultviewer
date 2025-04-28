import polars as pl
import pandas as pd
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, dcc, no_update, exceptions, ctx, callback, ALL, DiskcacheManager, background_callback
import dash_ag_grid as dag
import base64
import io
import matplotlib.pyplot as plt
from datetime import datetime
import uuid

# from pandasai import SmartDataframe
# from pandasai.llm.local_llm import LocalLLM
# from pandasai.helpers.chat_history import ChatHistory

from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.menu.edit.utils import handle_tab_button_click

class LLMAnalysis:
    def __init__(self):
        # LLM 모델 설정 정보
        self.api_base = "http://dre0bmg24004:8001/v1"
        self.available_models = [
            {"value": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B", "label": "DeepSeek Qwen-32B"},
            {"value": "meta-llama/Llama-2-70b-chat-hf", "label": "Llama-2-70b"},
            {"value": "mistralai/Mistral-7B-Instruct-v0.2", "label": "Mistral-7B"}
        ]
        self.default_model = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
        
        # LLM 및 SmartDataframe 객체 초기화 (실제 연결은 나중에)
        self.llm_model = None
        self.smart_df = None
        self.chat_history = None
        self.session_id = None
        
        # 기능 플래그
        self.is_initialized = False
        self.is_session_active = False


    def button_layout(self):
        """LLM 분석 버튼 레이아웃"""
        return dbpc.Button("AI Analysis", id="llm-btn", icon="robot", minimal=True, outlined=True)

    def tab_layout(self):
        """LLM 분석 탭 레이아웃"""
        return dmc.Paper(
            children=[
                # 상단 타이틀 및 설정 영역
                dmc.Group([
                    dbpc.EntityTitle(title="AI Data Analysis", heading="H5", icon="robot"),
                    dmc.Menu(
                        [
                            dmc.MenuTarget(dbpc.Button("Settings", icon="cog", minimal=True, small=True)),
                            dmc.MenuDropdown([
                                dmc.MenuItem("Test Connection", id="llm-test-connection-btn"),
                                dmc.MenuDivider(),
                                dmc.MenuItem("Reset Session", id="llm-reset-session-btn"),
                                dmc.MenuDivider(),
                                dmc.MenuLabel("Model Selection"),
                                *[dmc.MenuItem(
                                    model["label"], 
                                    id={"type": "llm-model-select", "model": model["value"]},
                                    rightSection=dmc.Text("✓", c="green") if model["value"] == self.default_model else None
                                ) for model in self.available_models]
                            ])
                        ],
                        trigger="hover",
                    )
                ], justify="space-between"),
                
                dmc.Space(h=10),
                
                # 모델 정보 표시
                html.Div(
                    id="llm-model-info",
                    children=[
                        dmc.Group([
                            dbpc.Icon(icon="robot", size=16),
                            dmc.Text(
                                f"Using model: {next((m['label'] for m in self.available_models if m['value'] == self.default_model), self.default_model)}",
                                size="sm"
                            ),
                            dmc.Badge(
                                "Session Active", 
                                id="llm-session-badge",
                                color="blue",
                                variant="outline",
                                style={"display": "none"}
                            )
                        ], gap="xs")
                    ],
                    style={"marginBottom": "15px"}
                ),
                
                # 채팅 인터페이스 영역
                dmc.Paper(
                    children=[
                        html.Div(
                            id="llm-chat-history-container",
                            children=[],
                            style={
                                "height": "300px", 
                                "overflowY": "auto", 
                                "padding": "10px",
                                "backgroundColor": "#f9f9f9",
                                "borderRadius": "5px"
                            }
                        )
                    ],
                    withBorder=True,
                    p="md",
                    mb="md"
                ),
                
                # 프롬프트 입력 영역
                dmc.Group([
                    dmc.TextInput(
                        id="llm-prompt-input",
                        placeholder="Ask anything about your data...",
                        radius="md",
                        size="md",
                        style={"width": "100%"},
                        rightSection=dbpc.Button(
                            id="llm-generate-btn",
                            icon="send-message",
                            intent="primary",
                            minimal=False,
                            small=False,
                        ),
                    ),
                ], grow=True, align="center", style={"marginBottom": "8px"}),
                
                # 버튼 그룹
                dmc.Group([
                    dbpc.Button(
                        "Clear Chat",
                        id="llm-clear-btn",
                        icon="trash",
                        minimal=True,
                        outlined=True,
                        small=True
                    ),
                    dbpc.Button(
                        "Cancel Request",
                        id="llm-cancel-btn",
                        icon="delete",
                        intent="danger",
                        minimal=True,
                        small=True,
                        disabled=True
                    )
                ], justify="space-between", mt="xs"),
                
                # 상태 및 히든 데이터 저장용 스토어
                dcc.Store(id="llm-session-id", data=None),
                dcc.Store(id="llm-current-model", data=self.default_model),
                
                # 도움말 섹션
                dmc.Space(h=20),
                dmc.Accordion(
                    value="",
                    children=[
                        dmc.AccordionItem([
                            dmc.AccordionControl("Help & Tips"),
                            dmc.AccordionPanel([
                                dmc.Text("• AI will analyze filtered data from your current view.", w=500, mb="xs"),
                                dmc.Text("• Ask questions about your data, request visualizations, or get statistics.", size="sm"),
                                dmc.Text("• Your conversation history is maintained within a session.", size="sm"),
                                dmc.Text("• You can change the AI model from the settings menu.", size="sm"),
                                dmc.Text("• Use 'Reset Session' to start a fresh conversation.", size="sm"),
                                dmc.Text("• Long-running queries can be cancelled with the cancel button.", size="sm")
                            ])
                        ], value="help")
                    ]
                )
            ],
            p="md",
            shadow="sm",
            radius="xs",
            withBorder=True
        )

    def _initialize_llm(self, model_name=None):
        """LLM 모델 초기화"""
        try:
            # 모델 이름이 지정되지 않으면 현재 설정된 모델 사용
            model_name = model_name or self.default_model
            
            logger.info(f"Initializing LLM model: {model_name}")
            # self.llm_model = LocalLLM(
            #     api_base=self.api_base,
            #     model=model_name
            # )
            logger.info("LLM model initialized successfully")
            self.is_initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {str(e)}")
            self.is_initialized = False
            return False

    def _create_smart_dataframe(self, df, session_id=None):
        """SmartDataframe 생성"""
        try:
            # Polars DataFrame을 Pandas DataFrame으로 변환
            logger.info("Converting Polars DataFrame to Pandas DataFrame")
            pandas_df = df.to_pandas()
            
            # 세션 설정
            if session_id:
                self.session_id = session_id
            else:
                self.session_id = str(uuid.uuid4())
            
            # # 새로운 채팅 히스토리 생성
            # self.chat_history = ChatHistory(session_id=self.session_id)
            
            # # SmartDataframe 생성
            # logger.info("Creating SmartDataframe with LLM model")
            # self.smart_df = SmartDataframe(
            #     pandas_df, 
            #     config={
            #         "llm": self.llm_model,
            #         "save_chat_history": True,
            #         "chat_history": self.chat_history,
            #         "verbose": True
            #     }
            # )

            self.is_session_active = True
            return True
        except Exception as e:
            logger.error(f"Failed to create SmartDataframe: {str(e)}")
            self.is_session_active = False
            return False


    def _format_chat_message(self, role, content, timestamp=None):
        """채팅 메시지 포맷 생성"""
        timestamp = timestamp or datetime.now().strftime("%H:%M:%S")
        
        if role == "user":
            return html.Div([
                dmc.Group([
                    dbpc.Icon(icon="user", size=16),
                    dmc.Text(f"You ({timestamp}):", size="xs", c="dimmed")
                ], gap="xs"),
                dmc.Paper(
                    children=dmc.Text(content),
                    p="sm",
                    style={
                        "backgroundColor": "#e3f2fd", 
                        "borderRadius": "5px",
                        "maxWidth": "80%",
                        "marginLeft": "auto"
                    }
                )
            ], style={"marginBottom": "15px", "textAlign": "right"})
        else:  # assistant
            return html.Div([
                dmc.Group([
                    dbpc.Icon(icon="robot", size=16),
                    dmc.Text(f"AI Assistant ({timestamp}):", size="xs", c="dimmed")
                ], gap="xs"),
                dmc.Paper(
                    children=self._format_assistant_response(content),
                    p="sm",
                    style={
                        "backgroundColor": "#f1f8e9", 
                        "borderRadius": "5px",
                        "maxWidth": "80%"
                    }
                )
            ], style={"marginBottom": "15px"})
    
    def _format_assistant_response(self, content):
        """AI 응답 내용 포맷팅 (타입에 따라 다르게 표시)"""
        if isinstance(content, pd.DataFrame):
            # DataFrame 응답
            return html.Div([
                dmc.Text("DataFrame Result:", w=500, mb="xs", size="sm"),
                dag.AgGrid(
                    columnDefs=[
                        {"field": col, "sortable": True, "filter": True}
                        for col in content.columns
                    ],
                    rowData=content.to_dict("records"),
                    style={"height": "250px", "width": "100%"},
                    className="ag-theme-alpine",
                    defaultColDef={"resizable": True, "filter": True}
                )
            ])
        
        elif isinstance(content, (plt.Figure, type(plt))):
            # Matplotlib plot 응답
            try:
                # 이미지를 메모리 버퍼에 저장
                buf = io.BytesIO()
                if isinstance(content, plt.Figure):
                    content.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                else:
                    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                buf.seek(0)
                
                # base64로 인코딩
                image_base64 = base64.b64encode(buf.read()).decode('utf-8')
                plt.close('all')  # 메모리 정리
                
                return html.Div([
                    dmc.Text("Chart Result:", weight=500, mb="xs", size="sm"),
                    html.Img(
                        src=f"data:image/png;base64,{image_base64}",
                        style={"maxWidth": "100%", "height": "auto"}
                    )
                ])
            except Exception as e:
                logger.error(f"Failed to display plot: {str(e)}")
                return dmc.Text(f"Failed to display chart: {str(e)}")
        
        else:
            # 텍스트 응답 (기본)
            return dmc.Text(str(content) if content else "No result returned.")


    def register_callbacks(self, app):
        """콜백 함수 등록"""
        
        @app.callback(
            Output("flex-layout", "model", allow_duplicate=True),
            Output("toaster", "toasts", allow_duplicate=True),
            Input("llm-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True
        )
        def handle_llm_button_click(n_clicks, current_model):
            """LLM 버튼 클릭 시 우측 패널에 탭 추가"""
            return handle_tab_button_click(n_clicks, current_model, "llm-tab", "AI Analysis")

        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("llm-model-info", "children"),
            Output("llm-current-model", "data"),
            Input({"type": "llm-model-select", "model": ALL}, "n_clicks"),
            State("llm-current-model", "data"),
            prevent_initial_call=True
        )
        def change_llm_model(n_clicks_list, current_model):
            """모델 변경"""
            # 클릭된 모델 확인
            if not any(n_clicks_list) or ctx.triggered_id is None:
                raise exceptions.PreventUpdate
            
            selected_model = ctx.triggered_id["model"]
            
            # 이미 선택된 모델이면 아무것도 하지 않음
            if selected_model == current_model:
                raise exceptions.PreventUpdate
            
            # 모델 변경 시도
            try:
                # 새 모델 초기화
                if self._initialize_llm(selected_model):
                    model_label = next((m["label"] for m in self.available_models if m["value"] == selected_model), selected_model)
                    
                    # 세션 활성 상태 표시
                    session_badge = dmc.Badge(
                        "Session Active", 
                        id="llm-session-badge",
                        color="blue",
                        variant="outline",
                        style={"display": "inline-block" if self.is_session_active else "none"}
                    )
                    
                    # 모델 정보 업데이트
                    model_info = dmc.Group([
                        dbpc.Icon(icon="robot", size=16),
                        dmc.Text(f"Using model: {model_label}", size="sm"),
                        session_badge
                    ], gap="xs")
                    
                    return [
                        dbpc.Toast(
                            message=f"Model changed to {model_label}",
                            intent="success",
                            icon="tick"
                        )
                    ], model_info, selected_model
                else:
                    return [
                        dbpc.Toast(
                            message=f"Failed to initialize model: {selected_model}",
                            intent="danger",
                            icon="error"
                        )
                    ], no_update, current_model
            
            except Exception as e:
                logger.error(f"Error changing model: {str(e)}")
                return [
                    dbpc.Toast(
                        message=f"Error changing model: {str(e)}",
                        intent="danger",
                        icon="error"
                    )
                ], no_update, current_model

        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("llm-session-badge", "style"),
            Input("llm-test-connection-btn", "n_clicks"),
            State("llm-current-model", "data"),
            prevent_initial_call=True
        )
        def test_llm_connection(n_clicks, current_model):
            """LLM 연결 테스트"""
            if n_clicks:
                if self._initialize_llm(current_model):
                    return [
                        dbpc.Toast(
                            message=f"LLM connection successful!",
                            intent="success",
                            icon="tick"
                        )
                    ], {"display": "none"}
                else:
                    return [
                        dbpc.Toast(
                            message="LLM connection failed. Please check your configuration.",
                            intent="danger",
                            icon="error"
                        )
                    ], {"display": "none"}
            return no_update, no_update

        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("llm-chat-history-container", "children"),
            Output("llm-session-badge", "style", allow_duplicate=True),
            Output("llm-session-id", "data"),
            Input("llm-reset-session-btn", "n_clicks"),
            prevent_initial_call=True
        )
        def reset_session(n_clicks):
            """세션 초기화"""
            if n_clicks:
                # 세션 관련 변수 초기화
                self.smart_df = None
                self.chat_history = None
                self.is_session_active = False
                new_session_id = str(uuid.uuid4())
                
                return [
                    dbpc.Toast(
                        message="Session reset. Starting a new conversation.",
                        intent="info",
                        icon="refresh"
                    )
                ], [], {"display": "none"}, new_session_id
            
            return no_update, no_update, no_update, no_update
        
        @app.callback(
            Output("llm-prompt-input", "value"),
            Output("llm-chat-history-container", "children", allow_duplicate=True),
            Input("llm-clear-btn", "n_clicks"),
            prevent_initial_call=True
        )
        def clear_chat(n_clicks):
            """채팅 초기화"""
            if n_clicks:
                return "", []
            raise exceptions.PreventUpdate
        
        # 백그라운드 콜백으로 메인 AI 분석 실행 - 올바른 문법 사용
        @callback(
            output=Output("llm-chat-history-container", "children", allow_duplicate=True),
            inputs=Input("llm-generate-btn", "n_clicks"),
            state=[
                State("llm-prompt-input", "value"),
                State("llm-chat-history-container", "children"),
                State("llm-session-id", "data"),
                State("llm-current-model", "data")
            ],
            background=True,
            running=[
                (Output("llm-generate-btn", "disabled"), True, False),
                (Output("llm-cancel-btn", "disabled"), False, True),
                (Output("llm-session-badge", "style"), {"display": "none"}, 
                 {"display": "inline-block" if self.is_session_active else "none"})
            ],
            cancel=[Input("llm-cancel-btn", "n_clicks")],
            prevent_initial_call=True,
        )
        def generate_analysis(n_clicks, prompt, chat_history, session_id, current_model):
            """LLM 분석 생성 실행 (백그라운드)"""
            if not n_clicks or not prompt:
                return no_update
            
            # 현재 타임스탬프
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # 사용자 메시지 추가
            user_message = self._format_chat_message("user", prompt, current_time)
            updated_chat = chat_history + [user_message]
            
            try:
                # LLM 초기화
                if not self.is_initialized or self.llm_model is None:
                    if not self._initialize_llm(current_model):
                        error_message = self._format_chat_message(
                            "assistant", 
                            "Failed to initialize LLM. Please check the connection.", 
                            current_time
                        )
                        return updated_chat + [error_message]
                
                # 필터링된 데이터프레임 가져오기
                df = displaying_df(filtred_apply=True)
                
                if df is None or df.is_empty():
                    error_message = self._format_chat_message(
                        "assistant", 
                        "No data available for analysis. Please load or filter data first.", 
                        current_time
                    )
                    return updated_chat + [error_message]
                
                # SmartDataframe 생성 또는 재사용
                if not self.is_session_active or self.smart_df is None:
                    if not self._create_smart_dataframe(df, session_id):
                        error_message = self._format_chat_message(
                            "assistant", 
                            "Failed to create SmartDataframe for analysis.", 
                            current_time
                        )
                        return updated_chat + [error_message]
                
                # AI 응답 생성
                logger.info(f"Running analysis with prompt: {prompt}")
                # result = self.smart_df.chat(prompt)
                import time
                time.sleep(2)
                result="test"
                logger.info(f"Analysis completed, result type: {type(result)}")
                
                # AI 응답 메시지 추가
                assistant_message = self._format_chat_message("assistant", result, current_time)
                final_chat = updated_chat + [assistant_message]
                
                # # 비동기 작업 완료 표시
                # app.clientside_callback(
                #     """
                #     function update_badge() {
                #         return {"display": "inline-block"};
                #     }
                #     """,
                #     Output("llm-session-badge", "style", allow_duplicate=True),
                #     Input("llm-chat-history-container", "children"),
                #     prevent_initial_call=True,
                # )
                
                # # 성공 토스트 표시
                # app.clientside_callback(
                #     """
                #     function show_success_toast() {
                #         return [{
                #             message: "Analysis completed successfully",
                #             intent: "success",
                #             icon: "tick"
                #         }];
                #     }
                #     """,
                #     Output("toaster", "toasts", allow_duplicate=True),
                #     Input("llm-chat-history-container", "children"),
                #     prevent_initial_call=True,
                # )
                
                # 결과 반환
                return final_chat
                
            except Exception as e:
                logger.error(f"Analysis failed: {str(e)}")
                
                # 오류 메시지 추가
                error_message = self._format_chat_message(
                    "assistant", 
                    f"Error during analysis: {str(e)}", 
                    current_time
                )
                
                # 세션이 끊어진 경우 초기화
                self.is_session_active = False
                self.smart_df = None
                
                # # 에러 상태 표시
                # app.clientside_callback(
                #     """
                #     function show_error_toast(error) {
                #         return [{
                #             message: "Analysis failed: " + error,
                #             intent: "danger",
                #             icon: "error"
                #         }];
                #     }
                #     """,
                #     Output("toaster", "toasts", allow_duplicate=True),
                #     Input("llm-chat-history-container", "children"),
                #     State("llm-chat-history-container", "children"),
                #     prevent_initial_call=True,
                # )
                
                return updated_chat + [error_message]
        
        # 입력 후 입력창 초기화
        @app.callback(
            Output("llm-prompt-input", "value", allow_duplicate=True),
            Input("llm-generate-btn", "n_clicks"),
            State("llm-prompt-input", "value"),
            prevent_initial_call=True
        )
        def clear_input_after_submit(n_clicks, current_value):
            """프롬프트 제출 후 입력창 초기화"""
            if n_clicks and current_value:
                return ""
            raise exceptions.PreventUpdate

