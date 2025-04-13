import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, no_update, exceptions, ctx

from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions
from components.menu.edit.utils import find_tab_in_layout

class DelRow:
    def __init__(self):
        pass
        
    def button_layout(self):
        return dbpc.Button(
            "Delete Row", 
            id="delete-row-btn", 
            icon="remove-row", 
            minimal=True, 
            outlined=True
        )


    def tab_layout(self):
        return dmc.Paper(
            children=[
                dmc.Group([
                    dbpc.EntityTitle(
                        title="Delete Rows", 
                        heading="H5", 
                        icon="remove-row"
                    )
                ], grow=True),
                dmc.Space(h=20),
                
                # 필터링 정보 컨테이너
                dmc.Paper(
                    children=[
                        dmc.Text("필터링된 데이터 정보", w=500, size="sm"),
                        dmc.Divider(my="xs"),
                        dmc.Text(
                            "현재 적용된 필터에 따라 보이는 행만 삭제됩니다.",
                            size="xs", 
                            c="dimmed"
                        ),
                        dmc.Text(
                            id="delete-row-filtered-status",
                            size="sm",
                            mt=10
                        ),
                    ],
                    p="xs",
                    withBorder=True,
                    shadow="xs",
                ),
                
                dmc.Space(h=20),
                
                # 삭제 확인 체크박스
                dmc.Checkbox(
                    id="delete-row-confirm",
                    label="삭제를 확인합니다. 이 작업은 되돌릴 수 없습니다.",
                    size="sm",
                ),
                
                dmc.Space(h=15),
                
                # 삭제 버튼
                dmc.Group([
                    dbpc.Button(
                        "Delete Filtered Rows", 
                        id="delete-row-apply-btn", 
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
                                    dmc.Text("1. 그리드에 필터를 적용하여 삭제할 행을 결정합니다."),
                                    dmc.Text("2. 필터가 적용되면 현재 표시된 행 수가 나타납니다."),
                                    dmc.Text("3. 삭제 확인 체크박스를 클릭하세요."),
                                    dmc.Text("4. Delete Filtered Rows 버튼을 클릭하면 필터링된 행만 삭제됩니다.")
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
            Input("delete-row-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True
        )
        def handle_delete_row_button_click(n_clicks, current_model):
            """Delete Row 버튼 클릭 시 우측 패널에 탭 추가"""
            if n_clicks is None:
                raise exceptions.PreventUpdate
                
            dff = displaying_df()
            if dff is None:
                return no_update, [dbpc.Toast(message=f"데이터가 로드되지 않았습니다", intent="warning", icon="warning-sign")]

            # 기존 탭 검색
            tab_search_result = find_tab_in_layout(current_model, "row-del-tab")
            
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
                "name": "Delete Row",
                "component": "button",
                "enableClose": True,
                "id": "row-del-tab"
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
            Output("delete-row-filtered-status", "children"),
            [Input("row-counter", "children")]
        )
        def update_filtered_status(row_counter):
            print("update_filtered_status: row_counter:", row_counter)
            """필터링된 행 정보 업데이트"""
            # 기본값
            total_rows = len(SSDF.dataframe) if SSDF.dataframe is not None else 0
            filtered_text = "필터가 적용되지 않았습니다. 모든 행이 표시되고 있습니다."
            
            # row_counter 분석
            if row_counter:
                if "Filtered:" in row_counter:
                    try:
                        filtered_part = row_counter.split("Filtered:")[1].strip()
                        filtered_count = int(filtered_part.replace(",", ""))
                        
                        if filtered_count < total_rows:
                            filtered_text = f"현재 {filtered_count:,}개 행이 필터링되어 있습니다. (전체 {total_rows:,}개 중)"
                        else:
                            filtered_text = "모든 행이 표시되고 있습니다. 필터를 적용하여 일부 행만 표시하세요."
                    except (IndexError, ValueError):
                        pass
            
            return filtered_text
        
        @app.callback(
            Output("delete-row-apply-btn", "disabled"),
            [
                Input("delete-row-confirm", "checked"),
                Input("delete-row-filtered-status", "children")
            ]
        )
        def toggle_delete_button(confirmed, filtered_status):
            """삭제 버튼 활성화/비활성화"""
            if not confirmed:
                return True
                
            # 필터링 상태 확인
            if "현재" in filtered_status and "개 행이 필터링되어 있습니다" in filtered_status:
                return False  # 필터가 적용되었고 체크박스가 선택되었으면 버튼 활성화
            
            return True  # 그 외 경우는 버튼 비활성화
        
        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("delete-row-confirm", "checked"),
            Input("delete-row-apply-btn", "n_clicks"),
            [
                State("aggrid-table", "filterModel"),
                State("row-counter", "children")
            ],
            prevent_initial_call=True
        )
        def handle_delete_row_submission(n_clicks, filter_model, row_counter):
            """행 삭제 로직 실행"""
            if not n_clicks:
                raise exceptions.PreventUpdate
                
            try:
                # 원본 데이터프레임
                df = SSDF.dataframe
                if df is None or df.is_empty():
                    return ([dbpc.Toast(
                        message="데이터프레임이 비어있습니다",
                        intent="warning",
                        icon="warning-sign"
                    )], no_update, False)
                
                original_row_count = len(df)
                
                # 필터링 상태 확인
                filtered_count = None
                has_filter = False
                
                # 필터모델 확인
                if filter_model:
                    has_filter = True
                
                # row_counter에서 필터링된 행 수 추출 시도
                if row_counter and "Filtered:" in row_counter:
                    try:
                        filtered_part = row_counter.split("Filtered:")[1].split()[0]
                        filtered_count = int(filtered_part.replace(",", ""))
                        if filtered_count < original_row_count:
                            has_filter = True
                    except (IndexError, ValueError):
                        pass
                
                if not has_filter:
                    return ([dbpc.Toast(
                        message="필터가 적용되지 않았거나 모든 행이 포함되어 있습니다. 특정 행만 필터링한 후 시도해주세요.",
                        intent="warning",
                        icon="warning-sign"
                    )], no_update, False)
                
                # 필터링된 데이터 가져오기
                from components.grid.dag.SSRM.apply_filter import apply_filters
                
                # 현재 필터 적용하여 필터링된 데이터 가져오기
                request = {"filterModel": filter_model}
                filtered_df = apply_filters(df, request)
                
                if filtered_df.height == df.height:
                    return ([dbpc.Toast(
                        message="필터 조건에 모든 행이 포함되어 있어 삭제할 수 없습니다. 특정 행만 필터링한 후 시도해주세요.",
                        intent="warning",
                        icon="warning-sign"
                    )], no_update, False)
                
                # 필터링된 행의 ID 추출 (uniqid가 있는 경우)
                if "uniqid" in filtered_df.columns:
                    filtered_ids = filtered_df["uniqid"].to_list()
                    
                    # 필터링된 행만 삭제 (필터링된 행은 유지하지 않음)
                    SSDF.dataframe = df.filter(~pl.col("uniqid").is_in(filtered_ids))
                    deleted_count = original_row_count - len(SSDF.dataframe)
                else:
                    # uniqid가 없는 경우 인덱스로 처리
                    # 필터링된 행을 인덱스로 식별하여 삭제
                    all_indices = set(range(original_row_count))
                    filtered_indices = set(filtered_df.row_index())
                    keep_indices = list(all_indices - filtered_indices)
                    
                    SSDF.dataframe = df.select(keep_indices)
                    deleted_count = original_row_count - len(SSDF.dataframe)
                
                # 성공 메시지
                toast = dbpc.Toast(
                    message=f"필터링된 {deleted_count:,}개 행이 삭제되었습니다",
                    intent="success",
                    icon="endorsed",
                    timeout=4000
                )
                
                # 행 삭제 후 uniqid 인덱스 재생성
                if "uniqid" in SSDF.dataframe.columns:
                    try:
                        SSDF.dataframe = SSDF.dataframe.drop("uniqid").with_row_index("uniqid")
                    except Exception as e:
                        logger.warning(f"uniqid 인덱스 재생성 실패: {e}")
                
                # 컬럼 정의 업데이트
                updated_columnDefs = generate_column_definitions(SSDF.dataframe)
                
                # 체크박스 초기화
                return [toast], updated_columnDefs, False
                    
            except Exception as e:
                # 오류 메시지
                logger.error(f"행 삭제 실패: {str(e)}")
                return ([dbpc.Toast(
                    message=f"행 삭제 실패: {str(e)}",
                    intent="danger",
                    icon="error"
                )], no_update, False)
