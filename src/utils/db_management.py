import os
import tempfile
from typing import Dict, Any
import diskcache as dc

DEBUG = True
USERNAME = os.getenv("USER", "user")
WORKSPACE = os.getenv("WORKSPACE", "C:/Users/deepw/OneDrive/문서/Python")
SCRIPT = os.getenv("SCRIPT_PATH", "/user/verifier14/deepwonwoo/Release/scripts")

def get_user_rv_dir() -> str:
    base_dir = "./RV"
    user_dir = f"{base_dir}_{USERNAME}"
    return user_dir if os.access(".", os.W_OK) and not os.path.exists(user_dir) else os.path.join(tempfile.gettempdir(), f"RV_{USERNAME}")

def ensure_directory_exists(directory: str) -> None:
    os.makedirs(directory, exist_ok=True)

def initialize_cache(cache_dir: str) -> dc.Cache:
    return dc.Cache(os.path.join(cache_dir, f"cache_{USERNAME}"))

USER_RV_DIR = get_user_rv_dir()
ensure_directory_exists(USER_RV_DIR)

DATAFRAME: Dict[str, Any] = {"df": None, "lock": None, "readonly": True}
APPCACHE = initialize_cache(USER_RV_DIR)
ROW_COUNTER: Dict[str, int] = {"filtered": 0, "groupby": 0, "total_waivers": 0, "waived": 0}
CACHE: Dict[str, Any] = {"REQUEST": None, "hide_waiver": None, "CP": {}, "init_csv": {}, "TreeMode": {}, "TreeCol": {}, "viewmode": {}, "PropaRule": {}}

def get_cache(key, default=None):
    return CACHE.get(key, default)

def set_cache(key, value):
    CACHE[key] = value

def get_dataframe(key, default=None):
    return DATAFRAME.get(key, default)

def set_dataframe(key, value):
    DATAFRAME[key] = value
