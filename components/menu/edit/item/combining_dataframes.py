import os
import time
import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, no_update, callback, exceptions, ctx, dcc

from utils.data_processing import displaying_df, file2df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions
from components.menu.edit.utils import find_tab_in_layout, handle_tab_button_click

class CombiningDataframes:
    
    def __init__(self):
        self.join_types = [
            {"value": "inner", "label": "Inner Join (교집합)"},
            {"value": "left", "label": "Left Join (왼쪽 데이터 유지)"},
            {"value": "right", "label": "Right Join (오른쪽 데이터 유지)"},
            {"value": "outer", "label": "Outer Join (합집합)"},
            {"value": "cross", "label": "Cross Join (카테시안 곱)"}
        ]
        self.system_columns = ['uniqid', 'group', 'childCount']
        self.default_current_suffix = "_current"
        self.default_new_suffix = "_new"


    def button_layout(self):
        return dbpc.Button(
            "Combine Dataframes", 
            id="combine-dataframes-btn", 
            icon="git-merge", 
            minimal=True, 
            outlined=True
        )

    def tab_layout(self):
        return dmc.Paper(
            children=[
                dmc.Group([
                    dbpc.EntityTitle(
                        title="Combine Dataframes", 
                        heading="H5", 
                        icon="git-merge"
                    )
                ], grow=True),
                dmc.Space(h=10),
                
                # 모드 선택 탭
                dmc.Tabs(
                    id="combine-mode-tabs",
                    value="merge",
                    children=[
                        dmc.TabsList([
                            dmc.TabsTab("Merge (Join)", value="merge", leftSection=dbpc.Icon(icon="git-merge")),
                            dmc.TabsTab("Concatenate", value="concat", leftSection=dbpc.Icon(icon="arrow-down"))
                        ]),
                        
                        # 머지(조인) 모드 패널
                        dmc.TabsPanel(
                            value="merge",
                            children=[
                                dmc.Space(h=15),
                                dmc.Text("현재 데이터프레임과 새 데이터를 JOIN합니다.", size="sm", c="dimmed", mb=10),
                                
                                # 파일 선택
                                dmc.TextInput(
                                    id="combine-merge-file-input",
                                    label="Join할 파일 경로",
                                    description="JOIN할 파일 경로를 입력하세요 (CSV, Parquet)",
                                    placeholder="파일 경로 입력...",
                                    leftSection=dbpc.Button(
                                        id="combine-merge-file-browse",
                                        icon="search",
                                        minimal=True,
                                        n_clicks=0
                                    ),
                                    rightSection=dbpc.Button(
                                        id="combine-merge-file-load",
                                        children="Load",
                                        minimal=True,
                                        small=True,
                                        n_clicks=0
                                    ),
                                ),
                                
                                # 파일 로드 후 표시될 영역
                                html.Div(
                                    id="combine-merge-file-info",
                                    style={"display": "none"},
                                    children=[
                                        dmc.Alert(
                                            "파일이 로드되었습니다.",
                                            color="green",
                                            variant="light",
                                            mb=10
                                        ),
                                        dmc.Text(id="combine-merge-file-stats", size="sm", mb=10),
                                    ]
                                ),
                                
                                dmc.Space(h=15),
                                
                                # JOIN 설정
                                dmc.Select(
                                    id="combine-merge-type",
                                    label="JOIN 유형",
                                    description="어떤 방식으로 데이터를 결합할지 선택하세요",
                                    data=self.join_types,
                                    value="inner",
                                    mb=10
                                ),
                                
                                dmc.Text("JOIN 키 선택", w=500, mb=5),
                                dmc.Text("현재 데이터프레임과 새 데이터프레임을 연결할 키 열을 선택하세요", size="sm", c="dimmed", mb=10),
                                
                                dmc.Group([
                                    dmc.Select(
                                        id="combine-merge-left-key",
                                        label="현재 데이터 키 컬럼",
                                        description="현재 데이터프레임의 키 컬럼",
                                        data=[],
                                        searchable=True,
                                        style={"width": "48%"}
                                    ),
                                    dmc.Select(
                                        id="combine-merge-right-key",
                                        label="새 데이터 키 컬럼",
                                        description="새 데이터프레임의 키 컬럼",
                                        data=[],
                                        searchable=True,
                                        style={"width": "48%"}
                                    )
                                ], grow=True, mb=15),

                                dmc.Group([
                                    dmc.TextInput(
                                        id="combine-merge-left-suffix",
                                        label="현재 데이터 중복 컬럼 서픽스",
                                        description="현재 로드된 데이터의 중복 컬럼에 추가될 서픽스",
                                        placeholder="_current",
                                        value="_current",
                                        style={"width": "48%"}
                                    ),
                                    dmc.TextInput(
                                        id="combine-merge-right-suffix",
                                        label="새 데이터 중복 컬럼 서픽스",
                                        description="새로 로드한 데이터의 중복 컬럼에 추가될 서픽스",
                                        placeholder="_new",
                                        value="_new",
                                        style={"width": "48%"}
                                    )
                                ], grow=True, mb=15),

                                # 설명 추가
                                dmc.Text(
                                    "* 동일한 컬럼명이 양쪽 데이터에 있을 경우에만 서픽스가 적용됩니다.",
                                    size="sm",
                                    c="dimmed",
                                    style={"fontStyle": "italic"},
                                    mb=10
                                ),

                                # 미리보기 섹션
                                dmc.Button(
                                    "미리보기",
                                    id="combine-merge-preview-btn",
                                    leftSection=dbpc.Icon(icon="eye-open"),
                                    variant="outline",
                                    mb=10
                                ),
                                
                                html.Div(
                                    id="combine-merge-preview-container",
                                    style={"display": "none"},
                                    children=[
                                        dmc.Paper(
                                            children=[
                                                dmc.Text("미리보기 (최대 5행)", w=500, mb=5),
                                                html.Div(id="combine-merge-preview-content")
                                            ],
                                            p="sm",
                                            withBorder=True,
                                            style={"maxHeight": "200px", "overflow": "auto"}
                                        )
                                    ]
                                ),
                                
                                dmc.Space(h=15),
                                
                                # 실행 버튼
                                dmc.Button(
                                    "실행",
                                    id="combine-merge-apply-btn",
                                    leftSection=dbpc.Icon(icon="tick"),
                                    variant="filled",
                                    color="blue",
                                    fullWidth=True
                                )
                            ]
                        ),
                        
                        # 연결(concatenate) 모드 패널
                        dmc.TabsPanel(
                            value="concat",
                            children=[
                                dmc.Space(h=15),
                                dmc.Text("현재 데이터프레임에 새 데이터를 행 방향으로 추가합니다.", size="sm", c="dimmed", mb=10),
                                
                                # 파일 선택
                                dmc.TextInput(
                                    id="combine-concat-file-input",
                                    label="연결할 파일 경로",
                                    description="행으로 추가할 파일 경로를 입력하세요 (CSV, Parquet)",
                                    placeholder="파일 경로 입력...",
                                    leftSection=dbpc.Button(
                                        id="combine-concat-file-browse",
                                        icon="search",
                                        minimal=True,
                                        n_clicks=0
                                    ),
                                    rightSection=dbpc.Button(
                                        id="combine-concat-file-load",
                                        children="Load",
                                        minimal=True,
                                        small=True,
                                        n_clicks=0
                                    ),
                                ),
                                
                                # 파일 로드 후 표시될 영역
                                html.Div(
                                    id="combine-concat-file-info",
                                    style={"display": "none"},
                                    children=[
                                        dmc.Alert(
                                            "파일이 로드되었습니다.",
                                            color="green",
                                            variant="light",
                                            mb=10
                                        ),
                                        dmc.Text(id="combine-concat-file-stats", size="sm", mb=10),
                                    ]
                                ),
                                
                                dmc.Space(h=15),
                                
                                # 연결 옵션들
                                dmc.Checkbox(
                                    id="combine-concat-reset-index",
                                    label="인덱스 리셋",
                                    description="연결 후 인덱스를 처음부터 다시 부여합니다",
                                    checked=True,
                                    mb=10
                                ),
                                
                                dmc.Checkbox(
                                    id="combine-concat-add-source",
                                    label="소스 표시 컬럼 추가",
                                    description="각 행이 어느 데이터프레임에서 왔는지 표시하는 컬럼을 추가합니다",
                                    checked=True,
                                    mb=10
                                ),
                                
                                dmc.TextInput(
                                    id="combine-concat-source-col",
                                    label="소스 컬럼명",
                                    description="소스를 표시할 컬럼의 이름",
                                    placeholder="data_source",
                                    value="data_source",
                                    mb=15
                                ),
                                
                                # 미리보기 섹션
                                dmc.Button(
                                    "미리보기",
                                    id="combine-concat-preview-btn",
                                    leftSection=dbpc.Icon(icon="eye-open"),
                                    variant="outline",
                                    mb=10
                                ),
                                
                                html.Div(
                                    id="combine-concat-preview-container",
                                    style={"display": "none"},
                                    children=[
                                        dmc.Paper(
                                            children=[
                                                dmc.Text("미리보기 (최대 5행)", w=500, mb=5),
                                                html.Div(id="combine-concat-preview-content")
                                            ],
                                            p="sm",
                                            withBorder=True,
                                            style={"maxHeight": "200px", "overflow": "auto"}
                                        )
                                    ]
                                ),
                                
                                dmc.Space(h=15),
                                
                                # 실행 버튼
                                dmc.Button(
                                    "실행",
                                    id="combine-concat-apply-btn",
                                    leftSection=dbpc.Icon(icon="tick"),
                                    variant="filled",
                                    color="blue",
                                    fullWidth=True
                                )
                            ]
                        )
                    ]
                ),
                
                # 도움말 섹션
                dmc.Space(h=20),
                dmc.Accordion(
                    value="",
                    children=[
                        dmc.AccordionItem(
                            [
                                dmc.AccordionControl("도움말"),
                                dmc.AccordionPanel([
                                    dmc.Text("1. Merge (Join): 공통 키를 기준으로 두 데이터프레임을 수평으로 결합합니다."),
                                    dmc.Text("   - Inner Join: 양쪽 데이터에 모두 있는 키만 유지"),
                                    dmc.Text("   - Left Join: 현재 데이터의 모든 행 유지"),
                                    dmc.Text("   - Right Join: 새 데이터의 모든 행 유지"),
                                    dmc.Text("   - Outer Join: 모든 키 유지 (합집합)"),
                                    dmc.Space(h=5),
                                    dmc.Text("2. 중복 컬럼 처리: 양쪽 데이터에 동일한 이름의 컬럼이 있을 경우"),
                                    dmc.Text("   - 현재 데이터의 컬럼에는 '_current' 서픽스 추가"),
                                    dmc.Text("   - 새 데이터의 컬럼에는 '_new' 서픽스 추가"),
                                    dmc.Space(h=5),
                                    dmc.Text("3. Concatenate: 두 데이터프레임을 수직으로 쌓아 결합합니다."),
                                    dmc.Text("   - 인덱스 리셋: 결합 후 인덱스를 처음부터 다시 부여"),
                                    dmc.Text("   - 소스 표시: 각 행이 어떤 데이터프레임에서 온 것인지 구분하는 컬럼 추가")
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
    
    def _remove_system_columns(self, df):
            """시스템 컬럼 제거 유틸리티 함수"""
            return df.drop([col for col in self.system_columns if col in df.columns], errors='ignore')

    def _prepare_join_dataframes(self, df1, df2):
        """Join을 위한 데이터프레임 준비"""
        # uniqid 백업 및 제거
        if 'uniqid' in df1.columns:
            df1_uniqid = df1['uniqid']
            df1 = df1.drop('uniqid')
        else:
            df1_uniqid = None
            
        if 'uniqid' in df2.columns:
            df2 = df2.drop('uniqid')
            
        return df1, df2, df1_uniqid
    
    def _restore_uniqid(self, df, uniqid_column=None):
        """Join 후 uniqid 복원 또는 재생성"""
        if uniqid_column is not None and len(uniqid_column) == df.height:
            # 원본 uniqid 복원 가능한 경우
            return df.with_columns(uniqid_column.alias('uniqid'))
        else:
            # 새로운 uniqid 생성
            return df.with_row_index('uniqid')



    def register_callbacks(self, app):
        """콜백 함수들 등록"""
        
        @app.callback(
            Output("flex-layout", "model", allow_duplicate=True),
            Output("toaster", "toasts", allow_duplicate=True),
            Input("combine-dataframes-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True
        )
        def handle_combine_dataframes_button_click(n_clicks, current_model):
            """Combine Dataframes 버튼 클릭 시 우측 패널에 탭 추가"""
            return handle_tab_button_click(n_clicks, current_model, "combine-dataframes-tab", "Combine Dataframes")
            
        # Merge 모드 파일 브라우저 콜백
        @app.callback(
            Output("combine-merge-file-input", "value"),
            Input("combine-merge-file-browse", "n_clicks"),
            prevent_initial_call=True
        )
        def browse_merge_file(n_clicks):
            """파일 선택 다이얼로그 열기 (Merge 모드)"""
            if n_clicks is None or n_clicks == 0:
                raise exceptions.PreventUpdate
                
            try:
                import subprocess
                from utils.config import CONFIG
                
                cmd = f"{CONFIG.SCRIPT}/QFileDialog/file_dialog"
                result = subprocess.run([cmd], capture_output=True, text=True, env=CONFIG.get_QtFileDialog_env())
                file_path = result.stdout.strip()
                
                return file_path if file_path else no_update
            except Exception as e:
                logger.error(f"파일 브라우저 오류 (Merge): {str(e)}")
                return no_update
                
        # Concat 모드 파일 브라우저 콜백
        @app.callback(
            Output("combine-concat-file-input", "value"),
            Input("combine-concat-file-browse", "n_clicks"),
            prevent_initial_call=True
        )
        def browse_concat_file(n_clicks):
            """파일 선택 다이얼로그 열기 (Concat 모드)"""
            if n_clicks is None or n_clicks == 0:
                raise exceptions.PreventUpdate
                
            try:
                import subprocess
                from utils.config import CONFIG
                
                cmd = f"{CONFIG.SCRIPT}/QFileDialog/file_dialog"
                result = subprocess.run([cmd], capture_output=True, text=True, env=CONFIG.get_QtFileDialog_env())
                file_path = result.stdout.strip()
                
                return file_path if file_path else no_update
            except Exception as e:
                logger.error(f"파일 브라우저 오류 (Concat): {str(e)}")
                return no_update
        
        # Merge 모드 파일 로드 콜백
        @app.callback(
            Output("combine-merge-file-info", "style"),
            Output("combine-merge-file-stats", "children"),
            Output("combine-merge-left-key", "data"),
            Output("combine-merge-right-key", "data"),
            Output("toaster", "toasts", allow_duplicate=True),
            Input("combine-merge-file-load", "n_clicks"),
            State("combine-merge-file-input", "value"),
            prevent_initial_call=True
        )
        def load_merge_file(n_clicks, file_path):
            """파일 로드 및 정보 표시 (Merge 모드)"""
            if n_clicks is None or n_clicks == 0 or not file_path:
                raise exceptions.PreventUpdate
                
            try:
                # 현재 데이터프레임
                current_df = SSDF.dataframe
                if current_df is None or current_df.is_empty():
                    return no_update, no_update, no_update, no_update, [
                        dbpc.Toast(message="현재 데이터가 로드되지 않았습니다", intent="warning", icon="warning-sign")
                    ]
                
                # 새 데이터프레임 로드
                file_path = file_path.strip()
                new_df = file2df(file_path)
                
                if new_df is None or new_df.is_empty():
                    return no_update, no_update, no_update, no_update, [
                        dbpc.Toast(message="파일 로드에 실패했습니다", intent="danger", icon="error")
                    ]
                
                # 임시 저장
                app.server.config['COMBINE_MERGE_DF'] = new_df

                # 파일 정보 생성 (시스템 컬럼 제외)
                visible_cols_current = [col for col in current_df.columns if col not in self.system_columns]
                visible_cols_new = [col for col in new_df.columns if col not in self.system_columns]
                
                stats = [
                    dmc.Text(f"파일명: {os.path.basename(file_path)}", size="sm"),
                    dmc.Text(f"행 수: {new_df.shape[0]:,}", size="sm"),
                    dmc.Text(f"열 수: {len(visible_cols_new):,}", size="sm"),
                ]

                
                # 컬럼 목록 생성 (uniqid 제외)
                current_cols = [{"label": col, "value": col} for col in visible_cols_current]
                new_cols = [{"label": col, "value": col} for col in visible_cols_new]
                
                return {"display": "block"}, stats, current_cols, new_cols, [
                    dbpc.Toast(message=f"파일을 성공적으로 로드했습니다: {os.path.basename(file_path)}", intent="success", icon="endorsed")
                ]

                
            except Exception as e:
                logger.error(f"파일 로드 오류 (Merge): {str(e)}")
                return no_update, no_update, no_update, no_update, [
                    dbpc.Toast(message=f"파일 로드 오류: {str(e)}", intent="danger", icon="error")
                ]
        
        # Concat 모드 파일 로드 콜백
        @app.callback(
            Output("combine-concat-file-info", "style"),
            Output("combine-concat-file-stats", "children"),
            Output("toaster", "toasts", allow_duplicate=True),
            Input("combine-concat-file-load", "n_clicks"),
            State("combine-concat-file-input", "value"),
            prevent_initial_call=True
        )
        def load_concat_file(n_clicks, file_path):
            """파일 로드 및 정보 표시 (Concat 모드)"""
            if n_clicks is None or n_clicks == 0 or not file_path:
                raise exceptions.PreventUpdate
                
            try:
                # 현재 데이터프레임
                current_df = SSDF.dataframe
                if current_df is None or current_df.is_empty():
                    return no_update, no_update, [
                        dbpc.Toast(message="현재 데이터가 로드되지 않았습니다", intent="warning", icon="warning-sign")
                    ]
                
                # 새 데이터프레임 로드
                file_path = file_path.strip()
                new_df = file2df(file_path)
                
                if new_df is None or new_df.is_empty():
                    return no_update, no_update, [
                        dbpc.Toast(message="파일 로드에 실패했습니다", intent="danger", icon="error")
                    ]
                
                # 임시 저장
                app.server.config['COMBINE_CONCAT_DF'] = new_df
                
                # 파일 정보 생성
                stats = [
                    dmc.Text(f"파일명: {os.path.basename(file_path)}", size="sm"),
                    dmc.Text(f"행 수: {new_df.shape[0]:,}", size="sm"),
                    dmc.Text(f"열 수: {new_df.shape[1] - 1:,}", size="sm"),  # uniqid 제외
                ]
                
                # 컬럼 불일치 확인 및 경고
                current_cols = set(current_df.columns)
                new_cols = set(new_df.columns)
                
                missing_cols = current_cols - new_cols
                extra_cols = new_cols - current_cols
                
                warnings = []
                if missing_cols:
                    warnings.append(dmc.Alert(
                        f"현재 데이터에는 있지만 새 데이터에는 없는 컬럼: {', '.join(sorted(missing_cols))}",
                        color="yellow",
                        variant="light",
                        mt=10
                    ))
                
                if extra_cols:
                    warnings.append(dmc.Alert(
                        f"새 데이터에만 있는 컬럼: {', '.join(sorted(extra_cols))}",
                        color="blue",
                        variant="light",
                        mt=10
                    ))
                
                return {"display": "block"}, stats + warnings, [
                    dbpc.Toast(message=f"파일을 성공적으로 로드했습니다: {os.path.basename(file_path)}", intent="success", icon="endorsed")
                ]
                
            except Exception as e:
                logger.error(f"파일 로드 오류 (Concat): {str(e)}")
                return no_update, no_update, [
                    dbpc.Toast(message=f"파일 로드 오류: {str(e)}", intent="danger", icon="error")
                ]
        
        # Merge 미리보기 콜백
        @app.callback(
            Output("combine-merge-preview-container", "style"),
            Output("combine-merge-preview-content", "children"),
            Output("toaster", "toasts", allow_duplicate=True),
            Input("combine-merge-preview-btn", "n_clicks"),
            State("combine-merge-left-key", "value"),
            State("combine-merge-right-key", "value"),
            State("combine-merge-type", "value"),
            State("combine-merge-left-suffix", "value"),
            State("combine-merge-right-suffix", "value"),
            prevent_initial_call=True
        )
        def preview_merge(n_clicks, left_key, right_key, join_type, left_suffix, right_suffix):
            """Join 미리보기 생성"""
            if n_clicks is None or n_clicks == 0:
                raise exceptions.PreventUpdate
                
            if not left_key or not right_key:
                return no_update, no_update, [
                    dbpc.Toast(message="양쪽 데이터프레임의 키 컬럼을 선택해주세요", intent="warning", icon="warning-sign")
                ]
                
            try:
                current_df = SSDF.dataframe
                new_df = app.server.config.get('COMBINE_MERGE_DF', None)
                
                if current_df is None or new_df is None:
                    return no_update, no_update, [
                        dbpc.Toast(message="데이터가 로드되지 않았습니다", intent="warning", icon="warning-sign")
                    ]
                
                # JOIN 수행 (미리보기용)
                try:
                    # 복사본 생성하여 작업
                    current_sample = current_df.head(100).clone()
                    new_sample = new_df.head(100).clone()
                    
                    # Join 전 시스템 컬럼 제거
                    current_sample, new_sample, _ = self._prepare_join_dataframes(current_sample, new_sample)
                    
                    # Join 수행
                    result_df = self._perform_join(current_sample, new_sample, left_key, right_key, join_type, left_suffix, right_suffix)
                    
                    # 미리보기용 샘플 행 추출
                    result_df = result_df.head(5)
                    
                    if result_df.is_empty():
                        return {"display": "block"}, dmc.Alert(
                            "결과가 없습니다. 선택한 키로 매칭되는 데이터가 없습니다.",
                            color="yellow",
                            variant="light"
                        ), no_update
                    
                    # 중복 컬럼 및 suffix 적용 예시 표시
                    current_cols = set(current_sample.columns)
                    new_cols = set(new_sample.columns)
                    duplicate_cols = (current_cols & new_cols) - {left_key, right_key}


                    info_text = []
                    if duplicate_cols:
                        info_text.append(
                            dmc.Alert(
                                title="중복 컬럼 발견",
                                children=[
                                    dmc.Text(f"양쪽 데이터에 존재하는 컬럼: {', '.join(duplicate_cols)}", mb=5),
                                    dmc.Text(f"현재 데이터의 중복 컬럼 → '{left_suffix}' 추가", mb=2),
                                    dmc.Text(f"새 데이터의 중복 컬럼 → '{right_suffix}' 추가", mb=2),
                                    dmc.Text("예: 'Score' → 'Score_current', 'Score_new'", c="dimmed", size="sm")
                                ],
                                color="blue",
                                variant="light",
                                mb=10
                            )
                        )
                    
                    # 테이블로 변환
                    result_table = self._create_preview_table(result_df)
                    
                    # 행 수 정보 추가
                    preview_content = [
                        dmc.Text(f"결과 예상 행 수: 약 {result_df.height:,} 행", c="dimmed", size="sm", mb=5),
                    ] + info_text + [result_table]
                    
                    return {"display": "block"}, preview_content, no_update
                    
                except Exception as e:
                    logger.error(f"Join 미리보기 오류: {str(e)}")
                    return no_update, no_update, [
                        dbpc.Toast(message=f"Join 미리보기 오류: {str(e)}", intent="danger", icon="error")
                    ]
                
            except Exception as e:
                logger.error(f"미리보기 생성 오류: {str(e)}")
                return no_update, no_update, [
                    dbpc.Toast(message=f"미리보기 생성 오류: {str(e)}", intent="danger", icon="error")
                ]


        # Concat 미리보기 콜백
        @app.callback(
            Output("combine-concat-preview-container", "style"),
            Output("combine-concat-preview-content", "children"),
            Output("toaster", "toasts", allow_duplicate=True),
            Input("combine-concat-preview-btn", "n_clicks"),
            State("combine-concat-add-source", "checked"),
            State("combine-concat-source-col", "value"),
            prevent_initial_call=True
        )
        def preview_concat(n_clicks, add_source, source_col):
            """Concatenate 미리보기 생성"""
            if n_clicks is None or n_clicks == 0:
                raise exceptions.PreventUpdate
                
            try:
                current_df = SSDF.dataframe
                new_df = app.server.config.get('COMBINE_CONCAT_DF', None)
                
                if current_df is None or new_df is None:
                    return no_update, no_update, [
                        dbpc.Toast(message="데이터가 로드되지 않았습니다", intent="warning", icon="warning-sign")
                    ]
                
                # 연결 수행 (미리보기용 - 최대 5행)
                try:
                    # 복사본 생성하여 작업
                    current_sample = current_df.head(3).clone()
                    new_sample = new_df.head(3).clone()
                    
                    # 소스 컬럼 추가 옵션
                    if add_source and source_col:
                        current_sample = current_sample.with_columns(
                            pl.lit("현재 데이터").alias(source_col)
                        )
                        new_sample = new_sample.with_columns(
                            pl.lit("새 데이터").alias(source_col)
                        )
                    
                    # 컬럼 일치시키기
                    current_cols = set(current_sample.columns)
                    new_cols = set(new_sample.columns)
                    
                    # 양쪽에 없는 컬럼 추가
                    for col in current_cols - new_cols:
                        if col != "uniqid":  # uniqid는 제외
                            new_sample = new_sample.with_columns(
                                pl.lit(None).alias(col)
                            )
                    
                    for col in new_cols - current_cols:
                        if col != "uniqid":  # uniqid는 제외
                            current_sample = current_sample.with_columns(
                                pl.lit(None).alias(col)
                            )
                    
                    # 컬럼 순서 일치시키기
                    ordered_cols = [col for col in current_sample.columns if col != "uniqid"]
                    if "uniqid" in current_sample.columns:
                        ordered_cols.insert(0, "uniqid")
                    
                    current_sample = current_sample.select(ordered_cols)
                    new_sample = new_sample.select(ordered_cols)
                    
                    # 연결
                    result_df = pl.concat([current_sample, new_sample], how="vertical")
                    
                    # uniqid 제거
                    if "uniqid" in result_df.columns:
                        result_df = result_df.drop("uniqid")
                    
                    # 테이블로 변환
                    result_table = dmc.Table(
                        [
                            dmc.TableThead(
                                dmc.TableTr([
                                    dmc.TableTh(col) for col in result_df.columns
                                ])
                            ),
                            dmc.TableTbody([
                                dmc.TableTr([
                                    dmc.TableTd(str(cell)) for cell in row
                                ]) for row in result_df.rows()
                            ])
                        ],
                        striped=True,
                        highlightOnHover=True,
                        withTableBorder=True,
                        withColumnBorders=True,
                        fontSize="xs"
                    )
                    
                    # 총 행 수 정보
                    total_rows = current_df.height + new_df.height
                    
                    preview_content = [
                        dmc.Text(f"결과 예상 행 수: {total_rows:,} 행 ({current_df.height:,} + {new_df.height:,})", 
                                c="dimmed", size="sm", mb=5),
                        result_table
                    ]
                    
                    return {"display": "block"}, preview_content, no_update
                    
                except Exception as e:
                    logger.error(f"Concatenate 미리보기 오류: {str(e)}")
                    return no_update, no_update, [
                        dbpc.Toast(message=f"Concatenate 미리보기 오류: {str(e)}", intent="danger", icon="error")
                    ]
                
            except Exception as e:
                logger.error(f"미리보기 생성 오류: {str(e)}")
                return no_update, no_update, [
                    dbpc.Toast(message=f"미리보기 생성 오류: {str(e)}", intent="danger", icon="error")
                ]
        
        # Merge 적용 콜백
        @app.callback(
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("toaster", "toasts", allow_duplicate=True),
            Input("combine-merge-apply-btn", "n_clicks"),
            State("combine-merge-left-key", "value"),
            State("combine-merge-right-key", "value"),
            State("combine-merge-type", "value"),
            State("combine-merge-left-suffix", "value"),
            State("combine-merge-right-suffix", "value"),
            prevent_initial_call=True
        )
        def apply_merge(n_clicks, left_key, right_key, join_type, left_suffix, right_suffix):
            """Join 실제 적용"""
            if n_clicks is None or n_clicks == 0:
                raise exceptions.PreventUpdate
                
            if not left_key or not right_key:
                return no_update, [
                    dbpc.Toast(message="양쪽 데이터프레임의 키 컬럼을 선택해주세요", intent="warning", icon="warning-sign")
                ]
                
            try:
                current_df = SSDF.dataframe
                new_df = app.server.config.get('COMBINE_MERGE_DF', None)
                
                if current_df is None or new_df is None:
                    return no_update, [
                        dbpc.Toast(message="데이터가 로드되지 않았습니다", intent="warning", icon="warning-sign")
                    ]
                
                # JOIN 수행
                try:
                    start_time = time.time()

                    # Join 전 준비
                    current_df_prep, new_df_prep, original_uniqid = self._prepare_join_dataframes(current_df, new_df)
                    
                    # Cross join 행 수 체크
                    if join_type == "cross":
                        max_result_rows = current_df_prep.height * new_df_prep.height
                        if max_result_rows > 1000000:  # 백만 행 이상이면 경고
                            return no_update, [
                                dbpc.Toast(
                                    message=f"Cross Join 결과가 너무 큽니다 (예상 {max_result_rows:,} 행). 다른 Join 유형을 선택하거나 데이터를 필터링하세요.",
                                    intent="danger",
                                    icon="error"
                                )
                            ]

                    # Join 수행
                    result_df = self._perform_join(current_df_prep, new_df_prep, left_key, right_key, join_type, left_suffix, right_suffix)
                    
                    # uniqid 복원 또는 재생성
                    result_df = self._restore_uniqid(result_df, original_uniqid)
                    
                    elapsed_time = time.time() - start_time
                    
                    # 결과 데이터프레임으로 업데이트
                    SSDF.dataframe = result_df
                    
                    # 컬럼 정의 업데이트
                    updated_columnDefs = generate_column_definitions(result_df)

                    join_type_name = {
                        "inner": "Inner Join (교집합)", 
                        "left": "Left Join (왼쪽 유지)", 
                        "right": "Right Join (오른쪽 유지)", 
                        "outer": "Outer Join (합집합)",
                        "cross": "Cross Join (카테시안 곱)"
                    }.get(join_type, join_type)
                    
                    return updated_columnDefs, [
                        dbpc.Toast(
                            message=f"{join_type_name} 적용 완료. 결과 행 수: {result_df.height:,}, 열 수: {len(result_df.columns) - 1:,}, 처리 시간: {elapsed_time:.2f}초",
                            intent="success",
                            icon="endorsed",
                            timeout=5000
                        )
                    ]
                    
                except Exception as e:
                    logger.error(f"Join 적용 오류: {str(e)}")
                    return no_update, [
                        dbpc.Toast(message=f"Join 적용 오류: {str(e)}", intent="danger", icon="error")
                    ]
                
            except Exception as e:
                logger.error(f"Join 적용 오류: {str(e)}")
                return no_update, [
                    dbpc.Toast(message=f"Join 적용 오류: {str(e)}", intent="danger", icon="error")
                ]

        
        # Concat 적용 콜백
        @app.callback(
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("toaster", "toasts", allow_duplicate=True),
            Input("combine-concat-apply-btn", "n_clicks"),
            State("combine-concat-reset-index", "checked"),
            State("combine-concat-add-source", "checked"),
            State("combine-concat-source-col", "value"),
            prevent_initial_call=True
        )
        def apply_concat(n_clicks, reset_index, add_source, source_col):
            """Concatenate 실제 적용"""
            if n_clicks is None or n_clicks == 0:
                raise exceptions.PreventUpdate
                
            try:
                current_df = SSDF.dataframe
                new_df = app.server.config.get('COMBINE_CONCAT_DF', None)
                
                if current_df is None or new_df is None:
                    return no_update, [
                        dbpc.Toast(message="데이터가 로드되지 않았습니다", intent="warning", icon="warning-sign")
                    ]
                # 연결 수행
                try:
                    start_time = time.time()
                    
                    # uniqid 백업 (필요한 경우)
                    current_uniqid = current_df.get('uniqid') if 'uniqid' in current_df.columns and not reset_index else None
                    
                    # uniqid 제거
                    current_df_prep = self._remove_system_columns(current_df.clone())
                    new_df_prep = self._remove_system_columns(new_df.clone())
                    
                    # 소스 컬럼 추가
                    if add_source and source_col:
                        current_df_prep = current_df_prep.with_columns(pl.lit("현재 데이터").alias(source_col))
                        new_df_prep = new_df_prep.with_columns(pl.lit("새 데이터").alias(source_col))
                    
                    # 컬럼 일치시키기
                    current_df_prep, new_df_prep = self._align_columns(current_df_prep, new_df_prep)
                    
                    # 연결
                    result_df = pl.concat([current_df_prep, new_df_prep], how="vertical")
                    
                    # uniqid 처리
                    if reset_index or current_uniqid is None:
                        result_df = result_df.with_row_index("uniqid")
                    else:
                        # 기존 uniqid 사용 및 새 행에 대해 연속된 값 할당
                        new_uniqid_start = current_df.height
                        new_uniqid = pl.Series(range(new_uniqid_start, new_uniqid_start + new_df.height))
                        combined_uniqid = pl.concat([current_uniqid, new_uniqid])
                        result_df = result_df.with_columns(combined_uniqid.alias("uniqid"))
                    
                    elapsed_time = time.time() - start_time
                    
                    # 결과 데이터프레임으로 업데이트
                    SSDF.dataframe = result_df
                    
                    # 컬럼 정의 업데이트
                    updated_columnDefs = generate_column_definitions(result_df)
                    
                    return updated_columnDefs, [
                        dbpc.Toast(
                            message=f"데이터 연결 완료. 결과 행 수: {result_df.height:,}, 열 수: {len(result_df.columns) - 1:,}, 처리 시간: {elapsed_time:.2f}초",
                            intent="success",
                            icon="endorsed",
                            timeout=5000
                        )
                    ]
                    
                except Exception as e:
                    logger.error(f"Concatenate 적용 오류: {str(e)}")
                    return no_update, [
                        dbpc.Toast(message=f"데이터 연결 오류: {str(e)}", intent="danger", icon="error")
                    ]
                
            except Exception as e:
                logger.error(f"Concatenate 적용 오류: {str(e)}")
                return no_update, [
                    dbpc.Toast(message=f"데이터 연결 오류: {str(e)}", intent="danger", icon="error")
                ]


        # 조건에 따라 소스 컬럼명 입력 필드 표시/숨김
        @app.callback(
            Output("combine-concat-source-col", "disabled"),
            Input("combine-concat-add-source", "checked"),
            prevent_initial_call=True
        )
        def toggle_source_col_input(add_source):
            """소스 컬럼 추가 체크박스에 따라 입력 필드 활성화/비활성화"""
            return not add_source

    def _perform_join(self, df1, df2, left_key, right_key, join_type, left_suffix, right_suffix):
        """Join 수행 유틸리티 함수"""
        if join_type == "cross":
            # Cross join을 위한 임시 키 생성
            df1 = df1.with_columns(pl.lit(1).alias("__cross_key"))
            df2 = df2.with_columns(pl.lit(1).alias("__cross_key"))
            result = df1.join(
                df2,
                left_on="__cross_key",
                right_on="__cross_key",
                how="inner",
                suffix=right_suffix  # polars join에서는 오른쪽 dataframe의 중복 컬럼에만 suffix 적용
            ).drop("__cross_key")
        else:
            # 일반 join
            # 중복 컬럼 확인
            df1_cols = set(df1.columns)
            df2_cols = set(df2.columns)
            
            # join 키를 제외한 중복 컬럼 찾기
            duplicate_cols = (df1_cols & df2_cols) - {left_key, right_key}
            
            if duplicate_cols:
                # 중복 컬럼이 있는 경우: 왼쪽 데이터프레임의 중복 컬럼에 left_suffix 추가
                for col in duplicate_cols:
                    df1 = df1.rename({col: f"{col}{left_suffix}"})
                
                # join 수행 (오른쪽 중복 컬럼에 right_suffix 적용)
                result = df1.join(
                    df2,
                    left_on=left_key,
                    right_on=right_key,
                    how=join_type,
                    suffix=right_suffix
                )
            else:
                # 중복 컬럼이 없는 경우: 일반 join
                result = df1.join(
                    df2,
                    left_on=left_key,
                    right_on=right_key,
                    how=join_type
                )
            
            # join 키가 다른 경우, 오른쪽 키 컬럼 제거 (이미 왼쪽 키 컬럼에 데이터가 있음)
            if left_key != right_key and right_key in result.columns:
                result = result.drop(right_key)
        
        return result

    
    def _align_columns(self, df1, df2):
        """두 데이터프레임의 컬럼 일치시키기"""
        df1_cols = set(df1.columns)
        df2_cols = set(df2.columns)
        
        # 양쪽에 없는 컬럼 추가
        for col in df1_cols - df2_cols:
            df2 = df2.with_columns(pl.lit(None).alias(col))
        
        for col in df2_cols - df1_cols:
            df1 = df1.with_columns(pl.lit(None).alias(col))
        
        # 컬럼 순서 일치시키기
        common_columns = sorted(df1_cols.union(df2_cols))
        df1 = df1.select(common_columns)
        df2 = df2.select(common_columns)
        
        return df1, df2
    
    def _create_preview_table(self, df):
        """미리보기 테이블 생성"""
        return dmc.Table(
            [
                dmc.TableThead(
                    dmc.TableTr([
                        dmc.TableTh(col) for col in df.columns
                    ])
                ),
                dmc.TableTbody([
                    dmc.TableTr([
                        dmc.TableTd(str(cell)) for cell in row
                    ]) for row in df.rows()
                ])
            ],
            striped=True,
            highlightOnHover=True,
            withTableBorder=True,
            withColumnBorders=True,
        )
