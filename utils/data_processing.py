import polars as pl
from collections import Counter
from utils.db_management import SSDF
from utils.logging_utils import logger
from components.grid.dag.server_side_operations import apply_filters


def file2df(csv_file_path):
    print("file2df")
    try:
        df = validate_df(csv_file_path)
    except:
        raise
    SSDF.dataframe = df
    SSDF.release_lock()
    return df


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
    print("process_dataframe")
    df = df.rename({col: col.strip() for col in df.columns})
    df = df.select([col for col in df.columns if col != ""])
    for col in df.columns:
        try:
            if df[col].dtype == pl.Utf8:
                df = df.with_columns(pl.col(col).str.strip_chars().alias(col))
            df = df.with_columns(pl.col(col).cast(pl.Float64()).alias(col))
            df = df.with_columns(pl.col(col).replace(float("inf"), -99999).fill_null(-99999).fill_nan(-99999).alias(col))
            if df[col].dtype == pl.Float64:
                if (df[col] == df[col].cast(pl.Int64())).sum() == len(df[col]):
                    df = df.with_columns(pl.col(col).cast(pl.Int64()).alias(col))
        except Exception:
            df = df.with_columns(pl.col(col).fill_null(""))
    return df


def validate_df(filename):
    print("validate_df")
    if filename.endswith(".parquet"):
        try:
            df = pl.read_parquet(filename)
        except Exception as e:
            logger.error(f"Fail to read parquet: {e}")
    else:
        try:
            df = pl.read_csv(filename, ignore_errors=True, infer_schema_length=0, separator=detect_separator(filename))
        except pl.PolarsError as e:
            if "truncate_ragged_lines=True" in str(e):
                df = pl.read_csv(filename, ignore_errors=True, infer_schema_length=0, truncate_ragged_lines=True)
    return process_dataframe(df).with_row_index("uniqid")


def validate_js(json_file):
    return pl.read_parquet(json_file) if json_file.endswith(".parquet") else pl.read_json(json_file)


def displaying_df(filtred_apply=False):
    dff = SSDF.dataframe
    if dff.is_empty():
        return None
    try:

        if filtred_apply:
            dff = apply_filters(dff, SSDF.request)
    except Exception as e:
        logger.error(f"displaying_df Error : {e}")
    for col in ["childCount", "uniqid"]:
        if col in dff.columns:
            dff = dff.drop(col)
    return dff





"""
def displaying_df(filtered_apply=False):
    try:
        dff = SSDF.dataframe.lazy()
        
        # 필터링 적용
        if filtered_apply and SSDF.request.get('filterModel'):
            dff = apply_filters(dff, SSDF.request)
        
        # 그룹화 적용 (기존 데이터 처리 파이프라인과 동일한 로직)
        if SSDF.request.get('rowGroupCols'):
            dff = apply_group(dff, SSDF.request)
            dff = apply_sort(dff, SSDF.request)
            
            # 그룹 계층 구조 평탄화
            dff = dff.with_columns(
                pl.when(pl.col("group") == True)
                .then(pl.col("childCount"))
                .otherwise(None)
                .alias("_is_group_row")
            )
        
        return dff.collect()
    
    except Exception as e:
        logger.error(f"Error preparing display DF: {e}")
        return SSDF.dataframe
"""