import flask
import dash_ag_grid as dag
from dash import Input, Output, no_update
from typing import Dict, Any
from components.dag.column_definitions import DEFAULT_COL_DEF
from components.dag.server_side_operations import extract_rows_from_data
from utils.db_management import ROW_COUNTER, DATAFRAME
from utils.logging_utils import logger
from dash_extensions import EventListener


class DataGrid:
    """
    DataGrid component for displaying and managing grid data.
    """

    DASH_GRID_OPTIONS: Dict[str, Any] = {
        "rowHeight": 24,  # 각 행의 높이 (픽셀)
        "headerHeight": 30,  # 헤더 행의 높이 (픽셀)
        "cacheBlockSize": 1000,  # 한 번에 캐시할 행의 수
        "maxBlocksInCache": 3,  # 최대 캐시 블록 수
        "blockLoadDebounceMillis": 100,  # 블록 로드 요청 간 최소 시간 간격 (밀리초)
        "enableCharts": True,  # 차트 기능 활성화
        "undoRedoCellEditing": True,  # 셀 편집 취소/재실행 기능 활성화
        "enableRangeSelection": True,  # 범위 선택 기능 활성화
        "enableAdvancedFilter": True,  # 고급 필터링 기능 활성화
        "rowGroupPanelShow": "always",  # 행 그룹 패널 항상 표시
        "groupAllowUnbalanced": True,  # 불균형 그룹 허용
        "suppressMultiRangeSelection": False,  # 다중 범위 선택 허용
        "groupLockGroupColumns": 0,  # 그룹 열 잠금 비활성화
        "getChildCount": {"function": "getChildCount(params)"},  # 자식 행 수 계산 함수
        "treeData": False,  # 트리 데이터 모드 비활성화
        "rowSelection": "multiple",  # 다중 행 선택 모드
        "suppressRowClickSelection": True,  # 행 클릭 시 자동 선택 비활성화
        "purgeClosedRowNodes": True,  # 닫힌 행 노드 제거
        "includeHiddenColumnsInAdvancedFilter": True,  # 숨겨진 열도 고급 필터에 포함
        "isServerSideGroup": {"function": "params ? params.group : null"},  # 서버 사이드 그룹 확인 함수
        "getServerSideGroupKey": {"function": "params ? params.tree_group : null"},  # 서버 사이드 그룹 키 가져오기 함수
        "autoGroupColumnDef": {
            "field": "tree_group",  # 자동 그룹 열 정의
        },
        "sideBar": {
            "toolPanels": [
                {
                    "id": "columns",
                    "labelDefault": "Columns",
                    "labelKey": "columns",
                    "iconKey": "columns",
                    "toolPanel": "agColumnsToolPanel",
                },
            ],
            "defaultToolPanel": None,  # 사이드바 설정
        },
        "statusBar": {
            "statusPanels": [
                {
                    "statusPanel": "agAggregationComponent",  # 상태바에 집계 컴포넌트 표시
                }
            ]
        },
    }



    def layout(self) -> EventListener:
        """
        Generate the layout for the DataGrid component.

        Returns:
            EventListener: The layout wrapped in an EventListener.
        """
        events = [
            {
                "event": "mousedown",
                "props": [
                    "altKey",
                    "ctrlKey",
                    "shiftKey",
                    "srcElement.innerText",
                    "srcElement.attributes.col-id.nodeValue",
                    "button",
                ],
            }
        ]

        return EventListener(
            id="el",
            children=dag.AgGrid(
                id="aggrid-table",
                selectedRows=[],
                columnDefs=[],
                defaultColDef=DEFAULT_COL_DEF,
                enableEnterpriseModules=True,
                rowModelType="serverSide",
                persisted_props=["filterModel"],
                dashGridOptions=self.DASH_GRID_OPTIONS,
                style={"height": "88vh", "width": "100%", "overflow": "auto"},
            ),
            events=events,
            logging=False,
        )
        
    def register_callbacks(self, app):

        @app.server.route("/api/serverData", methods=["POST"])
        def serverData():
            data = flask.request.json
            request = data["request"]
            response = extract_rows_from_data(request)
            counter_info = self._generate_counter_info()
            return flask.jsonify({"response": response, "counter_info": counter_info})

        app.clientside_callback(
            """
            async function initializeGrid(id, columnDefs) {
                const MAX_ATTEMPTS = 20;
                const DELAY_DURATION = 100;

                async function delay(ms) {
                    return new Promise(resolve => setTimeout(resolve, ms));
                }

                async function getGrid(id) {
                    for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
                        try {
                            const grid = dash_ag_grid.getApi(id);
                            if (grid) return grid;
                        } catch (error) {
                            console.warn(`Attempt ${attempt + 1}: Error fetching grid API:`, error);
                        }
                        await delay(DELAY_DURATION);
                    }
                    throw new Error("Failed to initialize grid API after multiple attempts.");
                }

                try {
                    const grid = await getGrid(id);
                    const datasource = createServerSideDatasource();
                    grid.updateGridOptions({ serverSideDatasource: datasource });
                    console.log("Grid initialized successfully");
                } catch (error) {
                    console.error(error.message);
                }

                return window.dash_clientside.no_update;
            }
            """,
            Output("row-counter", "children"),
            [
                Input("aggrid-table", "id"),
                Input("aggrid-table", "columnDefs"),
            ],
            prevent_initial_call=True,
        )

        @app.callback(
            Output("notifications", "children", allow_duplicate=True),
            Input("notifications", "children"),
            prevent_initial_call=True,
        )
        def refresh_noti(n):
            return None



    @staticmethod
    def _generate_counter_info() -> str:
        """
        Generate counter information string.
        """
        counter_info = ""
        if ROW_COUNTER.get("filtered"):
            counter_info += f"Filtered: {ROW_COUNTER['filtered']}"
        if ROW_COUNTER.get("groupby"):
            counter_info += f"   GroupRows: {ROW_COUNTER['groupby']}"
        if ROW_COUNTER.get("waived"):
            counter_info += f"   Waived: {ROW_COUNTER['waived']}"
        return counter_info