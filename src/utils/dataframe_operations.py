import os
import polars as pl
from collections import Counter
from utils.logging_utils import logger
from utils.file_operations import get_lock_status, acquire_file_lock
from utils.db_management import DATAFRAME, CACHE
from components.dag.server_side_operations import apply_filters


def read_csv_file(csv_file):

    def detect_separator(file_path, sample_lines=10):
        possible_separators = [",", ";", "\t", " ", "|"]
        separator_counts = Counter()

        with open(file_path, "r") as file:
            for _ in range(sample_lines):
                line = file.readline()
                if not line:
                    break
                line = line.strip()
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
                
                if df[col].dtype == pl.Float64:
                    if (df[col] == df[col].cast(pl.Int64())).sum() == len(df[col]):
                        df = df.with_columns(pl.col(col).cast(pl.Int64()).alias(col))
                
                df = df.with_columns(pl.col(col).fill_null(0).fill_nan(0))
            except Exception:
                df = df.with_columns(pl.col(col).fill_null(""))

        return df.with_row_index("uniqid")

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
    df = pl.read_parquet(csv_file) if csv_file.endswith(".parquet") else read_csv_file(csv_file)
    return df



def file2df(csv_file_path, workspace=True):
    try:
        df = validate_df(csv_file_path)
    except Exception as e:
        logger.error(f"Error validating DataFrame: {e}")
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
            if os.access(os.path.dirname(csv_file_path), os.W_OK):
                DATAFRAME["readonly"] = False
                DATAFRAME["lock"] = acquire_file_lock(csv_file_path)

    return df


def displaying_df(filtred_apply=False):
    
    dff = DATAFRAME.get("df", None)
    hide_waiver = CACHE.get("hide_waiver")


    if dff is None:
        return None
    
    try:
        if hide_waiver and "waiver" in dff.columns:
            conditions_expr = (dff["waiver"] == "Waiver.") | (dff["waiver"] == "Fixed.")
            update_waiver_column = (
                pl.when(conditions_expr)
                .then(pl.col("waiver").str.strip_chars("."))
                .otherwise(pl.col("waiver"))
                .alias("waiver")
            )
            dff = dff.with_columns(update_waiver_column)

        if filtred_apply:
            dff = apply_filters(dff, CACHE.get("REQUEST"))
    except Exception as e:
        logger.error(f"displaying_df Error : {e}")

    if "childCount" in dff.columns:
        dff = dff.drop("childCount")

    return dff.drop(["uniqid"])