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
import os


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
        
        # LLM 및 Agent 객체 초기화 (실제 연결은 나중에)
        self.llm_model = None
        self.agent = None
        self.pandas_df = None  # Pandas DataFrame 저장 변수 추가
        self.session_id = None
        
        # 기능 플래그
        self.is_initialized = False
        self.is_session_active = False

    def button_layout(self):
        """LLM 분석 버튼 레이아웃"""
        return html.Div([dbpc.Button("AI Analysis", id="llm-btn", icon="lightbulb", minimal=True, outlined=True)])

    def tab_layout(self):
        """LLM 분석 탭 레이아웃"""
        return dmc.Paper(
            children=[
                # 상단 타이틀 및 설정 영역
                dmc.Group([
                    dbpc.EntityTitle(title="AI Data Analysis", heading="H5", icon="lightbulb"),
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
                            dbpc.Icon(icon="lightbulb", size=16),
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
                            "Explain",
                            id="llm-explain-btn",
                            icon="info-sign",
                            intent="primary",
                            minimal=True,
                            outlined=True,
                            small=True,
                            disabled=True
                        ),
                    ]),
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
                dcc.Store(id="llm-can-explain", data=False),
                dcc.Store(id="llm-initialize", data=None),
                
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
                                dmc.Text("• Use 'Explain' to get details on how results were calculated.", size="sm"),
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

    def initialize_system(self, model_name=None):
        """LLM 및 Agent 초기화 (메인 스레드에서 호출)"""
        try:
            # 모델 이름이 지정되지 않으면 현재 설정된 모델 사용
            model_name = model_name or self.default_model
            
            # LLM 모델 초기화
            logger.info(f"Initializing LLM model: {model_name}")
            from pandasai.llm.local_llm import LocalLLM
            self.llm_model = LocalLLM(
                api_base=self.api_base,
                model=model_name
            )
            logger.info("LLM model initialized successfully")
            
            # 필터링된 데이터프레임 가져오기
            df = displaying_df(filtred_apply=True)
            
            if df is None or df.is_empty():
                logger.warning("No data available for analysis")
                self.is_initialized = True
                self.is_session_active = False
                return False, "No data available for analysis"
            
            # Polars DataFrame을 Pandas DataFrame으로 변환 (메인 스레드에서)
            logger.info("Converting Polars DataFrame to Pandas DataFrame")
            self.pandas_df = df.to_pandas()
            
            # 세션 ID 생성
            self.session_id = str(uuid.uuid4())
            
            # Agent 생성 (메인 스레드에서)
            logger.info("Creating Agent with LLM model")
            from pandasai import Agent
            self.agent = Agent(
                [self.pandas_df], 
                config={"llm": self.llm_model},
                memory_size=10  # 대화 내역 유지 크기 
            )
            
            self.is_initialized = True
            self.is_session_active = True
            return True, "System initialized successfully"
            
        except Exception as e:
            logger.error(f"Failed to initialize system: {str(e)}")
            self.is_initialized = False
            self.is_session_active = False
            return False, str(e)

    def refresh_data(self):
        """데이터 갱신 (필요할 때 호출)"""
        try:
            # 현재 LLM이 초기화되어 있지 않으면 먼저 초기화
            if not self.is_initialized or self.llm_model is None:
                return False, "LLM not initialized"
                
            # 필터링된 데이터프레임 가져오기
            df = displaying_df(filtred_apply=True)
            
            if df is None or df.is_empty():
                return False, "No data available"
            
            # Polars DataFrame을 Pandas DataFrame으로 변환
            self.pandas_df = df.to_pandas()
            
            # 기존 Agent가 있으면 데이터만 업데이트
            if self.agent is not None:
                # 현재 Agent 인스턴스는 데이터 업데이트를 지원하지 않으므로
                # 새 Agent를 생성하고 기존 세션 ID 유지
                self.agent = Agent(
                    [self.pandas_df], 
                    config={"llm": self.llm_model},
                    memory_size=10
                )
                self.is_session_active = True
                return True, "Data refreshed successfully"
            else:
                # Agent가 없으면 새로 생성
                self.session_id = str(uuid.uuid4())
                self.agent = Agent(
                    [self.pandas_df], 
                    config={"llm": self.llm_model},
                    memory_size=10
                )
                self.is_session_active = True
                return True, "New agent created with refreshed data"
                
        except Exception as e:
            logger.error(f"Failed to refresh data: {str(e)}")
            return False, str(e)

    def _format_chat_message(self, role, content, timestamp=None, is_explain=False):
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
            # 설명 응답인 경우 특별한 배지 추가
            badge = None
            if is_explain:
                badge = dmc.Badge("EXPLANATION", color="cyan", size="sm", variant="outline", mb="xs")
            
            header_content = [
                dbpc.Icon(icon="lightbulb", size=16),
                dmc.Text(f"AI Assistant ({timestamp}):", size="xs", c="dimmed")
            ]
            
            return html.Div([
                dmc.Group(header_content, gap="xs"),
                dmc.Paper(
                    children=[
                        badge,
                        self._format_assistant_response(content)
                    ] if badge else self._format_assistant_response(content),
                    p="sm",
                    style={
                        "backgroundColor": "#f1f8e9" if not is_explain else "#e0f7fa", 
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
            Output("llm-initialize", "data"),
            Input("llm-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True
        )
        def handle_llm_button_click(n_clicks, current_model):
            """LLM 버튼 클릭 시 우측 패널에 탭 추가 및 LLM 초기화"""
            model_update, toaster_update = handle_tab_button_click(n_clicks, current_model, "llm-tab", "AI Analysis")
            
            # 탭이 추가되면 LLM 및 Agent 초기화 트리거
            # 실제 초기화는 다음 콜백에서 수행
            return model_update, toaster_update, n_clicks
            
        @app.callback(
            Output("llm-session-badge", "style"),
            Output("toaster", "toasts", allow_duplicate=True),
            Input("llm-initialize", "data"),
            State("llm-current-model", "data"),
            prevent_initial_call=True
        )
        def initialize_on_tab_open(trigger, current_model):
            """탭이 열릴 때 LLM 및 Agent 초기화"""
            if trigger is None:
                raise exceptions.PreventUpdate
                
            # LLM 및 Agent 초기화 (메인 스레드에서)
            success, message = self.initialize_system(current_model)
            
            if success:
                return {"display": "block"}, [
                    dbpc.Toast(
                        message="AI Analysis system initialized and ready",
                        intent="success",
                        icon="tick"
                    )
                ]
            else:
                return {"display": "none"}, [
                    dbpc.Toast(
                        message=f"System initialization warning: {message}",
                        intent="warning",
                        icon="warning-sign"
                    )
                ]

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
                # 새 모델로 시스템 초기화
                success, message = self.initialize_system(selected_model)
                model_label = next((m["label"] for m in self.available_models if m["value"] == selected_model), selected_model)
                
                # 세션 활성 상태 표시
                session_badge = dmc.Badge(
                    "Session Active", 
                    id="llm-session-badge",
                    color="blue",
                    variant="outline",
                    style={"display": "block" if success else "none"}
                )
                
                # 모델 정보 업데이트
                model_info = dmc.Group([
                    dbpc.Icon(icon="lightbulb", size=16),
                    dmc.Text(f"Using model: {model_label}", size="sm"),
                    session_badge
                ], gap="xs")
                
                if success:
                    return [
                        dbpc.Toast(
                            message=f"Model changed to {model_label}. Session has been reset.",
                            intent="success",
                            icon="tick"
                        )
                    ], model_info, selected_model
                else:
                    return [
                        dbpc.Toast(
                            message=f"Model changed but warning: {message}",
                            intent="warning",
                            icon="warning-sign"
                        )
                    ], model_info, selected_model
            
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
            Output("llm-session-badge", "style", allow_duplicate=True),
            Input("llm-test-connection-btn", "n_clicks"),
            State("llm-current-model", "data"),
            prevent_initial_call=True
        )
        def test_llm_connection(n_clicks, current_model):
            """LLM 연결 테스트"""
            if n_clicks:
                # 데이터 새로고침 및 연결 테스트
                success, message = self.refresh_data()
                
                if success:
                    return [
                        dbpc.Toast(
                            message=f"LLM connection successful! {message}",
                            intent="success",
                            icon="tick"
                        )
                    ], {"display": "block"}
                else:
                    return [
                        dbpc.Toast(
                            message=f"LLM connection warning: {message}",
                            intent="warning",
                            icon="warning-sign"
                        )
                    ], {"display": "none" if message == "LLM not initialized" else "block"}
            return no_update, no_update

        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("llm-chat-history-container", "children"),
            Output("llm-session-badge", "style", allow_duplicate=True),
            Output("llm-session-id", "data"),
            Output("llm-explain-btn", "disabled"),
            Output("llm-can-explain", "data"),
            Input("llm-reset-session-btn", "n_clicks"),
            State("llm-current-model", "data"),
            prevent_initial_call=True
        )
        def reset_session(n_clicks, current_model):
            """세션 초기화"""
            if n_clicks:
                # 세션 관련 변수 초기화하고 새로운 Agent 생성
                success, message = self.initialize_system(current_model)
                
                if success:
                    return [
                        dbpc.Toast(
                            message="Session reset. Starting a new conversation.",
                            intent="success",
                            icon="refresh"
                        )
                    ], [], {"display": "block"}, self.session_id, True, False
                else:
                    return [
                        dbpc.Toast(
                            message=f"Session reset warning: {message}",
                            intent="warning",
                            icon="warning-sign"
                        )
                    ], [], {"display": "none"}, None, True, False
            
            return no_update, no_update, no_update, no_update, no_update, no_update
        
        @app.callback(
            Output("llm-prompt-input", "value"),
            Output("llm-chat-history-container", "children", allow_duplicate=True),
            Output("llm-explain-btn", "disabled", allow_duplicate=True),
            Output("llm-can-explain", "data", allow_duplicate=True),
            Input("llm-clear-btn", "n_clicks"),
            prevent_initial_call=True
        )
        def clear_chat(n_clicks):
            """채팅 초기화"""
            if n_clicks:
                return "", [], True, False
            raise exceptions.PreventUpdate
        
        # 백그라운드 콜백으로 메인 AI 분석 실행
        @callback(
            output=[
                Output("llm-chat-history-container", "children", allow_duplicate=True),
                Output("llm-explain-btn", "disabled", allow_duplicate=True),
                Output("llm-can-explain", "data", allow_duplicate=True)
            ],
            inputs=Input("llm-generate-btn", "n_clicks"),
            state=[
                State("llm-prompt-input", "value"),
                State("llm-chat-history-container", "children"),
            ],
            background=True,
            running=[
                (Output("llm-generate-btn", "loading"), True, False),
                (Output("llm-cancel-btn", "disabled"), False, True),
            ],
            cancel=[Input("llm-cancel-btn", "n_clicks")],
            prevent_initial_call=True,
        )
        def generate_analysis(n_clicks, prompt, chat_history):
            """LLM 분석 생성 실행 (백그라운드)"""
            if not n_clicks or not prompt:
                return no_update, no_update, no_update
            
            # 현재 타임스탬프
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # 사용자 메시지 추가
            user_message = self._format_chat_message("user", prompt, current_time)
            updated_chat = chat_history + [user_message]
            
            try:
                # 시스템이 초기화되었는지 확인
                if not self.is_initialized or self.agent is None:
                    error_message = self._format_chat_message(
                        "assistant", 
                        "System not initialized. Please try resetting the session.", 
                        current_time
                    )
                    return updated_chat + [error_message], True, False
                
                # AI 응답 생성
                logger.info(f"Running analysis with prompt: {prompt}")
                result = self.agent.chat(prompt)
                logger.info(f"Analysis completed, result type: {type(result)}")
                
                # AI 응답 메시지 추가
                assistant_message = self._format_chat_message("assistant", result, current_time)
                final_chat = updated_chat + [assistant_message]

                # 결과 반환 (설명 버튼 활성화)
                return final_chat, False, True
                
            except Exception as e:
                logger.error(f"Analysis failed: {str(e)}")
                
                # 오류 메시지 추가
                error_message = self._format_chat_message(
                    "assistant", 
                    f"Error during analysis: {str(e)}", 
                    current_time
                )
                
                # 세션을 유지하도록 변경 (오류가 있어도 재설정 안 함)
                # 필요시 사용자가 Reset Session 버튼을 통해 직접 초기화 가능

                return updated_chat + [error_message], True, False
        
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
            
        # 설명 요청 처리
        @callback(
            output=Output("llm-chat-history-container", "children", allow_duplicate=True),
            inputs=Input("llm-explain-btn", "n_clicks"),
            state=[
                State("llm-chat-history-container", "children"),
                State("llm-can-explain", "data")
            ],
            background=True,
            running=[
                (Output("llm-explain-btn", "loading"), True, False),
                (Output("llm-cancel-btn", "disabled"), False, True),
            ],
            cancel=[Input("llm-cancel-btn", "n_clicks")],
            prevent_initial_call=True,
        )
        def explain_analysis(n_clicks, chat_history, can_explain):
            """분석 결과 설명 가져오기"""
            if not n_clicks or not can_explain or self.agent is None:
                return no_update
            
            # 현재 타임스탬프
            current_time = datetime.now().strftime("%H:%M:%S")
            
            try:
                # 설명 요청
                logger.info("Requesting explanation from Agent")
                explanation = self.agent.explain()
                logger.info("Explanation received")
                
                # 설명 메시지 추가
                explanation_message = self._format_chat_message(
                    "assistant", 
                    explanation, 
                    current_time,
                    is_explain=True
                )
                
                # 결과 반환
                return chat_history + [explanation_message]
                
            except Exception as e:
                logger.error(f"Explanation failed: {str(e)}")
                
                # 오류 메시지 추가
                error_message = self._format_chat_message(
                    "assistant", 
                    f"Failed to get explanation: {str(e)}", 
                    current_time
                )
                
                return chat_history + [error_message]