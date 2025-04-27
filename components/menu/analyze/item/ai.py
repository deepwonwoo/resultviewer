# components/menu/analyze/item/llm.py

import polars as pl
import pandas as pd
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, dcc, no_update, exceptions, ctx, callback, ALL
import dash_ag_grid as dag
import base64
import io
import matplotlib.pyplot as plt

# from pandasai import Agent
# from pandasai.llm.local_llm import LocalLLM

from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.menu.edit.utils import handle_tab_button_click


class LLMAnalysis:
    def __init__(self):
        # LLM 모델 설정 - 초기화는 실제 사용시에 함
        self.llm_model = None
        self.agent = None
        
        # LLM 연결 설정 (하드코딩)
        self.api_base = "http://localhost:11434/v1"
        self.model_name = "llama3"

    def button_layout(self):
        return dbpc.Button("AI Analysis", id="llm-btn", icon="lightbulb", minimal=True, outlined=True)

    def tab_layout(self):
        return dmc.Paper(
            children=[
                # 상단 타이틀 및 설정 영역
                dmc.Group([
                    dbpc.EntityTitle(title="AI Data Analysis", heading="H5", icon="lightbulb"),
                    dmc.Group([
                        dmc.Checkbox(
                            id="llm-use-filtered-data",
                            label="Use filtered data only",
                            size="sm",
                            checked=False
                        ),
                        dbpc.Button(
                            "Test Connection",
                            id="llm-test-connection-btn",
                            icon="link",
                            minimal=True,
                            small=True
                        )
                    ], gap="md")
                ], justify="space-between"),
                
                dmc.Space(h=20),
                
                # 프롬프트 입력 영역
                dmc.Textarea(
                    id="llm-prompt-input",
                    placeholder="Enter your question or analysis prompt here...",
                    style={"width": "100%"},
                    autosize=True,
                    minRows=3,
                    maxRows=10
                ),
                
                dmc.Space(h=10),
                
                # 생성 버튼 및 로딩 인디케이터
                dmc.Group([
                    dbpc.Button(
                        "Generate",
                        id="llm-generate-btn",
                        icon="play",
                        intent="primary",
                        loading=False
                    ),
                    dbpc.Button(
                        "Clear",
                        id="llm-clear-btn",
                        icon="trash",
                        minimal=True,
                        outlined=True
                    )
                ], justify="center"),
                
                dmc.Space(h=20),
                
                # 결과 표시 영역
                dmc.Paper(
                    children=[
                        dmc.Title("Analysis Result", order=5, mb="md"),
                        dmc.LoadingOverlay(  
                            id="llm-loading-overlay"
                        ),
                        html.Div(id="llm-result-container"),
                    ],
                    withBorder=True,
                    p="md",
                    style={"minHeight": "200px"}
                ),
                
                # 상태 저장용 스토어
                dcc.Store(id="llm-result-type"),
                dcc.Store(id="llm-result-data"),
                
                # 도움말 섹션
                dmc.Space(h=20),
                dmc.Accordion(
                    value="",
                    children=[
                        dmc.AccordionItem([
                            dmc.AccordionControl("Help"),
                            dmc.AccordionPanel([
                                dmc.Text("• AI will analyze the current dataframe based on your prompt.", size="sm"),
                                dmc.Text("• Check 'Use filtered data only' to analyze only the filtered data.", size="sm"),
                                dmc.Text("• Results can be text, tables, or charts.", size="sm"),
                                dmc.Text("• Use 'Test Connection' to verify LLM connectivity.", size="sm")
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

    def _initialize_llm(self):
        """LLM 모델 초기화"""
        try:
            if self.llm_model is None:
                # self.llm_model = LocalLLM(
                #     api_base=self.api_base,
                #     model=self.model_name
                # )
                logger.info("LLM model initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {str(e)}")
            return False

    def _create_agent(self, df):
        """PandasAI Agent 생성"""
        try:
            # Polars DataFrame을 Pandas DataFrame으로 변환
            pandas_df = df.to_pandas()
            # self.agent = Agent(pandas_df, config={"llm": self.llm_model})
            return True
        except Exception as e:
            logger.error(f"Failed to create agent: {str(e)}")
            return False

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
            Input("llm-test-connection-btn", "n_clicks"),
            prevent_initial_call=True
        )
        def test_llm_connection(n_clicks):
            """LLM 연결 테스트"""
            if n_clicks:
                if self._initialize_llm():
                    return [dbpc.Toast(
                        message="LLM connection successful!",
                        intent="success",
                        icon="tick"
                    )]
                else:
                    return [dbpc.Toast(
                        message="LLM connection failed. Please check your configuration.",
                        intent="danger",
                        icon="error"
                    )]
            return no_update

        @app.callback(
            Output("llm-result-container", "children"),
            Output("llm-generate-btn", "loading"),
            Output("llm-loading-overlay", "visible"),
            Output("toaster", "toasts", allow_duplicate=True),
            Input("llm-generate-btn", "n_clicks"),
            State("llm-prompt-input", "value"),
            State("llm-use-filtered-data", "checked"),
            prevent_initial_call=True
        )
        def generate_analysis(n_clicks, prompt, use_filtered):
            """LLM 분석 실행"""
            if not n_clicks or not prompt:
                raise exceptions.PreventUpdate
            
            # 로딩 시작
            loading_outputs = [None, True, True, no_update]
            
            try:
                # LLM 초기화
                if not self._initialize_llm():
                    return [
                        dmc.Alert(
                            "Failed to initialize LLM. Please check the connection.",
                            color="red",
                            withCloseButton=True
                        ),
                        False, False,
                        [dbpc.Toast(
                            message="LLM initialization failed",
                            intent="danger",
                            icon="error"
                        )]
                    ]
                
                # 데이터프레임 가져오기
                if use_filtered:
                    df = displaying_df(filtred_apply=True)
                else:
                    df = SSDF.dataframe
                
                if df is None or df.is_empty():
                    return [
                        dmc.Alert(
                            "No data available for analysis.",
                            color="yellow",
                            withCloseButton=True
                        ),
                        False, False,
                        [dbpc.Toast(
                            message="No data loaded",
                            intent="warning",
                            icon="warning-sign"
                        )]
                    ]
                
                # Agent 생성 및 분석 실행
                if not self._create_agent(df):
                    return [
                        dmc.Alert(
                            "Failed to create analysis agent.",
                            color="red",
                            withCloseButton=True
                        ),
                        False, False,
                        [dbpc.Toast(
                            message="Agent creation failed",
                            intent="danger",
                            icon="error"
                        )]
                    ]
                
                # 분석 실행
                result = self.agent.chat(prompt)
                
                # 결과 타입에 따른 처리
                if isinstance(result, pd.DataFrame):
                    # DataFrame 결과
                    return [
                        dag.AgGrid(
                            columnDefs=[
                                {"field": col, "sortable": True, "filter": True}
                                for col in result.columns
                            ],
                            rowData=result.to_dict("records"),
                            style={"height": "400px", "width": "100%"},
                            className="ag-theme-alpine",
                            defaultColDef={"resizable": True}
                        ),
                        False, False,
                        [dbpc.Toast(
                            message="Analysis completed successfully",
                            intent="success",
                            icon="tick"
                        )]
                    ]
                
                elif isinstance(result, (plt.Figure, type(plt))):
                    # Matplotlib plot 결과
                    try:
                        # 이미지를 메모리 버퍼에 저장
                        buf = io.BytesIO()
                        if isinstance(result, plt.Figure):
                            result.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                        else:
                            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                        buf.seek(0)
                        
                        # base64로 인코딩
                        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
                        plt.close('all')  # 메모리 정리
                        
                        return [
                            html.Img(
                                src=f"data:image/png;base64,{image_base64}",
                                style={"maxWidth": "100%", "height": "auto"}
                            ),
                            False, False,
                            [dbpc.Toast(
                                message="Chart generated successfully",
                                intent="success",
                                icon="tick"
                            )]
                        ]
                    except Exception as e:
                        logger.error(f"Failed to display plot: {str(e)}")
                        return [
                            dmc.Alert(
                                f"Failed to display chart: {str(e)}",
                                color="red",
                                withCloseButton=True
                            ),
                            False, False,
                            [dbpc.Toast(
                                message="Chart display failed",
                                intent="danger",
                                icon="error"
                            )]
                        ]
                
                elif isinstance(result, str) or result is None:
                    # 텍스트 결과
                    return [
                        dmc.Paper(
                            children=[
                                dmc.Text(str(result) if result else "No result returned.", size="md")
                            ],
                            p="md",
                            withBorder=True,
                            style={"backgroundColor": "#f8f9fa"}
                        ),
                        False, False,
                        [dbpc.Toast(
                            message="Analysis completed successfully",
                            intent="success",
                            icon="tick"
                        )]
                    ]
                
                else:
                    # 기타 결과 타입
                    return [
                        dmc.Paper(
                            children=[
                                dmc.Text(f"Result type: {type(result)}", weight=500),
                                dmc.Text(str(result), size="sm")
                            ],
                            p="md",
                            withBorder=True
                        ),
                        False, False,
                        [dbpc.Toast(
                            message="Analysis completed",
                            intent="success",
                            icon="tick"
                        )]
                    ]
                
            except Exception as e:
                logger.error(f"Analysis failed: {str(e)}")
                return [
                    dmc.Alert(
                        title="Analysis Error",
                        children=str(e),
                        color="red",
                        withCloseButton=True
                    ),
                    False, False,
                    [dbpc.Toast(
                        message=f"Analysis failed: {str(e)}",
                        intent="danger",
                        icon="error"
                    )]
                ]

        @app.callback(
            Output("llm-prompt-input", "value"),
            Output("llm-result-container", "children", allow_duplicate=True),
            Input("llm-clear-btn", "n_clicks"),
            prevent_initial_call=True
        )
        def clear_analysis(n_clicks):
            """분석 결과 및 입력 초기화"""
            if n_clicks:
                return "", html.Div()
            raise exceptions.PreventUpdate