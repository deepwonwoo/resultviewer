import os

# import pwd
import json
import shutil
from datetime import datetime
from utils.config import CONFIG
from utils.logging_utils import logger


def get_file_owner(file_path):
    try:
        # file_owner_id = os.stat(file_path).st_uid
        # file_owner_name = pwd.getpwuid(file_owner_id).pw_name
        return "file_owner_name"
    except Exception as e:
        logger.error(f"get_file_owner 오류: {e}")
        return str(e)


def get_lock_status(file_path):
    lock_path = f"{file_path}.lock"
    try:
        if not os.path.exists(lock_path):
            return False, None
        file_owner_name = get_file_owner(lock_path)
        return True, file_owner_name
    except Exception as e:
        logger.error(f"Error checking lock status for {file_path}: {e}")
    return False, None


def add_viewer_to_lock_file(file_path, viewer_id):
    lock_file = f"{file_path}.lock"
    data = {"viewers": []}
    if os.path.exists(lock_file):
        try:
            with open(lock_file, "r") as f:
                content = f.read().strip()
                if content:  # 파일에 내용이 있을 경우에만 JSON 파싱 시도
                    data = json.loads(content)
                    if not isinstance(data, dict):
                        data = {"viewers": []}
                    elif "viewers" not in data:
                        data["viewers"] = []
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 기본 데이터 구조 사용
            data = {"viewers": []}

    if viewer_id not in data["viewers"]:
        data["viewers"].append(viewer_id)

    with open(lock_file, "w") as f:
        json.dump(data, f)


def get_viewers_from_lock_file(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    return data.get("viewers", [])
        except json.JSONDecodeError:  # JSON 파싱 실패 시 빈 리스트 반환
            return []
    return []


def make_dirs_with_permissions(path):
    base_path = CONFIG.WORKSPACE
    relative_path = path.replace(base_path, "", 1)
    current_path = base_path
    for part in relative_path.split(os.sep):
        if part:  # 빈 문자열을 제외
            current_path = os.path.join(current_path, part)
            if not os.path.exists(current_path):  # 디렉토리가 없으면 생성하고 권한 설정
                os.makedirs(current_path, exist_ok=True)
                os.chmod(current_path, 0o777)


def backup_file(dir_path, file_path):
    backup_dir = os.path.join(dir_path, "backup")
    make_dirs_with_permissions(backup_dir)
    file_owner = get_file_owner(file_path)
    file_timestamp = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y%m%d_%H%M")
    dir_path, filename = os.path.split(file_path)
    name, ext = os.path.splitext(filename)
    backup_filename = f"{name}_{file_timestamp}_{file_owner}{ext}"
    backup_filepath = os.path.join(backup_dir, backup_filename)
    shutil.move(file_path, backup_filepath)
    return backup_filepath
