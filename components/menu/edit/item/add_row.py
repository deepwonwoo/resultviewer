import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
import dash_ag_grid as dag

from dash import Output, Input, State, Patch, html, no_update, exceptions, ctx, ALL
from utils.data_processing import displaying_df
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions
from components.menu.edit.utils import find_tab_in_layout, handle_tab_button_click
from components.grid.dag.server_side_operations import extract_rows_from_data

class AddRow:

    def __init__(self):
        pass
        
    def button_layout(self):
        return dbpc.Button(
            "Insert Row", 
            id="add-row-btn", 
            icon="add-row-bottom", 
            minimal=True, 
            outlined=True
        )

    def tab_layout(self):
        return dmc.Paper(
            children=[
                dmc.Group([
                    dbpc.EntityTitle(
                        title="Add Row", 
                        heading="H5", 
                        icon="add-row-top"
                    )
                ], grow=True),
                dmc.Space(h=10),
                
                # 행 추가 방식 선택
                dmc.SegmentedControl(
                    id="add-row-mode",
                    data=[
                        {"label": "상단에 추가", "value": "top"},
                        {"label": "하단에 추가", "value": "bottom"},
                    ],
                    value="bottom",
                    fullWidth=True,
                ),
                
                dmc.Space(h=20),
                
                # 추가할 행 수 입력
                dmc.NumberInput(
                    id="add-row-count",
                    label="추가할 행 수",
                    description="최대 100개까지 한 번에 추가할 수 있습니다",
                    value=1,
                    min=1,
                    max=100,
                    step=1
                ),
                
                dmc.Space(h=20),
                
                # 컬럼별 기본값 설정
                dmc.Text("컬럼별 기본값 설정", w=500, size="sm"),
                dmc.Text("(비워두면 빈 값으로 설정됩니다)", c="dimmed", size="xs", mb=10),
                
                # 동적으로 생성될 필드 컨테이너
                html.Div(id="add-row-fields-container"),
                
                dmc.Space(h=20),
                
                # 추가 버튼
                dmc.Group([
                    dbpc.Button(
                        "Add Row", 
                        id="add-row-apply-btn", 
                        outlined=True,
                        icon="add",
                        intent="primary"
                    ),
                ], justify="center"),
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
            Input("add-row-btn", "n_clicks"),
            State("flex-layout", "model"),
            prevent_initial_call=True
        )
        def handle_add_row_button_click(n_clicks, current_model):
            """Add Row 버튼 클릭 시 우측 패널에 탭 추가"""
            return handle_tab_button_click(n_clicks, current_model, "row-add-tab", "Add Row")

        @app.callback(
            Output("add-row-fields-container", "children"),
            Input("add-row-btn", "n_clicks"),
            State("aggrid-table", "columnDefs"),
            prevent_initial_call=True
        )
        def create_column_input_fields(n_clicks, columnDefs):
            """컬럼별 입력 필드 생성 - 데이터 타입을 정확히 반영"""
            if not columnDefs:
                return []
                
            # 보호할 컬럼 리스트 (시스템 컬럼)
            protected_columns = ["uniqid", "group", "childCount"]
            
            # SSDF에서 실제 데이터프레임의 데이터 타입 정보 가져오기
            df = SSDF.dataframe
            
            # 입력 필드 생성
            input_fields = []
            for col in columnDefs:
                field = col.get("field")
                if field and field not in protected_columns:
                    # 실제 데이터프레임에서 해당 컬럼의 데이터 타입 확인
                    field_dtype = None
                    try:
                        if field in df.columns:
                            field_dtype = df[field].dtype
                    except Exception as e:
                        logger.error(f"필드 {field} 데이터 타입 확인 실패: {e}")
                    
                    # 데이터 타입에 따라 적절한 입력 필드 제공
                    if field_dtype in [pl.Float64, pl.Float32]:
                        # 실수형 필드
                        input_field = dmc.NumberInput(
                            id={"type": "add-row-field", "field": field},
                            label=f"{field} (Float)",
                            description="실수 값을 입력하세요",
                            step=0.1,
                            style={"marginBottom": "8px"}
                        )
                    elif field_dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                        # 정수형 필드
                        input_field = dmc.NumberInput(
                            id={"type": "add-row-field", "field": field},
                            label=f"{field} (Integer)",
                            description="정수 값을 입력하세요",
                            step=1,
                            style={"marginBottom": "8px"}
                        )
                    elif field_dtype == pl.Boolean:
                        # 불리언 필드
                        input_field = dmc.Switch(
                            id={"type": "add-row-field", "field": field},
                            label=f"{field} (Boolean)",
                            description="On/Off 값을 선택하세요",
                            style={"marginBottom": "8px"}
                        )
                    elif field_dtype in [pl.Categorical, pl.Enum]:
                        # 카테고리형 필드
                        unique_values = []
                        try:
                            if not df.is_empty():
                                # 고유값 가져오기 (최대 20개)
                                unique_values = df[field].unique().to_list()[:20]
                                # None 값 제거
                                unique_values = [v for v in unique_values if v is not None]
                        except Exception as e:
                            logger.error(f"필드 {field} 고유값 가져오기 실패: {e}")
                        
                        if unique_values:
                            # 고유값이 있는 경우 Select 제공
                            input_field = dmc.Select(
                                id={"type": "add-row-field", "field": field},
                                label=f"{field} (Category)",
                                description="값을 선택하거나 직접 입력하세요",
                                data=[{"value": str(v), "label": str(v)} for v in unique_values],
                                searchable=True,
                                creatable=True,
                                style={"marginBottom": "8px"}
                            )
                        else:
                            # 고유값이 없는 경우 일반 텍스트 입력 제공
                            input_field = dmc.TextInput(
                                id={"type": "add-row-field", "field": field},
                                label=f"{field} (Category)",
                                description="카테고리 값을 입력하세요",
                                style={"marginBottom": "8px"}
                            )
                    else:
                        # 기본 텍스트 필드 (String 등)
                        input_field = dmc.TextInput(
                            id={"type": "add-row-field", "field": field},
                            label=f"{field} (Text)",
                            description="문자열 값을 입력하세요",
                            style={"marginBottom": "8px"}
                        )
                    
                    input_fields.append(input_field)
            
            return input_fields


        @app.callback(
            Output("toaster", "toasts", allow_duplicate=True),
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Input("add-row-apply-btn", "n_clicks"),
            State("add-row-mode", "value"),
            State("add-row-count", "value"),
            State("aggrid-table", "columnDefs"),
            State({"type": "add-row-field", "field": ALL}, "id"),
            State({"type": "add-row-field", "field": ALL}, "value"),
            prevent_initial_call=True
        )
        def handle_add_row_submission(n_clicks, mode, row_count, columnDefs, field_ids, field_values):
            """행 추가 실행 - 데이터 타입 처리 강화"""
            if not n_clicks:
                raise exceptions.PreventUpdate
                
            try:
                # 행 수 검증
                if not row_count or row_count < 1:
                    return ([dbpc.Toast(
                        message=f"추가할 행 수가 유효하지 않습니다.",
                        intent="warning",
                        icon="warning-sign"
                    )], no_update)
                
                # 보호할 컬럼 리스트 (시스템 컬럼)
                protected_columns = ["uniqid", "group", "childCount"]
                
                # 원본 데이터프레임 
                df = SSDF.dataframe
                original_row_count = len(df)
                
                # 컬럼 필드 목록 (uniqid 제외)
                fields = [col for col in df.columns if col not in protected_columns]
                
                # uniqid 컬럼 제거한 데이터프레임 생성
                df_without_uniqid = df.drop("uniqid") if "uniqid" in df.columns else df
                
                # 필드 ID에서 필드 이름 추출 및 값 매핑
                field_values_dict = {}
                for idx, field_id in enumerate(field_ids):
                    field_name = field_id["field"]
                    field_value = field_values[idx]
                    field_values_dict[field_name] = field_value
                
                # 새 행 생성
                new_rows = {}
                for field in fields:
                    # 현재 필드의 데이터 타입
                    field_dtype = None
                    try:
                        field_dtype = df[field].dtype
                    except Exception as e:
                        logger.error(f"필드 {field} 데이터 타입 접근 실패: {e}")
                        continue
                        
                    # 사용자가 입력한 기본값이 있으면 사용, 없으면 빈 값
                    user_value = field_values_dict.get(field)
                    
                    try:
                        # 데이터 타입에 따라 적절한 값으로 변환
                        if field_dtype in [pl.Float64, pl.Float32]:
                            # 실수형 처리
                            if user_value is not None and user_value != "":
                                try:
                                    value = float(user_value)
                                except:
                                    value = 0.0
                            else:
                                value = 0.0
                                
                        elif field_dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                            # 정수형 처리
                            if user_value is not None and user_value != "":
                                try:
                                    value = int(user_value)
                                except:
                                    value = 0
                            else:
                                value = 0
                                
                        elif field_dtype == pl.Boolean:
                            # 불리언 처리
                            if user_value is not None:
                                if isinstance(user_value, bool):
                                    value = user_value
                                elif isinstance(user_value, str):
                                    value = user_value.lower() in ["true", "1", "t", "yes", "y"]
                                elif isinstance(user_value, (int, float)):
                                    value = bool(user_value)
                                else:
                                    value = False
                            else:
                                value = False
                                
                        elif field_dtype == pl.Date:
                            # 날짜 처리
                            if user_value:
                                try:
                                    from datetime import datetime, date
                                    if isinstance(user_value, (date, datetime)):
                                        value = user_value
                                    elif isinstance(user_value, str):
                                        # ISO 형식(YYYY-MM-DD) 파싱 시도
                                        value = date.fromisoformat(user_value)
                                    else:
                                        # 기본값으로 오늘 날짜
                                        value = date.today()
                                except:
                                    # 파싱 실패 시 기본값으로 오늘 날짜
                                    value = date.today()
                            else:
                                value = None
                                
                        elif field_dtype == pl.Datetime:
                            # 날짜/시간 처리
                            if user_value:
                                try:
                                    from datetime import datetime
                                    if isinstance(user_value, datetime):
                                        value = user_value
                                    elif isinstance(user_value, str):
                                        # ISO 형식 파싱 시도
                                        value = datetime.fromisoformat(user_value.replace('Z', '+00:00'))
                                    else:
                                        # 기본값으로 현재 시간
                                        value = datetime.now()
                                except:
                                    # 파싱 실패 시 기본값으로 현재 시간
                                    value = datetime.now()
                            else:
                                value = None
                                
                        elif field_dtype in [pl.Categorical, pl.Enum]:
                            # 카테고리형 처리
                            if user_value is not None and user_value != "":
                                value = str(user_value)
                            else:
                                value = ""
                                
                        elif field_dtype == pl.List:
                            # 리스트 타입 처리
                            if user_value is not None and user_value != "":
                                try:
                                    # 문자열을 리스트로 파싱 시도
                                    import json
                                    if isinstance(user_value, str):
                                        if user_value.startswith('[') and user_value.endswith(']'):
                                            value = json.loads(user_value)
                                        else:
                                            value = [user_value]
                                    elif isinstance(user_value, list):
                                        value = user_value
                                    else:
                                        value = [user_value]
                                except:
                                    value = []
                            else:
                                value = []
                                
                        else:
                            # 기타 타입 (문자열로 처리)
                            if user_value is not None:
                                value = str(user_value)
                            else:
                                value = ""
                        
                        # 선택한 행 수만큼 값 복제
                        new_rows[field] = [value] * row_count
                        
                    except Exception as e:
                        logger.error(f"필드 {field} 값 변환 실패: {e}")
                        # 에러 발생 시 기본값 설정
                        if field_dtype in [pl.Float64, pl.Float32]:
                            new_rows[field] = [0.0] * row_count
                        elif field_dtype in [pl.Int64, pl.Int32, pl.UInt32, pl.UInt64]:
                            new_rows[field] = [0] * row_count
                        elif field_dtype == pl.Boolean:
                            new_rows[field] = [False] * row_count
                        else:
                            new_rows[field] = [""] * row_count
                
                try:
                    # 새 행으로 데이터프레임 생성
                    new_rows_df = pl.DataFrame(new_rows)
                    
                    # 데이터 타입 일치시키기
                    for field in fields:
                        if field in new_rows_df.columns and field in df.columns:
                            try:
                                # 원본 데이터프레임의 데이터 타입으로 변환 시도
                                new_rows_df = new_rows_df.with_columns(
                                    pl.col(field).cast(df[field].dtype, strict=False)
                                )
                            except Exception as e:
                                logger.error(f"필드 {field} 데이터 타입 변환 실패: {e}")
                    
                    # 기존 데이터프레임과 결합
                    if mode == "top":
                        # 상단에 추가
                        df_without_uniqid = pl.concat([new_rows_df, df_without_uniqid], how="vertical")
                    else:
                        # 하단에 추가
                        df_without_uniqid = pl.concat([df_without_uniqid, new_rows_df], how="vertical")
                    
                    # uniqid 인덱스 재생성
                    final_df = df_without_uniqid.with_row_index("uniqid")
                    
                    # 데이터프레임 업데이트
                    SSDF.dataframe = final_df
                    
                    # 컬럼 정의 업데이트
                    updated_columnDefs = generate_column_definitions(SSDF.dataframe)
                    
                    # 추가된 행 수 계산
                    added_rows = len(final_df) - original_row_count
                    
                    # 성공 메시지
                    toast = dbpc.Toast(
                        message=f"{added_rows}개 행이 {mode == 'top'and '상단' or '하단'}에 추가되었습니다.",
                        intent="success",
                        icon="endorsed",
                        timeout=4000
                    )
                    
                    return [toast], updated_columnDefs
                    
                except Exception as e:
                    logger.error(f"데이터프레임 생성 또는 결합 실패: {e}")
                    return ([dbpc.Toast(
                        message=f"행 추가 실패: 데이터프레임 처리 오류: {str(e)}",
                        intent="danger",
                        icon="error"
                    )], no_update)
                    
            except Exception as e:
                # 오류 메시지
                logger.error(f"행 추가 실패: {str(e)}")
                return ([dbpc.Toast(
                    message=f"행 추가 실패: {str(e)}",
                    intent="danger",
                    icon="error"
                )], no_update)
