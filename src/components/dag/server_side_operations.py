import pprint
import time
import traceback
import polars as pl
from utils.logging_utils import logger
from utils.db_management import CACHE, ROW_COUNTER, DATAFRAME


def apply_filters(df, request):
    def filterDf(dff, filter_model, col): 

        if "filter" in filter_model:
            crit1 = filter_model["filter"]

        if filter_model["filterType"] == "boolean":
            dff = dff.filter(pl.col(col) == filter_model["type"])
        elif "type" in filter_model:
            if filter_model["type"] == "contains":
                dff = dff.loc[dff[col].str.contains(crit1, na=False)]
            elif filter_model["type"] == "notContains":
                dff = dff.loc[~dff[col].str.contains(crit1, na=False)]

            elif filter_model["type"] == "equals":
                dff = dff.loc[dff[col] == crit1]
            elif filter_model["type"] == "notEqual":
                dff = dff.loc[dff[col] != crit1]

            elif filter_model["type"] == "startsWith":
                dff = dff.loc[dff[col].str.startswith(crit1, na=False)]
            elif filter_model["type"] == "notStartsWith":
                dff = dff.loc[~dff[col].str.startswith(crit1, na=False)]
            elif filter_model["type"] == "endsWith":
                dff = dff.loc[dff[col].str.endswith(crit1, na=False)]
            elif filter_model["type"] == "notEndsWith":
                dff = dff.loc[~dff[col].str.endswith(crit1, na=False)]
            elif filter_model["type"] == "blank":
                dff = dff.loc[dff[col].isnull()]
            elif filter_model["type"] == "notBlank":
                dff = dff.loc[~dff[col].isnull()]

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

    def filter_df(df, condition):
        col = condition["colId"]
        return filterDf(df, condition, col)

    def process_conditions(df, conditions, operator):
        if operator == "AND":
            for condition in conditions:
                if "conditions" in condition:  # 중첩된 조건 처리
                    df = process_conditions(df, condition["conditions"], condition["type"])
                else:
                    df = filter_df(df, condition)
        elif operator == "OR":
            expressions = []
            for condition in conditions:
                if "conditions" in condition:
                    temp_df = process_conditions(df.clone(), condition["conditions"], condition["type"])
                    expressions.append(temp_df)

                else:
                    temp_df = filter_df(df.clone(), condition)
                    expressions.append(temp_df)

            # OR 조건을 만족하는 모든 행을 포함하는 단일 DataFrame을 생성합니다.
            if expressions:
                # 첫 번째 DataFrame을 기준으로 시작
                final_df = expressions[0]
                for expr_df in expressions[1:]:
                    final_df = final_df.vstack(expr_df).unique(maintain_order=True)
                df = final_df
        return df

    filterModel = request.get("filterModel")
    try:
        global ROW_COUNTER
        ROW_COUNTER["filtered"] = 0
        if filterModel:
            if "colId" in filterModel:
                df = filter_df(df, filterModel)
            elif "conditions" in filterModel:
                operator = filterModel.get("type", "AND")
                df = process_conditions(df, filterModel["conditions"], operator)

            ROW_COUNTER["filtered"] = len(df)

        return df

    except Exception as e:
        logger.error(f"Error in apply_filters: {e}")
        logger.error(traceback.format_exc())
        raise


