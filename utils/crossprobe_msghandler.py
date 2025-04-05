import re
import polars as pl
import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import Input, Output, State, no_update
from utils.db_management import SSDF
from utils.logging_utils import logger


class MsgHandler:

    def __init__(self):
        self.current_view = ""
        self.hier = ""

    def remove_initial_x(self, s):
        s = re.sub(r"^[xX]{2}(?!or)", "x", s, flags=re.IGNORECASE)
        s = re.sub(r"^[xX]", "", s, flags=re.IGNORECASE)
        return s

    def hier_name(self, s, delimiter="."):

        def remove_dot_main(s):
            return re.sub(r"\.main$", "", s)

        s = s.split("@")[0].replace("/", ".")
        s = remove_dot_main(s)

        paths = s.split(delimiter)
        if len(paths) > 1:
            # paths = [path[1:] if path.lower()[0]=="x" else path for path in paths]
            paths = [self.remove_initial_x(path) for path in paths]
            s = delimiter.join(paths)
        elif len(paths) == 1:
            s = self.remove_initial_x(s)
        try:
            hier_path, name = s.rsplit(
                delimiter, 1
            )  # 오른쪽에서부터 문자열을 '.'으로 분리
        except ValueError:  # '.'이 없어서 분리할 수 없는 경우
            hier_path = ""  # hier_path를 빈 문자열로 설정
            name = s  # name에 입력받은 문자열을 그대로 반환

        return hier_path, name

    def remove_init_r_m(self, obj, selected_name):
        # remove 'm' or 'r' at the begining of instance name
        if obj == "inst" and len(selected_name) > 1:
            if selected_name[0] == "r" or selected_name[0] == "m":
                selected_name = selected_name[1:]
        return selected_name

    def preprocess_d_name(obj, name):
        if obj == "inst" and len(name) > 1:
            # 'd'로 시작하지 않으면 원래 이름 반환
            if not name.startswith("d"):
                return name
            # 'd' 제거
            processed_name = name[1:]
            # 'd' 제거 후 숫자로만 이루어진 경우 원래 이름으로 복원
            if re.match(r"^\d+$", processed_name):
                return name
            return processed_name
        else:
            return name

    def cross_probing(self, selected_rows, obj, cp_col):
        logger.info(f"cross_probing! (obj:{obj}, tool:{cp_col})")
        if not obj:
            return [
                dbpc.Toast(
                    message="select 'net/instance to crossprobe",
                    intent="warning",
                    icon="warning-sign",
                )
            ]

        selected_row = selected_rows[0]
        value = selected_row[cp_col]
        if value == "":
            return no_update

        request = SSDF.request
        groupBy = [col["id"] for col in request.get("rowGroupCols", [])]

        selected_hier_path, selected_name = self.hier_name(value)
        selected_name = self.remove_init_r_m(obj, selected_name)
        # selected_name = self.preprocess_d_name(obj,selected_name)

        # Group CrossProbing
        if groupBy:
            dff = SSDF.dataframe
            for gc in groupBy:
                dff = dff.filter(pl.col(gc) == selected_row[gc])

            names = set([selected_name])
            for group_value in dff[cp_col]:
                group_hier_path, group_hier_name = self.hier_name(group_value)
                if group_hier_path == selected_hier_path:
                    name = self.remove_init_r_m(obj, group_hier_name)
                    # name = self.preprocess_d_name(obj, name)
                    names.add(name)

                elif group_hier_path.startswith(selected_hier_path):
                    group_hier_path = group_hier_path.replace(selected_hier_path, "")
                    if len(group_hier_path) and group_hier_path[0] == ".":
                        name = self.remove_init_r_m(obj, group_hier_path.split(".")[1])
                        # name = self.preprocess_d_name(obj, name)
                        names.add(name)

            if self.current_view == selected_hier_path:
                # Single Instance CrossProbing
                msg = f"selectCurObject -obj {obj} -name {','.join(names)}\n"
            else:
                msg = f"select -obj {obj} -hier {selected_hier_path} -name {','.join(names)}\n"
        else:
            # if save view hierarchy
            if self.current_view == selected_hier_path:
                # Single Instance CrossProbing
                msg = f"selectCurObject -obj {obj} -name {selected_name}\n"
            else:
                # Single Instance CrossProbing
                if selected_hier_path:
                    msg = f"select -obj {obj} -hier {selected_hier_path} -name {selected_name}\n"
                else:
                    msg = f"select -obj {obj} -name {selected_name}\n"
                self.current_view = selected_hier_path
        return msg

    def convert_cp_msg(self, msg, tool_name=""):
        # selectCurObject -obj "net" -name dev_name
        # select -obj "net" -name dev_name
        # select -obj "net" -hier hierarchy -name dev_name
        if "net" not in msg:
            return
        # cmd = msg.split()[0]; obj = msg.split()[2]
        try:
            if "-hier" in msg:
                hier = msg.split()[4]
                name = msg.split()[6]
            else:
                hier = None
                name = msg.split()[4]

            if hier is not None:
                if tool_name == "customwaveview":
                    self.hier = "x" + hier.replace(
                        ".", ".x"
                    )  # _abc._def._ghi -> x_abc.x_def.x_ghi
                elif tool_name == "verdi":
                    self.hier = hier.replace(
                        ".", "/"
                    )  # _abc._def._ghi -> _abc/x_def/x_ghi
                else:
                    self.hier = hier
            return ".".join([self.hier, name])

        except Exception as e:
            logger.error(f"Error converting cp msg: {str(e)}")
            logger.error(f"Original msg: {str(msg)}")
