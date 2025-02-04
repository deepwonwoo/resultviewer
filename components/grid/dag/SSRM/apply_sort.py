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
