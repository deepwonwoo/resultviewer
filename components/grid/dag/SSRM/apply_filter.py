import polars as pl
from utils.db_management import SSDF
from utils.logging_utils import logger


def apply_filters(df, request):
    filterModel = request.get("filterModel")
    if not filterModel:
        SSDF.filtered_row_count = ""
        return df

    def filterDf(dff, filter_model, col):
        if "filter" in filter_model:
            crit1 = filter_model["filter"]
        if filter_model["filterType"] == "boolean":
            dff = dff.filter(pl.col(col) == filter_model["type"])
        elif "type" in filter_model:
            if filter_model["type"] == "contains":
                dff = dff.filter(pl.col(col).str.contains(crit1))
            elif filter_model["type"] == "notContains":
                dff = dff.filter(~pl.col(col).str.contains(crit1))
            elif filter_model["type"] == "equals":
                dff = dff.filter(pl.col(col) == crit1)
            elif filter_model["type"] == "notEqual":
                dff = dff.filter(pl.col(col) != crit1)
            elif filter_model["type"] == "startsWith":
                dff = dff.filter(pl.col(col).str.starts_with(crit1))
            elif filter_model["type"] == "notStartsWith":
                dff = dff.filter(~pl.col(col).str.starts_with(crit1))
            elif filter_model["type"] == "endsWith":
                dff = dff.filter(pl.col(col).str.ends_with(crit1))
            elif filter_model["type"] == "notEndsWith":
                dff = dff.filter(~pl.col(col).str.ends_with(crit1))
            elif filter_model["type"] == "blank":
                dff = dff.filter(pl.col(col) == "")
            elif filter_model["type"] == "notBlank":
                dff = dff.filter(pl.col(col) != "")
            elif filter_model["filterType"] == "number" and filter_model["type"] == "inRange":
                if "filterTo" in filter_model:
                    crit2 = filter_model["filterTo"]
                    dff = dff.filter(pl.col(col).is_between(crit1, crit2))
            else:
                if filter_model["type"] == "greaterThanOrEqual":
                    dff = dff.filter(pl.col(col) >= crit1)
                elif filter_model["type"] == "lessThanOrEqual":
                    dff = dff.filter(pl.col(col) <= crit1)
                elif filter_model["type"] == "lessThan":
                    dff = dff.filter(pl.col(col) < crit1)
                elif filter_model["type"] == "greaterThan":
                    dff = dff.filter(pl.col(col) > crit1)
                elif filter_model["type"] == "notEqual":
                    dff = dff.filter(pl.col(col) != crit1)
                elif filter_model["type"] == "equals":
                    dff = dff.filter(pl.col(col) == crit1)
        return dff

    def apply_filter_condition(df, condition):
        col = condition["colId"]
        return filterDf(df, condition, col)

    def create_filter_expression(condition, col):
        filter_type = condition.get("type")
        filter_value = condition.get("filter")
        
        if filter_type == "contains":
            return pl.col(col).str.contains(filter_value)
        elif filter_type == "notContains":
            return ~pl.col(col).str.contains(filter_value)
        elif filter_type == "equals":
            return pl.col(col) == filter_value
        elif filter_type == "notEqual":
            return pl.col(col) != filter_value
        elif filter_type == "startsWith":
            return pl.col(col).str.starts_with(filter_value)
        elif filter_type == "notStartsWith":
            return ~pl.col(col).str.starts_with(filter_value)        
        elif filter_type == "endsWith":
            return pl.col(col).str.ends_with(filter_value)
        elif filter_type == "notEndsWith":
            return ~pl.col(col).str.ends_with(filter_value)
        
        elif filter_type == "blank":
            return pl.col(col) == ""
        elif filter_type == "notBlank":
            return pl.col(col) != ""
        
        # 숫자형 필터 처리
        if condition.get("filterType") == "number":
            if filter_type == "greaterThan":
                return pl.col(col) > filter_value
            elif filter_type == "lessThan":
                return pl.col(col) < filter_value
            elif filter_type == "greaterThanOrEqual":
                return pl.col(col) >= filter_value
            elif filter_type == "lessThanOrEqual":
                return pl.col(col) <= filter_value
            elif filter_type == "notEqual":
                return pl.col(col) != filter_value
            elif filter_type == "equals":
                return pl.col(col) == filter_value        
        
        raise ValueError(f"Unsupported filter type: {filter_type}")

    def process_conditions(df, conditions, operator):
        if operator == "AND":
            for condition in conditions:
                if "conditions" in condition:  # 중첩된 조건 처리
                    df = process_conditions(df, condition["conditions"], condition["type"])
                else:
                    df = apply_filter_condition(df, condition)
        elif operator == "OR":
            or_expressions = []
            for condition in conditions:
                if "conditions" in condition:
                    # 재귀적으로 중첩 조건 처리
                    nested_expr = process_conditions(df, condition["conditions"], condition["type"])
                    or_expressions.append(nested_expr)

                else:
                    # 개별 조건에 대한 필터 표현식 생성
                    col = condition["colId"]
                    filter_expr = create_filter_expression(condition, col)
                    or_expressions.append(filter_expr)
            # 모든 OR 조건을 단일 표현식으로 결합
            if or_expressions:
                combined_expr = pl.any_horizontal(or_expressions)
                df = df.filter(combined_expr)
        return df

    try:
        SSDF.filtered_row_count = ""
        if "colId" in filterModel:
            df = apply_filter_condition(df, filterModel)
        elif "conditions" in filterModel:
            operator = filterModel.get("type", "AND")
            df = process_conditions(df, filterModel["conditions"], operator)
        #SSDF.filtered_row_count = f"{len(df):,}"
        SSDF.filtered_row_count = f"{df.select(pl.count()).collect().item():,}"
        return df
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
