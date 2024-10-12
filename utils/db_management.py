import os
#import pwd
import polars as pl
from filelock import SoftFileLock
from typing import Dict, Any, List, Optional
from utils.file_operations import get_viewers_from_lock_file

class DataFrameManager:

    def __init__(self):
        self._data: Dict[str, Any] = {
            "df": pl.DataFrame(),
            "lock": None,
            "readonly": True,
        }
        self._row_counter: Dict[str, int] = {"filtered": 0, "groupby": 0}
        self._cache: Dict[str, Any] = {
            "REQUEST": {},
            "hide_waiver": None,
            "CP": {},
            "init_csv": {},
            "TreeMode": {},
            "TreeCol": {},
            "viewmode": {},
            "PropaRule": [],
            "TreeDeli": {},
            "js": {},
        }

    @property
    def dataframe(self) -> Any:
        return self._data.get("df")

    @dataframe.setter
    def dataframe(self, value: Any) -> None:
        self._data["df"] = value

    @property
    def is_readonly(self) -> bool:
        return self._data.get("readonly", True)

    @is_readonly.setter
    def is_readonly(self, value: bool) -> None:
        self._data["readonly"] = value

    @property
    def lock(self) -> Optional[SoftFileLock]:
        return self._data.get("lock")

    @lock.setter
    def lock(self, value: Optional[SoftFileLock]) -> None:
        self._data["lock"] = value

    def acquire_lock(self, file_path: str) -> bool:
        """파일에 대한 lock을 획득합니다."""
        lock_path = f"{file_path}.lock"
        lock = SoftFileLock(lock_path, thread_local=False)
        try:
            lock.acquire()
            self._data["lock"] = lock
            return True
        except TimeoutError:
            return False

    def release_lock(self) -> None:
        """현재 보유 중인 lock을 해제합니다."""
        lock = self._data.get("lock")
        if lock:
            viewers = get_viewers_from_lock_file(lock.lock_file)
            current_user = os.getenv("USER")
            lock_filename = os.path.basename(lock.lock_file)
            #viewers = [pwd.getpwnam(viewer).pw_uid for viewer in viewers]
            viewers = []

            lock.release()
            self._data["lock"] = None
            if os.path.exists(lock_filename):
                os.remove(lock_filename)

    # Row counter related methods
    def get_row_count(self, key: str) -> int:
        return self._row_counter.get(key, 0)

    def set_row_count(self, key: str, value: int) -> None:
        self._row_counter[key] = value

    @property
    def filtered_row_count(self) -> int:
        return self._row_counter.get("filtered", 0)

    @filtered_row_count.setter
    def filtered_row_count(self, value: int) -> None:
        self._row_counter["filtered"] = value

    @property
    def groupby_row_count(self) -> int:
        return self._row_counter.get("groupby", 0)

    @groupby_row_count.setter
    def groupby_row_count(self, value: int) -> None:
        self._row_counter["groupby"] = value

    def get_cache(self, key: str, default: Any = None) -> Any:
        return self._cache.get(key, default)

    def set_cache(self, key: str, value: Any) -> None:
        self._cache[key] = value

    @property
    def request(self) -> Dict:
        return self._cache.get("REQUEST")

    @request.setter
    def request(self, value: Dict) -> None:
        self._cache["REQUEST"] = value

    @property
    def hide_waiver(self) -> Optional[bool]:
        return self._cache.get("hide_waiver")

    @hide_waiver.setter
    def hide_waiver(self, value: Optional[bool]) -> None:
        self._cache["hide_waiver"] = value

    @property
    def cp(self) -> Dict:
        return self._cache.get("CP")

    @cp.setter
    def cp(self, value: Dict) -> None:
        self._cache["CP"] = value

    @property
    def init_csv(self) -> str:
        return self._cache.get("init_csv", "")

    @init_csv.setter
    def init_csv(self, value: str) -> None:
        self._cache["init_csv"] = value

    @property
    def tree_mode(self) -> Dict:
        return self._cache.get("TreeMode")

    @tree_mode.setter
    def tree_mode(self, value: Dict) -> None:
        self._cache["TreeMode"] = value

    @property
    def tree_col(self) -> Dict:
        return self._cache.get("TreeCol")

    @tree_col.setter
    def tree_col(self, value: Dict) -> None:
        self._cache["TreeCol"] = value

    @property
    def viewmode(self) -> Dict:
        return self._cache.get("viewmode", "")

    @viewmode.setter
    def viewmode(self, value: Dict) -> None:
        self._cache["viewmode"] = value

    @property
    def propa_rule(self) -> List:
        return self._cache.get("PropaRule")

    @propa_rule.setter
    def propa_rule(self, value: List) -> None:
        self._cache["PropaRule"] = value

    @property
    def tree_deli(self) -> Dict:
        return self._cache.get("TreeDeli")

    @tree_deli.setter
    def tree_deli(self, value: Dict) -> None:
        self._cache["TreeDeli"] = value

    @property
    def js(self) -> Dict:
        return self._cache.get("js")

    @js.setter
    def js(self, value: Dict) -> None:
        self._cache["js"] = value


# Global instances
SSDF = DataFrameManager()
