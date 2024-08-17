import os
import shutil
import datetime
from filelock import SoftFileLock
from utils.logging_utils import logger



def get_lock_status(file_path):
    lock_path = f"{file_path}.lock"
    if not os.path.exists(lock_path):
        return False, None
    file_owner_name = get_file_owner(lock_path)
    return True, file_owner_name

def get_file_owner(file_path):
    try:
        # file_owner_id = os.stat(file_path).st_uid
        # file_owner_name = pwd.getpwuid(file_owner_id).pw_name
        return "file_owner_name"
    except Exception as e:
        logger.error(f"get_file_owner error: {e}")
        return str(e)


def backup_file(dir_path, file_path):
    backup_dir = os.path.join(dir_path, "backup")
    create_directory(backup_dir)
    file_owner = get_file_owner(file_path)
    file_timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y%m%d_%H%M")
    dir_path, filename = os.path.split(file_path)
    name, ext = os.path.splitext(filename)
    backup_filename = f"{name}_{file_timestamp}_{file_owner}{ext}"
    backup_filepath = os.path.join(backup_dir, backup_filename)
    shutil.move(file_path, backup_filepath)



def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        os.chmod(path, 0o777)

def acquire_file_lock(file_path):
    lock = SoftFileLock(f"{file_path}.lock", thread_local=False)
    lock.acquire(timeout=1, poll_interval=0.05)
    return lock

def release_file_lock(lock):
    if lock is not None:
        lock.release()

