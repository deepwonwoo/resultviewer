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
from components.menu.edit.utils import find_tab_in_layout

class CombiningDataframes:
    def __init__(self):
        self.join_types = [
            {"value": "inner", "label": "Inner Join (교집합)"},
            {"value": "left", "label": "Left Join (왼쪽 데이터 유지)"},
            {"value": "right", "label": "Right Join (오른쪽 데이터 유지)"},
            {"value": "outer", "label": "Outer Join (합집합)"},
            {"value": "cross", "label": "Cross Join (카테시안 곱)"}
        ]
        
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
                                        label="왼쪽 서픽스",
                                        description="중복 컬럼명에 추가할 왼쪽 서픽스",
                                        placeholder="_left",
                                        value="_left",
                                        style={"width": "48%"}
                                    ),
                                    dmc.TextInput(
                                        id="combine-merge-right-suffix",
                                        label="오른쪽 서픽스",
                                        description="중복 컬럼명에 추가할 오른쪽 서픽스",
                                        placeholder="_right",
                                        value="_right",
                                        style={"width": "48%"}
                                    )
                                ], grow=True, mb=15),
                                
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
                                    dmc.Text("   - Left Join: 왼쪽(현재) 데이터의 모든 행 유지"),
                                    dmc.Text("   - Right Join: 오른쪽(새) 데이터의 모든 행 유지"),
                                    dmc.Text("   - Outer Join: 모든 키 유지 (합집합)"),
                                    dmc.Space(h=5),
                                    dmc.Text("2. Concatenate: 두 데이터프레임을 수직으로 쌓아 결합합니다."),
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
            if n_clicks is None:
                raise exceptions.PreventUpdate
                
            dff = displaying_df()
            if dff is None:
                return no_update, [dbpc.Toast(message=f"데이터가 로드되지 않았습니다", intent="warning", icon="warning-sign")]

            # 기존 탭 검색
            tab_search_result = find_tab_in_layout(current_model, "combine-dataframes-tab")
            
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
                "name": "Combine Dataframes",
                "component": "button",
                "enableClose": True,
                "id": "combine-dataframes-tab"
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
                
                # 파일 정보 생성
                stats = [
                    dmc.Text(f"파일명: {os.path.basename(file_path)}", size="sm"),
                    dmc.Text(f"행 수: {new_df.shape[0]:,}", size="sm"),
                    dmc.Text(f"열 수: {new_df.shape[1] - 1:,}", size="sm"),  # uniqid 제외
                ]
                
                # 컬럼 목록 생성 (uniqid 제외)
                current_cols = [{"label": col, "value": col} for col in current_df.columns if col != "uniqid" and col != "group" and col != "childCount"]
                new_cols = [{"label": col, "value": col} for col in new_df.columns if col != "uniqid" and col != "group" and col != "childCount"]
                
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
                
                # JOIN 수행 (미리보기용 - 최대 5행)
                try:
                    # 복사본 생성하여 작업
                    current_sample = current_df.head(100).clone()
                    new_sample = new_df.head(100).clone()
                    
                    # Join 수행
                    if join_type == "inner":
                        result_df = current_sample.join(
                            new_sample, 
                            left_on=left_key,
                            right_on=right_key,
                            how="inner",
                            suffix=f"{left_suffix}_{right_suffix}"
                        )
                    elif join_type == "left":
                        result_df = current_sample.join(
                            new_sample, 
                            left_on=left_key,
                            right_on=right_key,
                            how="left",
                            suffix=f"{left_suffix}_{right_suffix}"
                        )
                    elif join_type == "right":
                        result_df = current_sample.join(
                            new_sample, 
                            left_on=left_key,
                            right_on=right_key,
                            how="right",
                            suffix=f"{left_suffix}_{right_suffix}"
                        )
                    elif join_type == "outer":
                        result_df = current_sample.join(
                            new_sample, 
                            left_on=left_key,
                            right_on=right_key,
                            how="outer",
                            suffix=f"{left_suffix}_{right_suffix}"
                        )
                    elif join_type == "cross":
                        # Cross join은 row 수가 두 DF의 곱으로 증가하므로 아주 작은 샘플만 사용
                        current_tiny = current_sample.head(3)
                        new_tiny = new_sample.head(3)
                        # Polars에서는 cross_join이 없으므로 key를 상수값으로 만들고 inner join
                        current_tiny = current_tiny.with_columns(pl.lit(1).alias("__key"))
                        new_tiny = new_tiny.with_columns(pl.lit(1).alias("__key"))
                        result_df = current_tiny.join(
                            new_tiny,
                            left_on="__key",
                            right_on="__key",
                            how="inner",
                            suffix=f"{left_suffix}_{right_suffix}"
                        ).drop("__key")
                    
                    # 최대 5행만 표시
                    result_df = result_df.head(5)
                    
                    if "uniqid" in result_df.columns:
                        result_df = result_df.drop("uniqid")
                    

                    if result_df.is_empty():
                        return {"display": "block"}, dmc.Alert(
                            "결과가 없습니다. 선택한 키로 매칭되는 데이터가 없습니다.",
                            color="yellow",
                            variant="light"
                        ), no_update
                    
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
                    )
                    
                    # 행 수 정보 추가
                    preview_content = [
                        dmc.Text(f"결과 예상 행 수: 약 {result_df.height:,} 행", c="dimmed", size="sm", mb=5),
                        result_table
                    ]
                    
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
                        withBorder=True,
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
                    
                    # Join 수행
                    if join_type == "inner":
                        result_df = current_df.join(
                            new_df, 
                            left_on=left_key,
                            right_on=right_key,
                            how="inner",
                            suffix=f"{left_suffix}_{right_suffix}"
                        )
                    elif join_type == "left":
                        result_df = current_df.join(
                            new_df, 
                            left_on=left_key,
                            right_on=right_key,
                            how="left",
                            suffix=f"{left_suffix}_{right_suffix}"
                        )
                    elif join_type == "right":
                        result_df = current_df.join(
                            new_df, 
                            left_on=left_key,
                            right_on=right_key,
                            how="right",
                            suffix=f"{left_suffix}_{right_suffix}"
                        )
                    elif join_type == "outer":
                        result_df = current_df.join(
                            new_df, 
                            left_on=left_key,
                            right_on=right_key,
                            how="outer",
                            suffix=f"{left_suffix}_{right_suffix}"
                        )
                    elif join_type == "cross":
                        # Cross join은 행 수가 폭발적으로 증가할 수 있으므로 경고
                        max_result_rows = current_df.height * new_df.height
                        if max_result_rows > 1000000:  # 백만 행 이상이면 경고
                            return no_update, [
                                dbpc.Toast(
                                    message=f"Cross Join 결과가 너무 큽니다 (예상 {max_result_rows:,} 행). 다른 Join 유형을 선택하거나 데이터를 필터링하세요.",
                                    intent="danger",
                                    icon="error"
                                )
                            ]
                        
                        # Polars에서는 cross_join이 없으므로 key를 상수값으로 만들고 inner join
                        current_df = current_df.with_columns(pl.lit(1).alias("__key"))
                        new_df = new_df.with_columns(pl.lit(1).alias("__key"))
                        result_df = current_df.join(
                            new_df,
                            left_on="__key",
                            right_on="__key",
                            how="inner",
                            suffix=f"{left_suffix}_{right_suffix}"
                        ).drop("__key")
                    
                    # uniqid 재생성
                    result_df = result_df.drop("uniqid").with_row_index("uniqid")
                    
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
                    
                    # 소스 컬럼 추가 옵션
                    if add_source and source_col:
                        current_df = current_df.with_columns(
                            pl.lit("현재 데이터").alias(source_col)
                        )
                        new_df = new_df.with_columns(
                            pl.lit("새 데이터").alias(source_col)
                        )
                    
                    # 컬럼 일치시키기
                    current_cols = set(current_df.columns)
                    new_cols = set(new_df.columns)
                    
                    # 양쪽에 없는 컬럼 추가
                    for col in current_cols - new_cols:
                        if col != "uniqid":  # uniqid는 제외
                            new_df = new_df.with_columns(
                                pl.lit(None).alias(col)
                            )
                    
                    for col in new_cols - current_cols:
                        if col != "uniqid":  # uniqid는 제외
                            current_df = current_df.with_columns(
                                pl.lit(None).alias(col)
                            )
                    
                    # 컬럼 순서 일치시키기
                    ordered_cols = [col for col in current_df.columns if col != "uniqid"]
                    if "uniqid" in current_df.columns:
                        ordered_cols.insert(0, "uniqid")
                    
                    current_df = current_df.select(ordered_cols)
                    new_df = new_df.select(ordered_cols)
                    
                    # 연결
                    result_df = pl.concat([current_df, new_df], how="vertical")
                    
                    # 인덱스 리셋
                    if reset_index:
                        result_df = result_df.drop("uniqid").with_row_index("uniqid")
                    
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

