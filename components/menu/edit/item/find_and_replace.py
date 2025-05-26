import re
import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, no_update, exceptions, ctx, dcc

from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions, SYSTEM_COLUMNS
from components.menu.edit.common_utils import find_tab_in_layout, handle_tab_button_click


class FindAndReplace:
    def __init__(self):
        # 검색 방식 옵션
        self.search_modes = [["exact", "정확히 일치"], ["contains", "포함"], ["regex", "정규식"]]

        # 대소문자 구분 옵션
        self.case_sensitive_options = [["insensitive", "대소문자 구분 안함"], ["sensitive", "대소문자 구분"]]

        # 정규식 예제
        self.regex_examples = [{"value": r"\d+", "label": "숫자만 찾기", "description": "모든 숫자를 찾습니다 (예: 123, 45)"}, {"value": r"[a-zA-Z]+", "label": "알파벳만 찾기", "description": "알파벳 문자열을 찾습니다"}, {"value": r"^\w+", "label": "시작 문자열", "description": "줄의 시작 문자열을 찾습니다"}, {"value": r"\w+$", "label": "끝 문자열", "description": "줄의 끝 문자열을 찾습니다"}, {"value": r"\s+", "label": "공백 문자", "description": "하나 이상의 공백을 찾습니다"}, {"value": r"[A-Z]{2,}", "label": "대문자 연속", "description": "2개 이상 연속된 대문자를 찾습니다"}]

    def button_layout(self):
        return dbpc.Button("Find & Replace", id="find-replace-btn", icon="search-template", minimal=True, outlined=True)

    def tab_layout(self):
        return dmc.Paper(
            children=[
                dmc.Group([dbpc.Icon(icon="search-template", size=24), dmc.Title("Find and Replace", order=3)], mb="md"),
                # 컬럼 선택 섹션
                dmc.Card(
                    children=[
                        dmc.Text("검색할 컬럼 선택", w=500, mb="xs"),
                        dmc.Text("검색 및 치환을 실행할 컬럼을 선택하세요 (복수 선택 가능)", size="sm", c="dimmed", mb="xs"),
                        dmc.MultiSelect(
                            id="find-replace-column-select",
                            placeholder="컬럼 선택...",
                            required=True,
                            searchable=True,
                            clearable=True,
                            data=[],
                            leftSection=dbpc.Icon(icon="th"),
                        ),
                    ],
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    mb="md",
                ),
                # 검색 및 치환 값 입력 섹션
                dmc.Card(
                    children=[
                        dmc.Text("검색할 값", w=500, mb="xs"),
                        dmc.Text("찾을 텍스트나 패턴을 입력하세요", size="sm", c="dimmed", mb="xs"),
                        dmc.TextInput(id="find-replace-search-input", placeholder="검색어 입력...", required=True, leftSection=dbpc.Icon(icon="search"), mb="md"),
                        dmc.Text("변경할 값", w=500, mb="xs"),
                        dmc.Text("검색된 값을 대체할 텍스트를 입력하세요", size="sm", c="dimmed", mb="xs"),
                        dmc.TextInput(
                            id="find-replace-value-input",
                            placeholder="변경할 값 입력...",
                            required=True,
                            leftSection=dbpc.Icon(icon="edit"),
                        ),
                    ],
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    mb="md",
                ),
                # 검색 옵션 섹션
                dmc.Card(
                    children=[
                        dmc.Grid(
                            [
                                dmc.GridCol(
                                    span=6,
                                    children=[
                                        dmc.Text("검색 방식", size="sm", w=500, mb="xs"),
                                        dmc.RadioGroup(
                                            id="find-replace-mode",
                                            value="contains",
                                            children=dmc.Stack([dmc.Radio(label=l, value=k, size="sm") for k, l in self.search_modes], gap="xs"),
                                        ),
                                    ],
                                ),
                                dmc.GridCol(
                                    span=6,
                                    children=[
                                        dmc.Text("대소문자 구분", size="sm", w=500, mb="xs"),
                                        dmc.RadioGroup(
                                            id="find-replace-case-sensitive",
                                            value="insensitive",
                                            children=dmc.Stack([dmc.Radio(label=l, value=k, size="sm") for k, l in self.case_sensitive_options], gap="xs"),
                                        ),
                                    ],
                                ),
                            ]
                        ),
                        # 정규식 도움말 패널 (정규식 선택 시만 표시)
                        html.Div(id="regex-help-panel", style={"display": "none"}, children=[dmc.Divider(label="정규식 도움말", labelPosition="center", my="md"), dmc.SimpleGrid(cols=2, spacing="md", children=[dmc.Paper(p="xs", withBorder=True, children=[dmc.Group([dmc.Badge(ex["label"], color="blue", variant="light"), dmc.Code(ex["value"], color="blue")], mb="xs"), dmc.Text(ex["description"], size="sm", c="dimmed")]) for ex in self.regex_examples]), dmc.Center(dmc.Button("정규식 예제 복사", id="regex-example-select", variant="light", size="xs", mt="sm"))]),
                        dmc.Divider(my="md"),
                        dmc.Checkbox(id="find-replace-filtered-only", label="필터링된 데이터에만 적용", description="현재 필터링된 데이터에만 검색 및 치환을 적용합니다", size="sm", checked=False),
                    ],
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    mb="md",
                ),
                # 미리보기 버튼
                dmc.Center(dmc.Button("미리보기", id="find-replace-preview-btn", leftSection=dbpc.Icon(icon="eye-open"), variant="light", mb="md")),
                # 미리보기 결과 영역
                dmc.Card(id="find-replace-preview-card", withBorder=True, shadow="sm", radius="md", p="md", mb="md", style={"display": "none"}, children=[dmc.ScrollArea(id="find-replace-preview-container", h=200, children=[dmc.Text("검색 결과가 여기에 표시됩니다.", size="sm", c="dimmed")])]),
                # 실행 버튼
                dmc.Center(dmc.Button("Replace All", id="find-replace-apply-btn", leftSection=dbpc.Icon(icon="changes"), variant="filled", disabled=True, mb="md")),
                # 도움말 섹션 (폴딩 가능)
                dmc.Accordion(value="", children=[dmc.AccordionItem([dmc.AccordionControl(dmc.Group([dbpc.Icon(icon="help"), dmc.Text("도움말")])), dmc.AccordionPanel([dmc.Timeline(active=5, bulletSize=20, lineWidth=2, children=[dmc.TimelineItem(title="1. 컬럼 선택", children=dmc.Text("검색 및 치환을 실행할 컬럼을 선택하세요 (복수 선택 가능)", size="sm", c="dimmed")), dmc.TimelineItem(title="2. 검색어 입력", children=dmc.Text("찾을 텍스트나 패턴을 입력하세요", size="sm", c="dimmed")), dmc.TimelineItem(title="3. 치환 값 입력", children=dmc.Text("검색된 값을 대체할 텍스트를 입력하세요", size="sm", c="dimmed")), dmc.TimelineItem(title="4. 검색 옵션 설정", children=dmc.Text("검색 방식과 대소문자 구분 여부를 선택하세요", size="sm", c="dimmed")), dmc.TimelineItem(title="5. 미리보기 및 실행", children=dmc.Text("미리보기로 결과를 확인한 후 치환을 실행하세요", size="sm", c="dimmed"))])])], value="help")]),
                # 리셋 저장소
                dcc.Store(id="find-replace-reset-state"),
            ],
            p="lg",
            shadow="sm",
            radius="xs",
            withBorder=True,
        )

    def register_callbacks(self, app):
        """콜백 함수 등록"""

        @app.callback(Output("flex-layout", "model", allow_duplicate=True), Output("toaster", "toasts", allow_duplicate=True), Input("find-replace-btn", "n_clicks"), State("flex-layout", "model"), prevent_initial_call=True)
        def handle_find_replace_button_click(n_clicks, current_model):
            """Find & Replace 버튼 클릭 시 우측 패널에 탭 추가"""
            return handle_tab_button_click(n_clicks, current_model, "find-replace-tab", "Find & Replace")

        @app.callback(Output("find-replace-column-select", "data"), Input("find-replace-btn", "n_clicks"), State("aggrid-table", "columnDefs"), prevent_initial_call=True)
        def update_column_list(n_clicks, columnDefs):
            """Find & Replace 버튼 클릭 시 컬럼 목록 로드"""
            if n_clicks is None or not columnDefs:
                return []

            # 시스템 컬럼 제외하고 문자열 타입 컬럼만 필터링
            column_data = []
            for col in columnDefs:
                if col["field"] not in SYSTEM_COLUMNS and col.get("cellDataType", "text") == "text":
                    column_data.append({"label": col["field"], "value": col["field"]})

            return column_data

        # 정규식 선택 시 도움말 패널 표시
        @app.callback(Output("regex-help-panel", "style"), Input("find-replace-mode", "value"))
        def toggle_regex_help(mode):
            if mode == "regex":
                return {"display": "block"}
            return {"display": "none"}

        # 정규식 예제 선택 모달
        @app.callback(Output("find-replace-search-input", "value"), Input("regex-example-select", "n_clicks"), State("find-replace-search-input", "value"), prevent_initial_call=True)
        def show_regex_examples(n_clicks, current_value):
            if n_clicks:
                # 간단한 예제 선택을 위해 첫 번째 예제 자동 삽입
                # 실제로는 모달을 통해 선택하도록 개선 가능
                return self.regex_examples[0]["value"]
            return current_value

        # 미리보기 버튼 클릭 시 결과 영역 표시
        @app.callback(Output("find-replace-preview-card", "style"), Input("find-replace-preview-btn", "n_clicks"), prevent_initial_call=True)
        def show_preview_card(n_clicks):
            if n_clicks:
                return {"display": "block"}
            return {"display": "none"}

        # 미리보기 업데이트 (기존 코드 개선)
        @app.callback(Output("find-replace-preview-container", "children"), Output("find-replace-apply-btn", "disabled"), Input("find-replace-preview-btn", "n_clicks"), [State("find-replace-column-select", "value"), State("find-replace-search-input", "value"), State("find-replace-value-input", "value"), State("find-replace-mode", "value"), State("find-replace-case-sensitive", "value"), State("find-replace-filtered-only", "checked")], prevent_initial_call=True)
        def update_preview(n_clicks, selected_columns, search_value, replace_value, mode, case_sensitive, filtered_only):
            if not n_clicks or not selected_columns or not search_value:
                return [dmc.Text("미리보기: 필수 정보를 모두 입력해주세요.", size="sm", c="dimmed")], True

            try:
                df = SSDF.dataframe.clone()

                # 필터링된 데이터만 처리
                if filtered_only:
                    from components.grid.dag.SSRM.apply_filter import apply_filters

                    df = apply_filters(df, SSDF.request)

                # 검색 로직 구현
                matched_rows = []
                total_matches = 0

                for col in selected_columns:
                    # 검색 표현식 생성
                    search_expr = self._create_search_expression(col, search_value, mode, case_sensitive)

                    # 검색 수행
                    matches = df.filter(search_expr)
                    col_matches = len(matches)
                    total_matches += col_matches

                    if col_matches > 0:
                        matched_rows.append({"column": col, "count": col_matches, "sample": matches.head(5)[col].to_list()})

                if total_matches == 0:
                    return [dmc.Alert("검색 결과가 없습니다.", title="결과 없음", color="yellow", variant="light", withCloseButton=False, icon=dbpc.Icon(icon="info-sign"))], True

                # 미리보기 결과 생성
                preview_content = [
                    dmc.Text(f"총 {total_matches}개의 일치 항목 발견", w=600, mb="md", size="lg"),
                ]

                for row in matched_rows:
                    preview_content.append(dmc.Card([dmc.Group([dmc.Text(f"컬럼: {row['column']}", w=500), dmc.Badge(f"{row['count']}개", color="blue", variant="light")], mb="xs"), dmc.ScrollArea(dmc.List([dmc.ListItem(dmc.Group([dmc.Badge(item, color="red", variant="light", style={"maxWidth": "200px", "overflow": "hidden", "textOverflow": "ellipsis"}), dbpc.Icon(icon="arrow-right", color="gray"), dmc.Badge(self._apply_replacement(item, search_value, replace_value, mode, case_sensitive), color="green", variant="light", style={"maxWidth": "200px", "overflow": "hidden", "textOverflow": "ellipsis"})])) for item in row["sample"]]), h=100)], withBorder=True, p="sm", mb="xs", shadow="sm"))

                return preview_content, False

            except Exception as e:
                logger.error(f"미리보기 생성 오류: {str(e)}")
                return [dmc.Alert(f"미리보기 생성 중 오류가 발생했습니다: {str(e)}", title="오류 발생", color="red", variant="light", withCloseButton=False, icon=dbpc.Icon(icon="error"))], True

        # Replace All 실행 후 초기화
        @app.callback([Output("toaster", "toasts", allow_duplicate=True), Output("aggrid-table", "columnDefs", allow_duplicate=True), Output("find-replace-search-input", "value", allow_duplicate=True), Output("find-replace-value-input", "value", allow_duplicate=True), Output("find-replace-preview-container", "children", allow_duplicate=True), Output("find-replace-preview-card", "style", allow_duplicate=True), Output("find-replace-apply-btn", "disabled", allow_duplicate=True)], Input("find-replace-apply-btn", "n_clicks"), [State("find-replace-column-select", "value"), State("find-replace-search-input", "value"), State("find-replace-value-input", "value"), State("find-replace-mode", "value"), State("find-replace-case-sensitive", "value"), State("find-replace-filtered-only", "checked")], prevent_initial_call=True)
        def apply_find_replace(n_clicks, selected_columns, search_value, replace_value, mode, case_sensitive, filtered_only):
            if not n_clicks or not selected_columns or not search_value:
                raise exceptions.PreventUpdate

            try:
                df = SSDF.dataframe.clone()
                total_replacements = 0

                # 필터링된 데이터 처리
                if filtered_only:
                    from components.grid.dag.SSRM.apply_filter import apply_filters

                    filtered_df = apply_filters(df, SSDF.request)
                    filtered_ids = filtered_df["uniqid"]

                # 각 컬럼에 대해 치환 수행
                for col in selected_columns:
                    # 치환 표현식 생성
                    replace_expr = self._create_replace_expression(col, search_value, replace_value, mode, case_sensitive)

                    if filtered_only:
                        # 필터링된 행에만 적용
                        df = df.with_columns([pl.when(pl.col("uniqid").is_in(filtered_ids)).then(replace_expr).otherwise(pl.col(col)).alias(col)])
                    else:
                        # 전체 적용
                        df = df.with_columns(replace_expr.alias(col))

                    # 치환된 행 개수 계산
                    if filtered_only:
                        matches = df.filter(pl.col("uniqid").is_in(filtered_ids)).filter(pl.col(col).is_not_null() & (pl.col(col) != ""))
                    else:
                        matches = df.filter(pl.col(col).is_not_null() & (pl.col(col) != ""))

                    total_replacements += len(matches)

                # 데이터프레임 업데이트
                SSDF.dataframe = df
                updated_columnDefs = generate_column_definitions(df)

                # 초기화 - 검색/치환 값만 초기화, 컬럼 선택은 유지
                return [dbpc.Toast(message=f"{total_replacements}개의 항목이 성공적으로 치환되었습니다.", intent="success", icon="endorsed", timeout=3000)], updated_columnDefs, "", "", [dmc.Text("검색 결과가 여기에 표시됩니다.", size="sm", c="dimmed")], {"display": "none"}, True

            except Exception as e:
                logger.error(f"치환 처리 오류: {str(e)}")
                return [dbpc.Toast(message=f"치환 처리 오류: {str(e)}", intent="danger", icon="error")], no_update, no_update, no_update, no_update, no_update, no_update

        # 나머지 기존 콜백들...
        # (handle_find_replace_button_click, update_column_list 등은 동일)

    def _create_search_expression(self, column, search_value, mode, case_sensitive):
        """검색 표현식 생성"""
        col_expr = pl.col(column).cast(pl.Utf8)

        if case_sensitive == "insensitive":
            col_expr = col_expr.str.to_lowercase()
            search_value = search_value.lower()

        if mode == "exact":
            return col_expr == search_value
        elif mode == "contains":
            return col_expr.str.contains(search_value)
        elif mode == "regex":
            return col_expr.str.contains(search_value, literal=False)
        else:
            raise ValueError(f"지원하지 않는 검색 모드: {mode}")

    def _create_replace_expression(self, column, search_value, replace_value, mode, case_sensitive):
        """치환 표현식 생성"""
        col_expr = pl.col(column).cast(pl.Utf8)

        if mode == "exact":
            if case_sensitive == "sensitive":
                return pl.when(col_expr == search_value).then(replace_value).otherwise(col_expr)
            else:
                return pl.when(col_expr.str.to_lowercase() == search_value.lower()).then(replace_value).otherwise(col_expr)
        elif mode == "contains":
            if case_sensitive == "sensitive":
                return col_expr.str.replace_all(search_value, replace_value, literal=True)
            else:
                # 대소문자 구분 없는 치환을 위해 정규식 사용
                escaped_search = re.escape(search_value)
                return col_expr.str.replace_all(r"(?i)" + escaped_search, replace_value, literal=False)
        elif mode == "regex":
            return col_expr.str.replace_all(search_value, replace_value, literal=False)
        else:
            raise ValueError(f"지원하지 않는 검색 모드: {mode}")

    def _apply_replacement(self, value, search_value, replace_value, mode, case_sensitive):
        """샘플 치환 미리보기를 위한 함수"""
        if mode == "exact":
            if case_sensitive == "sensitive":
                return replace_value if value == search_value else value
            else:
                return replace_value if value.lower() == search_value.lower() else value
        elif mode == "contains":
            if case_sensitive == "sensitive":
                return value.replace(search_value, replace_value)
            else:
                return re.sub(re.escape(search_value), replace_value, value, flags=re.IGNORECASE)
        elif mode == "regex":
            return re.sub(search_value, replace_value, value)
        return value