def apply_group(df, request):

    # 집계 함수 매핑 정의
    agg_function_mapping = {
        "avg": pl.mean,  # 평균
        "count": pl.count,  # 개수
        "first": pl.first,  # 첫 번째 값
        "last": pl.last,  # 마지막 값
        "min": pl.min,  # 최소값
        "max": pl.max,  # 최대값
        "sum": pl.sum,  # 합계
    }
    try:

        global ROW_COUNTER
        ROW_COUNTER["groupby"] = 0

        groupBy = [col["id"] for col in request.get("rowGroupCols", [])]
        groupKeys = request.get("groupKeys")
        agg = {col["id"]: col["aggFunc"] for col in request.get("valueCols", [])}

        if CACHE.get("hide_waiver") and "waiver" in df.columns:
            df = df.filter(~pl.col("waiver").str.ends_with("."))

        if groupBy:
            if groupKeys:
                group_counts = df.group_by(groupBy[0]).agg(pl.len().alias("childCount"))
                ROW_COUNTER["groupby"] = f"{len(group_counts['childCount'])} "

                additional_hier_group_info = "("

                for i in range(len(groupKeys)):
                    # 현재 그룹 키에 해당하는 데이터 필터링
                    if groupKeys[i] is None:
                        df = df.clear()
                        break
                    else:
                        df = df.filter(pl.col(groupBy[i]) == groupKeys[i])

                        # 다음 그룹화 컬럼에 대한 개수 정보 추가
                        if i + 1 < len(groupBy):
                            group_counts_next = df.group_by(groupBy[i + 1]).agg(pl.len().alias("count"))
                            total_count = len(group_counts_next["count"])
                            additional_hier_group_info += f"{groupKeys[i]}: {total_count}, "

                # 문자열 마무리 처리
                if additional_hier_group_info.endswith(", "):
                    ROW_COUNTER["groupby"] += additional_hier_group_info[:-2] + ")"

                # GROUPED_DF_CACHE[grouped_df_key[1:]] = df

                if len(groupKeys) != len(groupBy):
                    group_counts = df.group_by(groupBy[: len(groupKeys) + 1]).agg(pl.len().alias("childCount"))
                    # 제공된 agg에 따라 집계를 수행하거나, 없으면 각 그룹의 첫 번째 행을 선택
                    if agg:
                        # 그룹별 자식 수와 집계 결과를 합침
                        df = df_agg.join(group_counts, on=groupBy[: len(groupKeys) + 1], how="left")
                        df = df.sort(groupBy[len(groupKeys)])
                        if "waiver" in df.columns and "waiver" not in groupBy:
                            df = df.drop("waiver")
                            df = df.with_columns(pl.lit("").alias("waiver"))
                        df = df.with_columns(pl.lit(True).alias("group"))
                    else:
                        df = df.with_columns(pl.lit(False).alias("group"))
            else:

                group_counts = df.group_by(groupBy[0]).agg(pl.len().alias("childCount"))
                if agg:
                    # 집계 함수 매핑을 사용하여 집계 표현식 리스트 생성
                    agg_expressions = [
                        agg_function_mapping[agg_func](col_name).alias(col_name) for col_name, agg_func in agg.items()
                    ]
                    df_agg = df.group_by(groupBy[0]).agg(agg_expressions)

                else:
                    # 첫 번째 행 선택은 Polars에서 직접적인 메서드가 없으므로, head 메서드로 유사하게 처리할 수 있습니다.
                    df_agg = df.group_by(groupBy[0]).agg([pl.first("*")])

                df = df_agg.join(group_counts, on=groupBy[0], how="left")
                df = df.sort(groupBy[0])
                if "waiver" in df.columns and "waiver" not in groupBy:
                    df = df.drop("waiver")
                    df = df.with_columns(pl.lit("").alias("waiver"))
                df = df.with_columns(pl.lit(True).alias("group"))
                ROW_COUNTER["groupby"] = len(df)

        return df
    except Exception as e:
        logger.error(f"Error in apply_group: {e}")
        logger.error(traceback.format_exc())
        raise


def apply_sort(df, request):
    
    sortModel = request.get("sortModel")
    try:
        if sortModel:
            # 각 컬럼에 대한 정렬 방향을 설정합니다.
            sorting = [sort["colId"] for sort in sortModel if sort["colId"] != "ag-Grid-AutoColumn"]
            asc = [sort["sort"] == "asc" for sort in sortModel if sort["colId"] != "ag-Grid-AutoColumn"]

            groupBy = [col["id"] for col in request.get("rowGroupCols", [])]

            if len(groupBy) and "childCount" in df.columns:
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
                    # Convert necessary columns to a sortable type
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
        logger.error(f"Error in apply_sort: {e}")
        logger.error(traceback.format_exc())
        raise


def extract_rows_from_data(request):
    global DATAFRAME
    dff = DATAFRAME["df"]
    CACHE.set("REQUEST", request)
    logger.debug(f"request:\n{pprint.pformat(request)}")
    try:
        # Measure time for applying filters
        start_time = time.time()
        dff = apply_filters(dff, request)
        filter_time = time.time() - start_time
        logger.debug(f"filter time : {filter_time} / {dff.height}")

        start_time = time.time()
        dff = apply_sort(dff, request)
        sort_time = time.time() - start_time
        logger.debug(f"sort time : {sort_time} / {dff.height}")

        if CACHE.get("TreeMode"):
            start_time = time.time()
            # dff = apply_tree(dff, request)
            tree_time = time.time() - start_time
            logger.debug(f"tree time : {tree_time}")
        else:
            start_time = time.time()
            dff = apply_group(dff, request)
            group_time = time.time() - start_time
            logger.debug(f"group time : {group_time} / {dff.height}")
            start_time = time.time()
            dff = apply_sort(dff, request)
            sort_time = time.time() - start_time
            logger.debug(f"group sort time : {sort_time} / {dff.height}")

    except Exception as e:
        logger.error(f"extract_rows_from_data: {e}")
        time.sleep(0.1)
        dff = DATAFRAME["df"]

    # 결과 데이터 슬라이싱
    start_row = request.get("startRow", 0)
    end_row = request.get("endRow", 1000)
    partial_df = dff.slice(start_row, end_row - start_row)

    return {
        "rowData": partial_df.to_dicts(),
        "rowCount": dff.height,
    }
