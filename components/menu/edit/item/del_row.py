import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, no_update, exceptions, dcc, clientside_callback

from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions
from components.menu.edit.common_utils import find_tab_in_layout
from components.grid.dag.SSRM.apply_filter import apply_filters


class DelRow:
    def __init__(self):
        pass

    def button_layout(self):
        return dbpc.Button("Delete Row", id="delete-row-btn", icon="remove-row", minimal=True, outlined=True)

    def tab_layout(self):
        return html.Div(
            [
                # 필터 정보를 저장할 숨겨진 Store 컴포넌트
                dcc.Store(id="delete-row-filter-info", data={"filtered_count": 0, "has_filter": False, "total_count": 0}),
                # 필터 모델을 저장할 Store 컴포넌트 추가
                dcc.Store(id="delete-row-filter-model", data={}),
                dmc.Paper(
                    children=[
                        dmc.Group([dbpc.EntityTitle(title="Delete Rows", heading="H5", icon="remove-row")], grow=True),
                        dmc.Space(h=20),
                        # 필터링 정보 컨테이너
                        dmc.Paper(
                            children=[
                                dmc.Text("필터링된 데이터 정보", w=500, size="sm"),
                                dmc.Divider(my="xs"),
                                dmc.Text("현재 적용된 필터에 따라 보이는 행만 삭제됩니다.", size="xs", c="dimmed"),
                                dmc.Group(
                                    [
                                        dmc.Text(id="delete-row-filtered-status", size="sm"),
                                        dmc.Button(
                                            "필터 정보 갱신",
                                            id="refresh-filter-info-btn",
                                            size="xs",
                                            variant="subtle",
                                            leftSection=dbpc.Icon(icon="refresh"),
                                        ),
                                    ],
                                    justify="apart",
                                    mt=10,
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
                        dmc.Group(
                            [
                                dbpc.Button("Delete Filtered Rows", id="delete-row-apply-btn", outlined=True, icon="trash", intent="danger", disabled=True),
                            ],
                            justify="center",
                        ),
                        # 도움말 섹션
                        dmc.Space(h=20),
                        dmc.Accordion(value="", children=[dmc.AccordionItem([dmc.AccordionControl("도움말"), dmc.AccordionPanel([dmc.Text("1. 그리드에 필터를 적용하여 삭제할 행을 결정합니다."), dmc.Text("2. '필터 정보 갱신' 버튼을 클릭하여 현재 필터 상태를 확인합니다."), dmc.Text("3. 삭제 확인 체크박스를 클릭하세요."), dmc.Text("4. Delete Filtered Rows 버튼을 클릭하면 필터링된 행만 삭제됩니다.")])], value="help")]),
                    ],
                    p="md",
                    shadow="sm",
                    radius="xs",
                    withBorder=True,
                ),
            ]
        )

    def register_callbacks(self, app):
        @app.callback(Output("flex-layout", "model", allow_duplicate=True), Output("toaster", "toasts", allow_duplicate=True), Input("delete-row-btn", "n_clicks"), State("flex-layout", "model"), prevent_initial_call=True)
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
            right_border_index = next((i for i, b in enumerate(current_model["borders"]) if b["location"] == "right"), None)

            # 새로운 탭 정의
            new_tab = {"type": "tab", "name": "Delete Row", "component": "button", "enableClose": True, "id": "row-del-tab"}

            patched_model = Patch()

            if right_border_index is not None:
                # 기존 right border 수정
                patched_model["borders"][right_border_index]["children"].append(new_tab)
                patched_model["borders"][right_border_index]["selected"] = len(current_model["borders"][right_border_index]["children"])
            else:
                # right border가 없으면 새로 추가
                patched_model["borders"].append({"type": "border", "location": "right", "size": 400, "selected": 0, "children": [new_tab]})

            return patched_model, no_update

        # 클라이언트 사이드에서 필터 정보와 필터 모델 가져오기
        app.clientside_callback(
            """
            function(n_clicks, grid_id) {
                if (!n_clicks) return [{}, window.dash_clientside.no_update];
                
                const grid = dash_ag_grid.getApi(grid_id);
                if (!grid) {
                    console.error("Grid API not found");
                    return [{}, {filtered_count: 0, has_filter: false, total_count: 0}];
                }
                
                // 모델 정보 가져오기
                const filterModel = grid.getFilterModel();
                const advancedFilterModel = grid.getAdvancedFilterModel();
                
                // 필터 모델 (일반 또는 고급 필터) 선택
                const effectiveFilterModel = advancedFilterModel || filterModel || {};
                
                // 필터가 적용되었는지 확인
                const hasFilter = Object.keys(effectiveFilterModel).length > 0;
                
                // 현재 표시된 행 수 가져오기
                let totalCount = 0;
                let filteredCount = 0;
                
                try {
                    // getInfiniteRowCount는 서버 사이드 모델에서 전체 행 수 가져오기
                    totalCount = grid.getInfiniteRowCount();
                    
                    // getDisplayedRowCount는 현재 필터링된 행 수 가져오기
                    filteredCount = grid.getDisplayedRowCount();
                } catch (e) {
                    console.error("Error getting row counts:", e);
                }
                
                console.log("Advanced Filter Model:", advancedFilterModel);
                console.log("Filter Model:", filterModel);
                console.log("Effective Filter Model:", effectiveFilterModel);
                console.log("Filter Info:", {
                    filtered_count: filteredCount,
                    has_filter: hasFilter,
                    total_count: totalCount,
                });
                
                return [
                    effectiveFilterModel, 
                    {
                        filtered_count: filteredCount,
                        has_filter: hasFilter,
                        total_count: totalCount,
                    }
                ];
            }
            """,
            [Output("delete-row-filter-model", "data"), Output("delete-row-filter-info", "data")],
            Input("refresh-filter-info-btn", "n_clicks"),
            State("aggrid-table", "id"),
            prevent_initial_call=True,
        )

        @app.callback(Output("delete-row-filtered-status", "children"), Input("delete-row-filter-info", "data"))
        def update_filtered_status(filter_info):
            """필터링된 행 정보 업데이트"""
            # 기본값
            total_rows = len(SSDF.dataframe) if SSDF.dataframe is not None else 0
            filtered_text = "필터가 적용되지 않았습니다. 모든 행이 표시되고 있습니다."

            try:
                # filter_info에서 필터링 정보 추출
                if filter_info and isinstance(filter_info, dict):
                    has_filter = filter_info.get("has_filter", False)
                    filtered_count = filter_info.get("filtered_count", 0)
                    client_total_count = filter_info.get("total_count", 0)

                    # 클라이언트에서 가져온 전체 행 수가 있으면 사용, 없으면 서버측 데이터프레임 크기 사용
                    if client_total_count > 0:
                        total_rows = client_total_count

                    if has_filter:
                        if filtered_count < total_rows:
                            filtered_text = f"현재 {filtered_count:,}개 행이 필터링되어 있습니다. (전체 {total_rows:,}개 중)"
                        else:
                            filtered_text = "모든 행이 표시되고 있습니다. 필터를 적용하여 일부 행만 표시하세요."
            except Exception as e:
                logger.error(f"필터 정보 업데이트 오류: {e}")
                filtered_text = f"필터 정보를 가져오는 중 오류가 발생했습니다: {str(e)}"

            return filtered_text

        @app.callback(Output("delete-row-apply-btn", "disabled"), [Input("delete-row-confirm", "checked"), Input("delete-row-filter-info", "data")])
        def toggle_delete_button(confirmed, filter_info):
            """삭제 버튼 활성화/비활성화"""
            if not confirmed:
                return True
            print("toggle_delete_button")
            print(f"filter_info: {filter_info}")

            # 필터가 적용되었는지 확인
            has_filter = filter_info.get("has_filter", False) if filter_info else False
            filtered_count = filter_info.get("filtered_count", 0) if filter_info else 0
            # total_count = filter_info.get("total_count", 0) if filter_info else 0

            # 조건: 확인 체크박스 선택됨 + 필터 적용됨 + 필터링된 행이 전체 행보다 적음
            if has_filter and confirmed and filtered_count > 0:
                return False

            return True

        @app.callback(Output("toaster", "toasts", allow_duplicate=True), Output("aggrid-table", "columnDefs", allow_duplicate=True), Output("delete-row-confirm", "checked"), Input("delete-row-apply-btn", "n_clicks"), [State("delete-row-filter-model", "data"), State("delete-row-filter-info", "data")], prevent_initial_call=True)
        def handle_delete_row_submission(n_clicks, filter_model, filter_info):
            print("handle_delete_row_submission")
            print(f"filter_model: {filter_model}")
            print(f"filter_info: {filter_info}")

            """행 삭제 로직 실행"""
            if not n_clicks:
                raise exceptions.PreventUpdate

            try:
                # 원본 데이터프레임
                df = SSDF.dataframe
                if df is None or df.is_empty():
                    return ([dbpc.Toast(message="데이터프레임이 비어있습니다", intent="warning", icon="warning-sign")], no_update, False)

                original_row_count = len(df)

                # 필터링 정보 검증
                has_filter = filter_info.get("has_filter", False)
                filtered_count = filter_info.get("filtered_count", 0)

                if not has_filter or not filter_model or len(filter_model) == 0:
                    return ([dbpc.Toast(message="필터가 적용되지 않았습니다. 특정 행만 필터링한 후 시도해주세요.", intent="warning", icon="warning-sign")], no_update, False)

                # 필터가 모든 행을 포함하는지 확인
                if filtered_count >= original_row_count:
                    return ([dbpc.Toast(message="필터 조건에 모든 행이 포함되어 있어 삭제할 수 없습니다.", intent="warning", icon="warning-sign")], no_update, False)

                # 서버에서 필터 적용하여 필터링된 데이터 가져오기
                logger.info(f"필터 모델: {filter_model}")
                request = {"filterModel": filter_model}

                # SSDF.request에 필터 모델 저장 (여러 유형의 필터 모델 대응)
                if "filterType" in filter_model:  # advancedFilterModel의 경우
                    SSDF.request = {"advancedFilterModel": filter_model}
                else:  # 일반 filterModel의 경우
                    SSDF.request = request

                # 필터링된 데이터프레임 가져오기
                filtered_df = apply_filters(df, SSDF.request)

                if filtered_df.height == 0:
                    return ([dbpc.Toast(message="필터링된 행이 없어 삭제할 수 없습니다.", intent="warning", icon="warning-sign")], no_update, False)

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
                toast = dbpc.Toast(message=f"필터링된 {deleted_count:,}개 행이 삭제되었습니다", intent="success", icon="endorsed", timeout=4000)

                # 행 삭제 후 uniqid 인덱스 재생성
                if "uniqid" in SSDF.dataframe.columns:
                    try:
                        # uniqid 컬럼이 있을 경우 인덱스 재생성
                        temp_df = SSDF.dataframe.drop("uniqid")
                        SSDF.dataframe = temp_df.with_row_index("uniqid")
                    except Exception as e:
                        logger.warning(f"uniqid 인덱스 재생성 실패: {e}")

                # 컬럼 정의 업데이트
                updated_columnDefs = generate_column_definitions(SSDF.dataframe)

                # 체크박스 초기화
                return [toast], updated_columnDefs, False

            except Exception as e:
                # 오류 메시지
                logger.error(f"행 삭제 실패: {str(e)}")
                return ([dbpc.Toast(message=f"행 삭제 실패: {str(e)}", intent="danger", icon="error")], no_update, False)
