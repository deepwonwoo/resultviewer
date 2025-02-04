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

  def process_conditions(df, conditions, operator):
    if operator == "AND":
      for condition in conditions:
        if "conditions" in condition:  # 중첩된 조건 처리
          df = process_conditions(df, condition["conditions"], condition["type"])
        else:
          df = apply_filter_condition(df, condition)
    elif operator == "OR":
      expressions = []
      for condition in conditions:
        if "conditions" in condition:
          temp_df = process_conditions(df.clone(), condition["conditions"], condition["type"])
          expressions.append(temp_df)
        else:
          temp_df = apply_filter_condition(df.clone(), condition)
          expressions.append(temp_df)
      # OR 조건을 만족하는 모든 행을 포함하는 단일 DataFrame을 생성
      if expressions:
        # 첫 번째 DataFrame을 기준으로 시작
        final_df = expressions[0]
        for expr_df in expressions[1:]:
          final_df = final_df.vstack(expr_df).unique(maintain_order=True)
        df = final_df
    return df

  try:
    SSDF.filtered_row_count = ""
    if "colId" in filterModel:
      df = apply_filter_condition(df, filterModel)
    elif "conditions" in filterModel:
      operator = filterModel.get("type", "AND")
      df = process_conditions(df, filterModel["conditions"], operator)
    SSDF.filtered_row_count = f"{len(df):,}"
    return df
  except Exception as e:
    logger.error(f"Error: {e}")
    raise