from utils.logging_utils import logger
from utils.db_management import SSDF
from components.grid.dag.SSRM.apply_sort import apply_sort
from components.grid.dag.SSRM.apply_filter import apply_filters
from components.grid.dag.SSRM.apply_group import apply_group


def extract_rows_from_data(request):
    # request:{'endRow': 1000,'filterModel': None,'groupKeys': [],'rowGroupCols': [],'sortModel': [],'startRow': 0,'valueCols': []}

    dff = SSDF.dataframe.lazy()
    SSDF.request = request
    
    dff = apply_filters(dff, request)
    
    dff = apply_group(dff, request)
    
    dff = apply_sort(dff, request)
    
    
    dff = dff.collect()
    
    start_row = request.get("startRow", 0)
    end_row = request.get("endRow", 1000)
    partial_df = dff.slice(start_row, end_row - start_row)

    return {"rowData": partial_df.to_dicts(), "rowCount": dff.height}
