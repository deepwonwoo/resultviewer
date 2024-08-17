import polars as pl
from typing import Dict, Any, List, Union
from enum import Enum

# 상수 정의
class ColumnType(Enum):
    NUMERIC = "numeric"
    STRING = "text"

class WaiverStatus(Enum):
    WAIVER = "Waiver"
    WAIVER_DOT = "Waiver."
    FIXED = "Fixed"
    FIXED_DOT = "Fixed."
    ERROR = "Error"

# 기본 열 정의
DEFAULT_COL_DEF: Dict[str, Any] = {
    "filter": True,
    "sortable": True,
    "resizable": True,
    "enableValue": True,
    "enablePivot": True,
    "enableRowGroup": True,
}


def determine_column_type(column_expr: pl.Expr) -> ColumnType:
    """Determine the most appropriate column type for AG Grid based on the Polars Series dtype."""
    if column_expr.dtype in (pl.Float64, pl.Int64):
        return ColumnType.NUMERIC
    return ColumnType.STRING




def generate_waiver_column_definition(column_name: str) -> Dict[str, Any]:
    return {
        "headerName": column_name,
        "field": column_name,
        "cellDataType": "text",
        "checkboxSelection": {"function": "params.data.group != true"},
        "cellStyle": {
            "styleConditions": [
                {"condition": f"params.data.waiver == '{status.value}'", 
                 "style": {"backgroundColor": color}}
                for status, color in [
                    (WaiverStatus.WAIVER, "lightskyblue"),
                    (WaiverStatus.WAIVER_DOT, "lightskyblue"),
                    (WaiverStatus.FIXED, "limegreen"),
                    (WaiverStatus.FIXED_DOT, "limegreen"),
                    (WaiverStatus.ERROR, "lightcoral"),
                ]
            ] + [{"condition": "params.data.waiver == ''", "style": {}}]
        },
        "editable": True,
        "cellClass": "text-dark"
    }


def generate_column_definition(
    column_name: str, 
    column_expr: pl.Expr, 
    col_hide: List[str] = [], 
    cellClassRules: Dict[str, str] = None, 
    is_editable: bool = False
) -> Dict[str, Any]:

    """    Generate a single column definition for AG Grid based on the column name and its Polars Series."""

    if column_name == "waiver":
        return generate_waiver_column_definition(column_name)

    col_def = {"headerName": column_name, "field": column_name}
    

    col_data_type = determine_column_type(column_expr)
    if col_data_type == ColumnType.STRING:
        col_def.update({"cellDataType": "text"})
    elif col_data_type == ColumnType.NUMERIC:
        col_def.update({"cellDataType": "number"})

    if column_name in col_hide:
        col_def.update({"hide": True})

    col_def["editable"] = is_editable
    col_def["cellClass"] = "text-dark" if col_def["editable"] else "text-secondary"


    if cellClassRules:
        col_def["cellClassRules"] = cellClassRules

    return col_def



def generate_column_definitions(df: pl.DataFrame, col_hide: List[str] = []) -> List[Dict[str, Any]]:

    """Generate column definitions for all columns in a Polars DataFrame suitable for AG Grid."""
    return [
        generate_column_definition(col, df[col], col_hide)
        for col in df.columns
        if col != "uniqid"
    ]