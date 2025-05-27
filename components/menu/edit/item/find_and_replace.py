import re
import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, Patch, html, no_update, exceptions, ctx, dcc, ALL
from typing import List, Dict, Any, Optional

from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions, SYSTEM_COLUMNS
from components.menu.edit.common_utils import handle_tab_button_click, FormComponents


class FindAndReplace:
    def __init__(self):

        self.form = FormComponents()
        
        # 검색 방식 옵션
        self.search_modes = [
            {"value": "exact", "label": "정확히 일치"},
            {"value": "contains", "label": "포함"},
            {"value": "starts_with", "label": "시작하는"},
            {"value": "ends_with", "label": "끝나는"},
            {"value": "regex", "label": "정규식"},
            {"value": "empty", "label": "빈 값"},
            {"value": "not_empty", "label": "빈 값이 아닌"},
        ]
        

    def button_layout(self):
        return dbpc.Button("Find & Replace", id="find-replace-btn", icon="search-template", minimal=True, outlined=True)
    
    def tab_layout(self):
        return dmc.Stack([
           
            # Main Configuration
            self.form.create_section_card(
                title="Find & Replace",
                icon="search-template",
                description="고급 검색 및 치환 옵션을 설정합니다.",
                children=[
                    # Column Selection
                    dmc.MultiSelect(
                        id="find-replace-column-select",
                        label="대상 컬럼",
                        description="검색할 컬럼을 선택하세요 (복수 선택 가능)",
                        placeholder="컬럼 선택...",
                        data=[],
                        searchable=True,
                        clearable=True,
                        leftSection=dbpc.Icon(icon="th"),
                        mb="md",
                    ),
                    
                    # Search and Replace Values
                    dmc.Grid([
                        dmc.GridCol([
                            dmc.TextInput(
                                id="find-replace-search-input",
                                label="찾을 값",
                                description="검색할 텍스트나 패턴",
                                placeholder="검색어 입력...",
                                leftSection=dbpc.Icon(icon="search"),
                            )
                        ], span=6),
                        dmc.GridCol([
                            dmc.TextInput(
                                id="find-replace-value-input",
                                label="바꿀 값",
                                description="대체할 텍스트",
                                placeholder="대체값 입력...",
                                leftSection=dbpc.Icon(icon="edit"),
                            )
                        ], span=6),
                    ], mb="md"),
                    
                    # Search Options
                    dmc.Grid([
                        dmc.GridCol([
                            dmc.Select(
                                id="find-replace-mode",
                                label="검색 방식",
                                data=self.search_modes,
                                value="contains",
                                leftSection=dbpc.Icon(icon="search"),
                            )
                        ], span=6),
                        dmc.GridCol([
                            dmc.Switch(
                                id="find-replace-case-sensitive",
                                label="대소문자 구분",
                                description="대소문자를 구분하여 검색",
                                size="sm",
                                mt="lg",
                            )
                        ], span=6),
                    ], mb="md"),


                    dmc.Grid([
                        dmc.GridCol([
                            dmc.RadioGroup(
                                id="find-replace-replace-mode",
                                label="치환 방식",
                                description="값을 어떻게 변경할지 선택하세요",
                                value="full",
                                children=[
                                    dmc.Radio(
                                        label="전체 값 변경",
                                        description="셀의 전체 값을 바꿀 값으로 변경",
                                        value="full"
                                    ),
                                    dmc.Radio(
                                        label="일치 부분만 변경", 
                                        description="찾은 부분만 바꿀 값으로 변경 (나머지는 유지)",
                                        value="partial"
                                    ),
                                ],
                                size="sm",
                            )
                        ], span=12),
                    ], mb="md"),

                    # Advanced Options
                    dmc.Accordion([
                        dmc.AccordionItem([
                            dmc.AccordionControl(
                                dmc.Group([
                                    dbpc.Icon(icon="advanced"),
                                    dmc.Text("고급 옵션")
                                ])
                            ),
                            dmc.AccordionPanel([
                                dmc.Checkbox(
                                    id="find-replace-filtered-only",
                                    label="필터링된 데이터에만 적용",
                                    description="현재 적용된 필터에 포함된 행만 처리",
                                    checked=True,
                                    mb="sm",
                                ),
                            ])
                        ], value="advanced")
                    ]),
                ]
            ),
            
            # Live Preview Section
            dmc.Card([
                dmc.Group([
                    dbpc.Icon(icon="eye-open"),
                    dmc.Text("실시간 미리보기", fw=600),
                    dmc.Badge(
                        id="find-replace-match-count",
                        children="0개 일치",
                        color="blue",
                        variant="light",
                    )
                ], mb="sm"),
                dmc.ScrollArea(
                    id="find-replace-preview-container",
                    h=200,
                    children=[
                        dmc.Text("설정을 변경하면 미리보기가 표시됩니다.", 
                               size="sm", c="dimmed", ta="center", mt="xl")
                    ]
                )
            ], withBorder=True, shadow="sm", mb="md"),
            
            # Action Buttons
            dmc.Group([
                dmc.Button(
                    "미리보기 업데이트",
                    id="find-replace-preview-btn",
                    leftSection=dbpc.Icon(icon="refresh"),
                    variant="light",
                    color="blue",
                ),
                dmc.Button(
                    "모두 바꾸기",
                    id="find-replace-apply-btn",
                    leftSection=dbpc.Icon(icon="changes"),
                    variant="filled",
                    color="blue",
                    disabled=True,
                ),
            ], justify="center", mb="md"),
            # Help Section
            self.form.create_help_section([
                "컬럼을 선택하고 찾을 값과 바꿀 값을 입력",
                "검색 방식을 선택 (정확히 일치, 포함, 정규식 등)",
                "치환 방식 선택:",
                "  • 전체 값 변경: 조건에 맞는 셀 전체를 바꿀 값으로 변경",
                "  • 일치 부분만 변경: 찾은 부분만 바꾸고 나머지는 유지",
                "필터링된 데이터에만 적용 옵션 활용",
                "미리보기에서 결과를 확인한 후 적용",
                "예시: 'x_edge.xlog2.xmn0'에서 'xmn'을 'NMOS'로 부분 변경하면 'x_edge.xlog2.NMOS0'이 됨"
            ])

        ], gap="md")



    def register_callbacks(self, app):
        """콜백 함수 등록"""

        @app.callback(Output("flex-layout", "model", allow_duplicate=True), Output("toaster", "toasts", allow_duplicate=True), Input("find-replace-btn", "n_clicks"), State("flex-layout", "model"), prevent_initial_call=True)
        def handle_find_replace_button_click(n_clicks, current_model):
            """Find & Replace 버튼 클릭 시 우측 패널에 탭 추가"""
            return handle_tab_button_click(n_clicks, current_model, "find-replace-tab", "Find & Replace")

        @app.callback(
            Output("find-replace-column-select", "data"),
            Input("find-replace-btn", "n_clicks"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True,
        )
        def update_column_list(n_clicks, columnDefs):
            """컬럼 목록 업데이트"""
            if not columnDefs:
                return []

            # 시스템 컬럼 제외하고 텍스트 타입 컬럼 필터링
            column_data = []
            for col in columnDefs:
                if col["field"] not in SYSTEM_COLUMNS:
                    column_data.append({"label": col["field"], "value": col["field"]})

            return column_data


        @app.callback(
            [
                Output("find-replace-preview-container", "children"),
                Output("find-replace-match-count", "children"),
                Output("find-replace-apply-btn", "disabled"),
            ],
            [
                Input("find-replace-preview-btn", "n_clicks"),
                Input("find-replace-search-input", "value"),
                Input("find-replace-value-input", "value"),
                Input("find-replace-mode", "value"),
                Input("find-replace-case-sensitive", "checked"),
                Input("find-replace-replace-mode", "value"),
            ],
            [
                State("find-replace-column-select", "value"),
                State("find-replace-filtered-only", "checked"),
            ],
            prevent_initial_call=True,
        )
        def update_preview(preview_clicks, search_value, replace_value, mode, case_sensitive, 
                         replace_mode, selected_columns, filtered_only):
            """미리보기 업데이트"""
            if not selected_columns:
                return [
                    dmc.Alert(
                        "컬럼을 선택해주세요",
                        title="선택 필요",
                        color="yellow",
                        icon=dbpc.Icon(icon="warning-sign"),
                    )
                ], "컬럼 미선택", True

            try:
                df = SSDF.dataframe.clone()
                
                # 필터링된 데이터만 처리
                if filtered_only:
                    from components.grid.dag.SSRM.apply_filter import apply_filters
                    df = apply_filters(df, SSDF.request)

                # 검색 및 미리보기 로직
                preview_results = []
                total_matches = 0

                for col in selected_columns:
                    matches = self._find_matches(df, col, search_value, mode, case_sensitive)
                    match_count = len(matches)
                    total_matches += match_count
                    
                    if match_count > 0:
                        # 샘플 결과 (최대 5개)
                        sample_matches = matches.head(5)
                        preview_results.append({
                            "column": col,
                            "count": match_count,
                            "samples": sample_matches.to_dicts()
                        })

                if total_matches == 0:
                    return [
                        dmc.Alert(
                            "검색 조건에 일치하는 항목이 없습니다.",
                            title="결과 없음",
                            color="blue",
                            icon=dbpc.Icon(icon="info-sign"),
                        )
                    ], "0개 일치", True

                # 미리보기 테이블 생성
                preview_content = self._create_preview_table(
                    preview_results, search_value, replace_value, mode, case_sensitive, replace_mode
                )
                
                return preview_content, f"{total_matches:,}개 일치", False

            except Exception as e:
                logger.error(f"미리보기 생성 오류: {str(e)}")
                return [
                    dmc.Alert(
                        f"미리보기 생성 중 오류가 발생했습니다: {str(e)}",
                        title="오류",
                        color="red",
                        icon=dbpc.Icon(icon="error"),
                    )
                ], "오류", True

        # Replace All 실행
        @app.callback(
            [
                Output("toaster", "toasts", allow_duplicate=True),
                Output("aggrid-table", "columnDefs", allow_duplicate=True),
                Output("find-replace-search-input", "value", allow_duplicate=True),
                Output("find-replace-value-input", "value", allow_duplicate=True),
            ],
            Input("find-replace-apply-btn", "n_clicks"),
            [
                State("find-replace-column-select", "value"),
                State("find-replace-search-input", "value"),
                State("find-replace-value-input", "value"),
                State("find-replace-mode", "value"),
                State("find-replace-case-sensitive", "checked"),
                State("find-replace-replace-mode", "value"),
                State("find-replace-filtered-only", "checked"),
            ],
            prevent_initial_call=True,
        )
        def apply_find_replace(n_clicks, selected_columns, search_value, replace_value, 
                             mode, case_sensitive, replace_mode, filtered_only):
            """Find & Replace 실행"""
            if not n_clicks or not selected_columns:
                raise exceptions.PreventUpdate

            try:
                df = SSDF.dataframe.clone()
                total_replacements = 0

                # 필터링된 데이터 처리
                filtered_ids = None
                if filtered_only:
                    from components.grid.dag.SSRM.apply_filter import apply_filters
                    filtered_df = apply_filters(df, SSDF.request)
                    if "uniqid" in filtered_df.columns:
                        filtered_ids = filtered_df["uniqid"]

                # 각 컬럼에 대해 치환 수행
                for col in selected_columns:
                    replacement_count = self._apply_replacement(
                        df, col, search_value, replace_value, mode, 
                        case_sensitive, replace_mode, filtered_ids
                    )
                    total_replacements += replacement_count

                # 데이터프레임 업데이트
                SSDF.dataframe = df
                updated_columnDefs = generate_column_definitions(df)

                # 성공 메시지
                replace_mode_text = "전체 값" if replace_mode == "full" else "일치 부분만"
                toast_message = f"{total_replacements:,}개 항목이 성공적으로 변경되었습니다. ({replace_mode_text})"
                
                return (
                    [dbpc.Toast(
                        message=toast_message,
                        intent="success",
                        icon="endorsed",
                        timeout=3000,
                    )],
                    updated_columnDefs,
                    "",  # 검색값 초기화
                    "",  # 대체값 초기화
                )

            except Exception as e:
                logger.error(f"Find & Replace 처리 오류: {str(e)}")
                return (
                    [dbpc.Toast(
                        message=f"처리 중 오류가 발생했습니다: {str(e)}",
                        intent="danger",
                        icon="error",
                    )],
                    no_update,
                    no_update,
                    no_update,
                )
            
    def _find_matches(self, df: pl.DataFrame, column: str, search_value: str, 
                     mode: str, case_sensitive: bool) -> pl.DataFrame:
        """검색 조건에 맞는 행들을 찾아 반환"""
        col_expr = pl.col(column).cast(pl.Utf8)
        
        # 대소문자 구분 처리
        if not case_sensitive:
            col_expr = col_expr.str.to_lowercase()
            if search_value:
                search_value = search_value.lower()

        # 검색 모드별 필터 조건
        if mode == "exact":
            condition = col_expr == search_value
        elif mode == "contains":
            condition = col_expr.str.contains(search_value, literal=True)
        elif mode == "starts_with":
            condition = col_expr.str.starts_with(search_value)
        elif mode == "ends_with":
            condition = col_expr.str.ends_with(search_value)
        elif mode == "regex":
            condition = col_expr.str.contains(search_value, literal=False)
        elif mode == "empty":
            condition = (pl.col(column).is_null()) | (pl.col(column) == "")
        elif mode == "not_empty":
            condition = (pl.col(column).is_not_null()) & (pl.col(column) != "")
        else:
            condition = col_expr.str.contains(search_value, literal=True)

        return df.filter(condition)

    def _create_preview_table(self, preview_results: List[Dict], search_value: str, 
                            replace_value: str, mode: str, case_sensitive: bool, 
                            replace_mode: str) -> List[Any]:
        """미리보기 테이블 생성"""
        if not preview_results:
            return []

        content = []
        
        for result in preview_results:
            # 컬럼별 섹션
            content.append(
                dmc.Card([
                    dmc.Group([
                        dmc.Text(f"컬럼: {result['column']}", fw=600),
                        dmc.Badge(f"{result['count']:,}개", color="blue", variant="light"),
                    ], justify="apart"),
                    
                    # 샘플 테이블
                    dmc.Table([
                        dmc.TableThead([
                            dmc.TableTr([
                                dmc.TableTh("현재 값"),
                                dmc.TableTh("→"),
                                dmc.TableTh("변경 후"),
                            ])
                        ]),
                        dmc.TableTbody([
                            dmc.TableTr([
                                dmc.TableTd(
                                    dmc.Code(str(sample.get(result['column'], '')), 
                                        color="red"),
                                    style={"maxWidth": "200px", "overflow": "hidden"}
                                ),
                                dmc.TableTd("→", ta="center"),
                                dmc.TableTd(
                                    dmc.Code(
                                        self._preview_replacement(
                                            str(sample.get(result['column'], '')),
                                            search_value, replace_value, mode, 
                                            case_sensitive, replace_mode
                                        ), 
                                        color="green"
                                    ),
                                    style={"maxWidth": "200px", "overflow": "hidden"}
                                ),
                            ])
                            for sample in result['samples'][:3]  # 최대 3개만 표시
                        ])
                    ], striped=True, withTableBorder=True),
                    
                    # 더 많은 항목이 있는 경우 표시
                    dmc.Text(
                        f"... 외 {result['count'] - len(result['samples'])}개" 
                        if result['count'] > len(result['samples']) else "",
                        size="xs", c="dimmed", ta="center", mt="xs"
                    ) if result['count'] > len(result['samples']) else None,
                    
                ], withBorder=True, p="sm", mb="sm")
            )
        
        return content


    def _apply_replacement(self, df: pl.DataFrame, column: str, search_value: str, 
                         replace_value: str, mode: str, case_sensitive: bool, 
                         replace_mode: str, filtered_ids: Optional[pl.Series] = None) -> int:
        """실제 치환 수행 및 변경된 행 수 반환"""
        
        # 치환 전 상태 저장 (변경 개수 계산용)
        original_values = df[column].clone()
        
        # 치환 표현식 생성
        replace_expr = self._create_replace_expression(
            column, search_value, replace_value, mode, case_sensitive, replace_mode
        )
        
        # 필터링된 행에만 적용
        if filtered_ids is not None:
            replace_expr = pl.when(
                pl.col("uniqid").is_in(filtered_ids)
            ).then(replace_expr).otherwise(pl.col(column))
        
        # 치환 적용 - with_columns 사용
        SSDF.dataframe = SSDF.dataframe.with_columns(replace_expr.alias(column))
        
        # 변경된 행 수 계산
        changed_count = (original_values != SSDF.dataframe[column]).sum()
        return changed_count




    def _create_replace_expression(self, column: str, search_value: str, 
                                replace_value: str, mode: str, 
                                case_sensitive: bool, replace_mode: str) -> pl.Expr:
        """치환 표현식 생성"""
        col_expr = pl.col(column).cast(pl.Utf8)
        
        # 전체 값 변경 모드
        if replace_mode == "full":
            if mode == "exact":
                if case_sensitive:
                    return pl.when(col_expr == search_value).then(replace_value).otherwise(col_expr)
                else:
                    return pl.when(
                        col_expr.str.to_lowercase() == search_value.lower()
                    ).then(replace_value).otherwise(col_expr)
            
            elif mode in ["contains", "starts_with", "ends_with", "regex"]:
                # 조건에 맞으면 전체를 replace_value로 변경
                condition = self._create_search_condition(col_expr, search_value, mode, case_sensitive)
                return pl.when(condition).then(replace_value).otherwise(col_expr)
            
            elif mode == "empty":
                return pl.when(
                    (pl.col(column).is_null()) | (pl.col(column) == "")
                ).then(replace_value).otherwise(col_expr)
                
            elif mode == "not_empty":
                return pl.when(
                    (pl.col(column).is_not_null()) & (pl.col(column) != "")
                ).then(replace_value).otherwise(col_expr)
        
        # 부분 변경 모드 (일치하는 부분만 변경)
        elif replace_mode == "partial":
            if mode == "exact":
                # 정확 일치는 전체 변경과 동일
                if case_sensitive:
                    return pl.when(col_expr == search_value).then(replace_value).otherwise(col_expr)
                else:
                    return pl.when(
                        col_expr.str.to_lowercase() == search_value.lower()
                    ).then(replace_value).otherwise(col_expr)
                    
            elif mode == "contains":
                if case_sensitive:
                    return col_expr.str.replace_all(search_value, replace_value, literal=True)
                else:
                    # 대소문자 구분 없는 치환을 위해 정규식 사용
                    pattern = f"(?i){re.escape(search_value)}"
                    return col_expr.str.replace_all(pattern, replace_value, literal=False)
                    
            elif mode == "starts_with":
                pattern = f"^{re.escape(search_value)}"
                if not case_sensitive:
                    pattern = f"(?i){pattern}"
                return col_expr.str.replace_all(pattern, replace_value, literal=False)
                
            elif mode == "ends_with":
                pattern = f"{re.escape(search_value)}$"
                if not case_sensitive:
                    pattern = f"(?i){pattern}"
                return col_expr.str.replace_all(pattern, replace_value, literal=False)
                
            elif mode == "regex":
                return col_expr.str.replace_all(search_value, replace_value, literal=False)
                
            elif mode == "empty":
                return pl.when(
                    (pl.col(column).is_null()) | (pl.col(column) == "")
                ).then(replace_value).otherwise(col_expr)
                
            elif mode == "not_empty":
                return pl.when(
                    (pl.col(column).is_not_null()) & (pl.col(column) != "")
                ).then(replace_value).otherwise(col_expr)
        
        # 기본값
        return col_expr.str.replace_all(search_value, replace_value, literal=True)
    

    def _create_search_condition(self, col_expr: pl.Expr, search_value: str, 
                            mode: str, case_sensitive: bool) -> pl.Expr:
        """검색 조건 생성"""
        if not case_sensitive:
            col_expr = col_expr.str.to_lowercase()
            if search_value:
                search_value = search_value.lower()

        if mode == "contains":
            return col_expr.str.contains(search_value, literal=True)
        elif mode == "starts_with":
            return col_expr.str.starts_with(search_value)
        elif mode == "ends_with":
            return col_expr.str.ends_with(search_value)
        elif mode == "regex":
            return col_expr.str.contains(search_value, literal=False)
        else:
            return col_expr.str.contains(search_value, literal=True)

    def _preview_replacement(self, original_value: str, search_value: str, 
                        replace_value: str, mode: str, case_sensitive: bool, 
                        replace_mode: str) -> str:
        """미리보기용 치환 결과 생성"""
        if not original_value or not search_value:
            return original_value
        
        try:
            # 전체 값 변경
            if replace_mode == "full":
                if mode == "exact":
                    if case_sensitive:
                        return replace_value if original_value == search_value else original_value
                    else:
                        return replace_value if original_value.lower() == search_value.lower() else original_value
                elif mode in ["contains", "starts_with", "ends_with"]:
                    # 조건에 맞으면 전체를 replace_value로 변경
                    if self._matches_condition(original_value, search_value, mode, case_sensitive):
                        return replace_value
                    return original_value
                elif mode == "regex":
                    if re.search(search_value, original_value, re.IGNORECASE if not case_sensitive else 0):
                        return replace_value
                    return original_value
            
            # 부분 변경
            elif replace_mode == "partial":
                if mode == "exact":
                    if case_sensitive:
                        return replace_value if original_value == search_value else original_value
                    else:
                        return replace_value if original_value.lower() == search_value.lower() else original_value
                elif mode == "contains":
                    if case_sensitive:
                        return original_value.replace(search_value, replace_value)
                    else:
                        return re.sub(re.escape(search_value), replace_value, original_value, flags=re.IGNORECASE)
                elif mode == "starts_with":
                    pattern = f"^{re.escape(search_value)}"
                    flags = re.IGNORECASE if not case_sensitive else 0
                    return re.sub(pattern, replace_value, original_value, flags=flags)
                elif mode == "ends_with":
                    pattern = f"{re.escape(search_value)}$"
                    flags = re.IGNORECASE if not case_sensitive else 0
                    return re.sub(pattern, replace_value, original_value, flags=flags)
                elif mode == "regex":
                    flags = re.IGNORECASE if not case_sensitive else 0
                    return re.sub(search_value, replace_value, original_value, flags=flags)
            
            return original_value
            
        except Exception as e:
            logger.error(f"미리보기 치환 오류: {str(e)}")
            return original_value

    def _matches_condition(self, value: str, search_value: str, mode: str, case_sensitive: bool) -> bool:
        """값이 검색 조건에 맞는지 확인"""
        if not case_sensitive:
            value = value.lower()
            search_value = search_value.lower()
        
        if mode == "contains":
            return search_value in value
        elif mode == "starts_with":
            return value.startswith(search_value)
        elif mode == "ends_with":
            return value.endswith(search_value)
        elif mode == "regex":
            try:
                flags = re.IGNORECASE if not case_sensitive else 0
                return bool(re.search(search_value, value, flags))
            except:
                return False
        return False