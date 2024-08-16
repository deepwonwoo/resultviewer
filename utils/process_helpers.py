import os
import pwd
import time
import shutil
import datetime
import traceback
import polars as pl
import dash_mantine_components as dmc
from dash import html, exceptions, ctx
from collections import Counter
from screeninfo import get_monitors
from functools import wraps
from components.grid.DAG.serverSide import apply_filters
from utils.db_management import CACHE, USERNAME, DATAFRAME
from utils.logging_config import logger
from filelock import SoftFileLock


def debugging_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):

        try:
            if ctx.triggered:
                logger.debug(f"Triggered by {ctx.triggered}")
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            logger.debug(f"{func.__name__} took {end - start:.2f}s to execute.")
        except Exception as e:
            logger.debug(f"Exception occured in ")
            logger.debug(f"{traceback.print_exc()}")
            raise exceptions.PreventUpdate
        finally:
            logger.debug("=" * 10)

        return result

    return wrapper


def create_notification(
    message,
    title="Something went wrong!",
    color="yellow",
    action="show",
    icon_name="bx-tired",
    position="bottom-right",
):
    """Generate a notification component."""
    if position == "center":
        style = {
            "position": "fixed",
            "top": "50%",
            "left": "50%",
            "transform": "translate(-50%, -50%)",
            "width": "auto",
            "zIndex": 9999,
        }
    elif position == "top-center":
        style = {
            "position": "fixed",
            "top": 20,
            "left": "50%",
            "transform": "translateX(-50%)",
            "width": "auto",
            "zIndex": 9999,
        }
    elif position == "top-right":
        style = {
            "position": "fixed",
            "top": 20,
            "right": 20,
            "width": 400,
            "zIndex": 9999,
        }
    elif position == "bottom-right":
        style = {
            "position": "fixed",
            "bottom": 70,
            "right": 25,
            "width": 400,
            "zIndex": 9999,
        }

    return dmc.Notification(
        title=title,
        message=message,
        color=color,
        action=action,
        icon=get_icon(icon_name),
        style=style,
        withCloseButton=True,
        withBorder=True,
    )


def preprocess():
    """Prepare the environment by cleaning up the uploads directory."""
    CACHE.clear()


def postprocess():
    if DATAFRAME.get("lock") is not None:
        DATAFRAME["lock"].release()
    CACHE.close()


def get_monitor_size():
    monitor = get_monitors()[-1]
    return monitor.width, monitor.height


def get_lock_status(file_path):
    lock_path = f"{file_path}.lock"
    if not os.path.exists(lock_path):
        return False, None
    file_owner_name = get_file_owner(lock_path)
    return True, file_owner_name


def get_icon(icon, width=20, height=20):
    return html.Img(src=f"assets/icons/{icon}.png", width=width, height=height)


def get_file_owner(file_path):
    try:
        file_owner_id = os.stat(file_path).st_uid
        file_owner_name = pwd.getpwuid(file_owner_id).pw_name
        return file_owner_name
    except Exception as e:
        logger.error(f"get_file_owner error: {e}")
        return e


def backup_file(dir_path, file_path):

    backup_dir = os.path.join(dir_path, "backup")
    create_directory(backup_dir)
    file_owner = get_file_owner(file_path)
    file_timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y%m%d_%H%M")
    # split the file path into directory and file
    dir_path, filename = os.path.split(file_path)
    # split the filename into name and extension
    name, ext = os.path.splitext(filename)

    # create a backup file name with modtime and USERNAME
    backup_filename = f"{name}_{file_timestamp}_{file_owner}{ext}"
    backup_filepath = os.path.join(backup_dir, backup_filename)
    shutil.move(file_path, backup_filepath)


def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        os.chmod(path, 0o777)


