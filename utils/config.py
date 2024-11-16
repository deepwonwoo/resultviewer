import os
import datetime
import tempfile
import diskcache as dc


class Config:
    
    def __init__(self):
        # self.WORKSPACE = "/user/ecolake/DATA/VERIFY/SIGNOFF/ResultViewer"
        # self.SCRIPT = "/user/signoff.dev/deepwonwoo/scripts"
        self.USERNAME = "deepwonwoo"
        self.WORKSPACE = "C:/Users/deepw/OneDrive/문서/Python"
        self.SCRIPT = os.getenv("SCRIPT_PATH", "/user/verifier14/deepwonwoo/Release/scripts")
        self.USER_RV_DIR, self.APPCACHE = self.get_user_rv_dir(self.USERNAME)

    def get_user_rv_dir(self, username=os.getenv("USER")) -> str:
        def make_cache_dir(dir_path: str) -> dc.Cache:
            os.makedirs(dir_path, mode=0o777, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            return dc.Cache(os.path.join(dir_path, f"cache_{username}"))

        base_dir = "RV"
        user_dir = f"./{base_dir}_{username}"
        
        user_dir = os.path.join(tempfile.gettempdir(), f"{base_dir}_{username}")
        return user_dir, make_cache_dir(user_dir)


CONFIG = Config()
