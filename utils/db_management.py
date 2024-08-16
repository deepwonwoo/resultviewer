import os
import tempfile
import diskcache as dc

DEBUG = True

USERNAME = "deepwonwoo" # os.getenv("USER")
WORKSPACE = "C:/Users/deepw/OneDrive/문서/Python" # "/user/ecolake/DATA/VERIFY/SIGNOFF/ResultViewer"
SCRIPT = "/user/verifier14/deepwonwoo/Release/scripts"

# Determine the workspace directory based on write access to the current directory
# or fall back to a temporary directory if no write access.
USER_RV_DIR = "./RV"
if os.access(".", os.W_OK) and (not os.path.exists(USER_RV_DIR) or os.stat(USER_RV_DIR).st_uid != os.getuid()):
    USER_RV_DIR = f"./RV_{USERNAME}"
elif not os.access(".", os.W_OK):
    USER_RV_DIR = os.path.join(tempfile.gettempdir(), f"RV_{USERNAME}")

if not os.path.exists(USER_RV_DIR):
    os.makedirs(USER_RV_DIR)

# Initialize the disk cache within the workspace directory
CACHE = dc.Cache(os.path.join(USER_RV_DIR, f"cache_{USERNAME}"))


# Initialize dictionaries to store DataFrames info.
DATAFRAME = {"df": None, "lock": None, "readonly": True}
ROW_COUNTER = {"filtered": 0, "groupby": 0, "waived": 0}