def file2df(csv_file_path, workspace=True):
    try:
        df = validate_df(csv_file_path)
    except:
        raise
    global DATAFRAME
    DATAFRAME["df"] = df

    if DATAFRAME.get("lock") is not None:
        DATAFRAME["lock"].release()
    if workspace:
        lock, owner = get_lock_status(csv_file_path)
        if lock:
            DATAFRAME["readonly"] = True
        else:
            # check if the directory exists
            if os.access(os.path.dirname(csv_file_path), os.W_OK):
                DATAFRAME["readonly"] = False
                DATAFRAME["lock"] = SoftFileLock(f"{csv_file_path}.lock", thread_local=False)
                DATAFRAME["lock"].acquire(timeout=1, poll_interval=0.05)

    return df


def validate_df(csv_file):

    def detect_separator(file_path, sample_lines=10):
        possible_separators = [",", ";", "\t", " ", "|"]
        separator_counts = Counter()

        with open(file_path, "r") as file:
            # 파일의 처음 sample_lines 줄을 읽습니다.
            for _ in range(sample_lines):
                line = file.readline()
                if not line:
                    break
                line = line.strip()
                for sep in possible_separators:
                    separator_counts[sep] += line.count(sep)

        # 가장 많이 사용된 구분자를 반환합니다.
        most_common_separator = separator_counts.most_common(1)[0][0]
        return most_common_separator

    if csv_file.endswith(".parquet"):
        df = pl.read_parquet(csv_file)

    # 파일 확장자에 따라 처리
    else:
        try:
            df = pl.read_csv(
                csv_file,
                ignore_errors=True,
                infer_schema_length=0,
                separator=detect_separator(csv_file),
            )
        except pl.PolarsError as e:
            if "truncate_ragged_lines=True" in str(e):
                try:
                    df = pl.read_csv(
                        csv_file,
                        ignore_errors=True,
                        infer_schema_length=0,
                        truncate_ragged_lines=True,
                    )
                except:
                    raise
            else:
                raise
        except Exception as e:
            raise

        # strip
        df = df.rename({col: col.strip() for col in df.columns})
        for col in df.columns:
            if df[col].dtype == pl.Utf8:
                df = df.with_columns(pl.col(col).str.strip().alias(col))
        # 컬럼 별로 타입 캐스팅 시도
        for col in df.columns:
            try:
                # 문자열 컬럼을 pl.Float64로 캐스팅 시도
                df = df.with_columns(pl.col(col).cast(pl.Float64()).alias(col))
                # 캐스팅 성공 시, 모든 값이 정수인지 확인하여 정수로만 구성되면 pl.Int64로 다시 캐스팅
                if df[col].dtype == pl.Float64:
                    # map_elements 대신 캐스팅을 사용하여 정수 확인
                    if (df[col] == df[col].cast(pl.Int64())).sum() == len(df[col]):
                        df = df.with_columns(pl.col(col).cast(pl.Int64()).alias(col))
                # 숫자 컬럼에 대해 Null 및 NaN 값을 0으로 대체
                df = df.with_columns(pl.col(col).fill_null(0).fill_nan(0))
            except Exception as e:
                df = df.with_columns(pl.col(col).fill_null(""))

    return df.with_row_index("uniqid")


def displaying_df(filtred_apply=False):

    dff = DATAFRAME.get("df", None)

    if dff is None:
        return None
    else:
        try:
            if CACHE.get("hide_waiver") and "waiver" in dff.columns:
                conditions_expr = dff["waiver"] == "Waiver."
                update_waiver_column = (
                    pl.when(conditions_expr).then(pl.lit("Waiver")).otherwise(pl.col("waiver")).alias("waiver")
                )
                dff = dff.with_columns(update_waiver_column)

                conditions_expr = dff["waiver"] == "Fixed."
                update_waiver_column = (
                    pl.when(conditions_expr).then(pl.lit("Fixed")).otherwise(pl.col("waiver")).alias("waiver")
                )
                dff = dff.with_columns(update_waiver_column)

            if filtred_apply:
                dff = apply_filters(dff, CACHE.get("REQUEST"))
        except Exception as e:
            logger.error(f"displaying_df Error : {e}")
            dff = DATAFRAME["df"]

        return dff.drop(["uniqid", "childCount"])
