import polars as pl
from collections import Counter
from components.grid.dag.server_side_operations import (
    apply_filters,
    apply_group,
    apply_sort,
)
from utils.db_management import SSDF
from utils.logging_utils import logger
from utils.config import CONFIG


def file2df(csv_file_path):
    try:
        df = validate_df(csv_file_path)
        SSDF.dataframe = df
        SSDF.release_lock()
        return df
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


def validate_df(filename):

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

    def try_convert(df, col_name):
        float_col = df[col_name].cast(pl.Float64, strict=False)
        if float_col.null_count() == 0:
            return float_col
        return df[col_name]

    def process_dataframe(df):
        df = df.rename({col: col.strip().replace(".", "_") for col in df.columns})
        df = df.select([col for col in df.columns if col != ""])
        for col in df.columns:
            try:
                if df[col].dtype == pl.Utf8:
                    df = df.with_columns(pl.col(col).str.strip_chars().alias(col))

                df = df.with_columns(try_convert(df, col).alias(col))
                df = df.with_columns(
                    pl.col(col)
                    .replace(float("inf"), -99999)
                    .fill_null(-99999)
                    .fill_nan(-99999)
                    .alias(col)
                )

            except Exception:
                try:
                    df = df.with_columns(pl.col(col).fill_null(""))
                except Exception as e:
                    logger.error(f"Error: {e}")
        return df

    if filename.startswith("WORKSAPCE"):
        filename = filename.replace("WORKSPACE", CONFIG.WORKSPACE)

    if filename.endswith(".parquet"):
        try:
            df = pl.read_parquet(filename)
            return df.with_row_index("uniqid")

        except Exception as e:
            logger.error(f"Fail to read parquet: {e}")
    else:
        try:
            df = pl.read_csv(
                filename,
                ignore_errors=True,
                infer_schema_length=0,
                separator=detect_separator(filename),
                null_values="-",
            )
        except pl.PolarsError as e:
            if "truncate_ragged_lines=True" in str(e):
                df = pl.read_csv(
                    filename,
                    ignore_errors=True,
                    infer_schema_length=0,
                    truncate_ragged_lines=True,
                    null_values="-",
                )
    return process_dataframe(df).with_row_index("uniqid")


def validate_js(json_file):
    return (
        pl.read_parquet(json_file)
        if json_file.endswith(".parquet")
        else pl.read_json(json_file)
    )


def displaying_df(filtred_apply=False):
    dff = SSDF.dataframe
    hide_waiver = SSDF.hide_waiver
    if dff.is_empty():
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
            request = SSDF.request
            request["groupKeys"] = []
            dff = apply_filters(dff, request)

            # if SSDF.tree_mode == "no-label-tree":
            #     dff = apply_tree(dff, request)
            # elif SSDF.tree_mode == "labeled-tree":
            #     dff = apply_labeled_tree(dff, request)
            #     dff = apply_sort(dff, request)
            # else:
            #     dff = apply_sort(dff, request)
            #     dff = apply_group(dff, request)
            dff = apply_sort(dff, request)
            dff = apply_group(dff, request)

    except Exception as e:
        logger.error(f"displaying_df Error : {e}")
    for col in ["childCount", "uniqid"]:
        if col in dff.columns:
            dff = dff.drop(col)
    return dff
