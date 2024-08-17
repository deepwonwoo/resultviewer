import os
import tempfile
from typing import Dict, Any, Optional
import diskcache as dc


# Constants and Configuration
DEBUG = True
USERNAME = os.getenv("USER", "user")  # Use environment variable with fallback
WORKSPACE = os.getenv("WORKSPACE", "C:/Users/deepw/OneDrive/문서/Python") # "/user/ecolake/DATA/VERIFY/SIGNOFF/ResultViewer"
SCRIPT = os.getenv("SCRIPT_PATH", "/user/verifier14/deepwonwoo/Release/scripts")


def get_user_rv_dir() -> str:
    """Determine the workspace directory based on write access."""
    base_dir = "./RV"
    user_dir = f"{base_dir}_{USERNAME}"
    
    if os.access(".", os.W_OK):
        if not os.path.exists(user_dir): # or  os.stat(user_dir).st_uid != os.getuid():  리눅스에서는 이주석 풀어야함
            return user_dir
    
    return os.path.join(tempfile.gettempdir(), f"RV_{USERNAME}")

def ensure_directory_exists(directory: str) -> None:
    """Create the directory if it doesn't exist."""
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except OSError as e:
            print(f"Error creating directory {directory}: {e}")

def initialize_cache(cache_dir: str) -> dc.Cache:
    """Initialize the disk cache within the workspace directory."""
    cache_path = os.path.join(cache_dir, f"cache_{USERNAME}")
    return dc.Cache(cache_path)


# Initialize workspace and cache
USER_RV_DIR = get_user_rv_dir()
ensure_directory_exists(USER_RV_DIR)
CACHE = initialize_cache(USER_RV_DIR)


# Initialize dictionaries to store DataFrames info
DATAFRAME: Dict[str, Any] = {"df": None, "lock": None, "readonly": True}
ROW_COUNTER:  Dict[str, int] = {"filtered": 0, "groupby": 0, "waived": 0}



# 전역 변수에 대한 안전한 접근을 제공하는 함수들
def get_dataframe() -> Optional[Any]:
    """Getter for the dataframe."""
    return DATAFRAME.get("df")

def set_dataframe(df: Any) -> None:
    """Setter for the dataframe."""
    DATAFRAME["df"] = df

def update_row_counter(counter_type: str, value: int) -> None:
    """Update the row counter."""
    if counter_type in ROW_COUNTER:
        ROW_COUNTER[counter_type] = value
    else:
        print(f"Warning: Unknown counter type '{counter_type}'")