import polars as pl
from utils.db_management import SSDF
from utils.logging_utils import logger


def apply_sort(df, request):
    sortModel = request.get("sortModel")
    if not sortModel:
        return df
    try:
        sorting = [sort["colId"] for sort in sortModel if sort["colId"] != "ag-Grid-AutoColumn"]
        asc = [sort["sort"] == "asc" for sort in sortModel if sort["colId"] != "ag-Grid-AutoColumn"]
        groupBy = [col["id"] for col in request.get("rowGroupCols", [])]

        if len(groupBy) and "childCount" in df.columns:  # grouped row 확인
            group_sort = []
            group_asc = []
            non_group_sort = []
            non_group_asc = []
            for i, s in enumerate(sorting):
                if s in groupBy:
                    group_sort.append(s)
                    group_asc.append(asc[i])
                else:
                    non_group_sort.append(s)
                    non_group_asc.append(asc[i])
            if group_sort:
                df = df.sort(by=["childCount"], descending=group_asc[0])
            elif non_group_sort:
                for col in non_group_sort:
                    df = df.with_columns(pl.col(col).cast(pl.Utf8))
                df = df.sort(non_group_sort, descending=non_group_asc)
        else:
            updated_sorting = []
            updated_asc = []
            for i, s in enumerate(sorting):
                if s in df.columns:
                    updated_sorting.append(sorting[i])
                    updated_asc.append(asc[i])
            df = df.sort(updated_sorting, descending=updated_asc)
        return df
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
