import os
import datetime
import polars as pl
from collections import Counter
from filelock import SoftFileLock
from utils.logging_utils import logger
from utils.db_management import get_dataframe, CACHE, get_cache, set_dataframe
from components.dag.server_side_operations import apply_filters
from utils.file_operations import get_lock_status, get_file_owner, backup_file, create_directory

def detect_separator(file_path, sample_lines=10):
    possible_separators = [",", ";", "\t", " ", "|"]
    separator_counts = Counter()

    with open(file_path, "r") as file:
        for _ in range(sample_lines):
            line = file.readline().strip()
            if not line:
                break
            for sep in possible_separators:
                separator_counts[sep] += line.count(sep)

    return separator_counts.most_common(1)[0][0]

def process_dataframe(df):
    df = df.rename({col: col.strip() for col in df.columns})

    for col in df.columns:
        try:
            if df[col].dtype == pl.Utf8:
                df = df.with_columns(pl.col(col).str.strip_chars().alias(col))

            df = df.with_columns(pl.col(col).cast(pl.Float64()).alias(col))

            if df[col].dtype == pl.Float64 and (df[col] == df[col].cast(pl.Int64())).all():
                df = df.with_columns(pl.col(col).cast(pl.Int64()).alias(col))

            df = df.with_columns(pl.col(col).fill_null(0).fill_nan(0))
        except Exception:
            df = df.with_columns(pl.col(col).fill_null(""))

    return df.with_row_index("uniqid")

def read_csv_file(csv_file):
    try:
        df = pl.read_csv(
            csv_file,
            ignore_errors=True,
            infer_schema_length=0,
            separator=detect_separator(csv_file),
        )
    except pl.PolarsError as e:
        if "truncate_ragged_lines=True" in str(e):
            df = pl.read_csv(
                csv_file,
                ignore_errors=True,
                infer_schema_length=0,
                truncate_ragged_lines=True,
            )
        else:
            raise

    return process_dataframe(df)

def validate_df(csv_file):
    return pl.read_parquet(csv_file) if csv_file.endswith(".parquet") else read_csv_file(csv_file)

def file2df(csv_file_path, workspace=True):
    try:
        df = validate_df(csv_file_path)
    except Exception as e:
        logger.error(f"Error validating DataFrame: {e}")
        raise

    set_dataframe("df", df)

    if get_dataframe("lock"):
        get_dataframe("lock").release()

    if workspace:
        lock, owner = get_lock_status(csv_file_path)
        set_dataframe("readonly", lock)
        if not lock and os.access(os.path.dirname(csv_file_path), os.W_OK):
            set_dataframe("lock", acquire_file_lock(csv_file_path))

    return df

def displaying_df(filtred_apply=False):
    dff = get_dataframe("df")
    hide_waiver = CACHE.get("hide_waiver")

    if dff is None:
        return None

    try:
        if hide_waiver and "waiver" in dff.columns:
            conditions_expr = (dff["waiver"] == "Waiver.") | (dff["waiver"] == "Fixed.")
            update_waiver_column = pl.when(conditions_expr).then(pl.col("waiver").str.strip_chars(".")).otherwise(pl.col("waiver")).alias("waiver")
            dff = dff.with_columns(update_waiver_column)

        if filtred_apply:
            dff = apply_filters(dff, get_cache("REQUEST"))
    except Exception as e:
        logger.error(f"displaying_df Error : {e}")

    return dff.drop(["uniqid", "childCount"] if "childCount" in dff.columns else ["uniqid"])

def acquire_file_lock(file_path):
    lock_path = f"{file_path}.lock"
    lock = SoftFileLock(lock_path, thread_local=False)
    try:
        lock.acquire(timeout=1, poll_interval=0.05)
        return lock
    except:
        return None

def enter_edit_mode(file_path):
    lock, _ = get_lock_status(file_path)
    if lock:
        return False
    lock = acquire_file_lock(file_path)
    if lock:
        if get_dataframe("lock"):
            get_dataframe("lock").release()
        set_dataframe("lock", lock)
        return True
    return False

def exit_edit_mode(file_path):
    if get_dataframe("lock"):
        get_dataframe["lock"].release()
        set_dataframe("lock", None)

def save_changes(file_path):
    df = displaying_df()
    if df is not None:
        df.write_parquet(file_path)
