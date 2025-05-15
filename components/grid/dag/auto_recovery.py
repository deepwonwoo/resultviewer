import os
import time
import threading
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Output, Input, State, html, dcc, no_update, exceptions
from datetime import datetime
import polars as pl
from utils.db_management import SSDF
from utils.config import CONFIG
from utils.logging_utils import logger
from components.grid.dag.column_definitions import generate_column_definitions


class AutoRecovery:
    def __init__(self):
        self.backup_interval = 600  # 10분(600초) 간격으로 백업
        self.backup_path = os.path.join(CONFIG.USER_RV_DIR, "backup")
        self.backup_file = None
        self.last_backup_time = None
        self.backup_thread = None
        self.stop_flag = threading.Event()
        self._setup_backup_directory()
        
    def _setup_backup_directory(self):
        """백업 디렉토리 생성"""
        try:
            if not os.path.exists(self.backup_path):
                os.makedirs(self.backup_path, mode=0o777, exist_ok=True)
        except Exception as e:
            logger.error(f"백업 디렉토리 생성 실패: {str(e)}")
    
    def layout(self):
        return html.Div([
            dcc.Interval(id="backup-interval", interval=self.backup_interval * 1000),  # 10분마다 백업
            dcc.Store(id="backup-info", data={"last_backup": None, "backup_file": None}),
            dcc.Store(id="current-file-info", data={"path": None, "name": None}),
            dbpc.Alert(
                id="recovery-alert",
                children=["자동 백업 파일이 발견되었습니다. 복구하시겠습니까?"],
                cancelButtonText="취소",
                confirmButtonText="복구",
                icon="history",
                intent="warning"
            ),
            # 백업 상태 표시를 위한 작은 텍스트
            html.Div(
                dmc.Text(id="backup-status", size="xs", color="dimmed"),
                style={"position": "fixed", "bottom": "5px", "left": "10px", "zIndex": 1000}
            )
        ])
    
    def register_callbacks(self, app):
        # 파일 로드 시 현재 파일 정보 저장
        @app.callback(
            Output("current-file-info", "data"),
            Input("csv-mod-time", "data"),
            State("flex-layout", "model")
        )
        def update_current_file_info(mod_time, model_layout):
            if not mod_time or not model_layout:
                return no_update
                
            try:
                file_path = model_layout["layout"]["children"][0]["children"][0]["name"]
                if not file_path:
                    return no_update
                    
                # WORKSPACE 경로 처리
                if file_path.startswith("WORKSPACE"):
                    file_path = file_path.replace("WORKSPACE", CONFIG.WORKSPACE)
                    
                return {
                    "path": file_path,
                    "name": os.path.basename(file_path),
                    "mod_time": mod_time
                }
            except Exception as e:
                logger.error(f"현재 파일 정보 업데이트 실패: {str(e)}")
                return no_update
        
        # 자동 백업 실행
        @app.callback(
            Output("backup-info", "data"),
            Output("backup-status", "children"),
            Output("backup-status", "color"),
            Input("backup-interval", "n_intervals"),
            State("current-file-info", "data"),
            State("backup-info", "data"),
            prevent_initial_call=True
        )
        def perform_auto_backup(n_intervals, file_info, backup_info):
            if not file_info or not file_info.get("path"):
                return no_update, "자동 백업: 열린 파일 없음", "gray"
                
            try:
                # 백업 디렉토리 확인
                if not os.path.exists(self.backup_path):
                    self._setup_backup_directory()
                
                # 데이터프레임 확인
                if SSDF.dataframe is None or SSDF.dataframe.is_empty():
                    return no_update, "자동 백업: 데이터 없음", "gray"
                
                # 디스크 공간 확인
                try:
                    import shutil
                    free_space = shutil.disk_usage(self.backup_path).free
                    df_size = SSDF.dataframe.estimated_size()
                    
                    if free_space < df_size * 2:  # 필요한 공간의 2배 확보
                        return backup_info, "자동 백업: 디스크 공간 부족", "red"
                except:
                    # 디스크 공간 확인 실패해도 계속 진행
                    pass
                
                # 백업 파일명 생성
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_base = os.path.splitext(file_info["name"])[0]
                backup_file = os.path.join(self.backup_path, f"{file_base}_backup.parquet")
                
                # 이전 백업 파일 삭제 (하나만 유지)
                if backup_info and backup_info.get("backup_file") and os.path.exists(backup_info["backup_file"]):
                    try:
                        os.remove(backup_info["backup_file"])
                    except Exception as e:
                        logger.error(f"이전 백업 파일 삭제 실패: {str(e)}")
                
                # 새 백업 저장
                SSDF.dataframe.write_parquet(backup_file)
                
                # 백업 정보 업데이트
                new_backup_info = {
                    "last_backup": timestamp,
                    "backup_file": backup_file,
                    "original_file": file_info["path"]
                }
                
                return new_backup_info, f"마지막 백업: {timestamp}", "green"
                
            except Exception as e:
                logger.error(f"자동 백업 실패: {str(e)}")
                return backup_info, f"자동 백업 실패: {str(e)[:30]}...", "red"
        
        # 앱 시작 시 백업 파일 확인
        @app.callback(
            Output("recovery-alert", "isOpen"),
            Output("recovery-alert", "children"),
            Input("current-file-info", "data"),
        )
        def check_backup_files(file_info):
            if not file_info or not file_info.get("path"):
                return False, no_update
                
            try:
                if not os.path.exists(self.backup_path):
                    return False, no_update
                    
                # 현재 파일에 대한 백업 찾기
                file_base = os.path.splitext(file_info["name"])[0]
                backup_file = os.path.join(self.backup_path, f"{file_base}_backup.parquet")
                
                if not os.path.exists(backup_file):
                    return False, no_update
                
                # 백업 파일 정보 확인
                backup_time = datetime.fromtimestamp(os.path.getmtime(backup_file)).strftime("%Y-%m-%d %H:%M:%S")
                
                # 백업 파일이 현재 파일보다 최신인지 확인
                current_file_time = datetime.fromtimestamp(file_info.get("mod_time", 0))
                backup_file_time = datetime.fromtimestamp(os.path.getmtime(backup_file))
                
                if backup_file_time <= current_file_time:
                    return False, no_update
                
                # 메시지 생성
                message = [
                    f"자동 백업 파일이 발견되었습니다. ({backup_time})",
                    html.Br(),
                    "현재 작업 내용이 모두 사라지고 백업 파일로 대체됩니다.",
                    html.Br(),
                    "복구하시겠습니까?"
                ]
                
                return True, message
                
            except Exception as e:
                logger.error(f"백업 파일 확인 실패: {str(e)}")
                return False, no_update
        
        # 복구 실행
        @app.callback(
            Output("aggrid-table", "columnDefs", allow_duplicate=True),
            Output("toaster", "toasts", allow_duplicate=True),
            Output("recovery-alert", "isConfirmed"),
            Input("recovery-alert", "isConfirmed"),
            State("current-file-info", "data"),
            prevent_initial_call=True
        )
        def recover_from_backup(confirmed, file_info):
            if not confirmed:
                return no_update, no_update, False
                
            try:
                if not file_info or not file_info.get("path"):
                    return no_update, no_update, False
                    
                file_base = os.path.splitext(file_info["name"])[0]
                backup_file = os.path.join(self.backup_path, f"{file_base}_backup.parquet")
                
                if not os.path.exists(backup_file):
                    return no_update, [dbpc.Toast(message="백업 파일을 찾을 수 없습니다.", intent="danger", icon="error")], False
                
                # 백업 파일 로드
                df = pl.read_parquet(backup_file)
                SSDF.dataframe = df
                
                # 백업 시간 확인
                backup_time = datetime.fromtimestamp(os.path.getmtime(backup_file)).strftime("%Y-%m-%d %H:%M:%S")
                
                return (
                    generate_column_definitions(df),
                    [dbpc.Toast(message=f"백업 파일 복구 완료 ({backup_time})", intent="success", icon="endorsed")],
                    False
                )
                
            except Exception as e:
                logger.error(f"백업 파일 복구 실패: {str(e)}")
                return no_update, [dbpc.Toast(message=f"백업 파일 복구 실패: {str(e)}", intent="danger", icon="error")], False