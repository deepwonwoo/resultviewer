import polars as pl
from utils.db_management import CACHE
from utils.logging_config import logger

# Default column definition for AG Grid
defaultColDef = {
    "filter": True,
    "sortable": True,
    "resizable": True,
    "enableValue": True,
    "enablePivot": True,
    "enableRowGroup": True,
}


def determine_column_type(column_expr):
    """Determine the most appropriate column type for AG Grid based on the Polars Series dtype."""
    if column_expr.dtype == pl.Float64 or column_expr.dtype == pl.Int64:
        return "numeric"
    else:
        return "string"


def generate_column_definition(column_name, column_expr, col_hide=[], cellClassRules=None, is_editable=False):
    """Generate a single column definition for AG Grid based on the column name and its Polars Series."""
    # col_def = {"headerName": column_name, "field": column_name, "headerComponent": "SelectColumn"}
    col_def = {"headerName": column_name, "field": column_name}

    col_data_type = determine_column_type(column_expr)
    if column_name == "waiver":
        col_def.update({"cellDataType": "text"})
        col_def.update({"checkboxSelection": {"function": "params.data.group != true"}})
        col_def.update(
            {
                "cellStyle": {
                    "styleConditions": [
                        {
                            "condition": "params.data.waiver == 'Waiver'",
                            "style": {"backgroundColor": "lightskyblue"},
                        },
                        {
                            "condition": "params.data.waiver == 'Waiver.'",
                            "style": {"backgroundColor": "lightskyblue"},
                        },
                        {
                            "condition": "params.data.waiver == 'Fixed'",
                            "style": {"backgroundColor": "limegreen"},
                        },
                        {
                            "condition": "params.data.waiver == 'Fixed.'",
                            "style": {"backgroundColor": "limegreen"},
                        },
                        {
                            "condition": "params.data.waiver == 'Error'",
                            "style": {"backgroundColor": "lightcoral"},
                        },
                        {
                            "condition": "params.data.waiver == ''",
                            "style": {},
                        },
                    ]
                }
            }
        )
    elif col_data_type == "string":
        col_def.update({"cellDataType": "text"})

    elif col_data_type == "numeric":
        col_def.update({"cellDataType": "number", "type": "rightAligned"})

    if column_name in col_hide:
        # col_def.update({"rowGroup": True}),
        col_def.update({"hide": True})
    # else:
    # col_def.update({"rowGroup": False}),
    # col_def.update({"hide": False})

    if is_editable or column_name == "waiver":
        col_def["editable"] = True
        col_def["cellClass"] = "text-dark"
    else:
        col_def["editable"] = False
        col_def["cellClass"] = "text-secondary"

    if cellClassRules:
        col_def["cellClassRules"] = cellClassRules

    return col_def


def generate_column_definitions(df, col_hide=[]):
    """Generate column definitions for all columns in a Polars DataFrame suitable for AG Grid."""
    column_defs = [generate_column_definition(col, df[col], col_hide) for col in df.columns if col != "uniqid"]

    return column_defs
