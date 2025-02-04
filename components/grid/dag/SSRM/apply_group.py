import polars as pl
from utils.db_management import SSDF
from components.grid.dag.SSRM.apply_sort import apply_sort
from utils.logging_utils import logger


def apply_group(df, request):

    agg_function_mapping = {"avg": pl.mean, "count": pl.count, "first": pl.first, "last": pl.last, "min": pl.min, "max": pl.max, "sum": pl.sum}
    try:
        groupBy = [col["id"] for col in request.get("rowGroupCols", [])]
        groupKeys = request.get("groupKeys")
        agg = {col["id"]: col["aggFunc"] for col in request.get("valueCols", [])}
        row_counter_groupby = ""
        if SSDF.hide_waiver and "waiver" in df.columns:
            df = df.filter(~pl.col("waiver").str.ends_with("."))
        if groupBy:
            if groupKeys:
                group_counts = df.group_by(groupBy[0]).agg(pl.len().alias("childCount"))
                #row_counter_groupby = f"{len(group_counts['childCount']):,} "
                row_counter_groupby = f"{group_counts.select(pl.count()).collect().item():,} "
                additional_hier_group_info = "("
                for i in range(len(groupKeys)):
                    if groupKeys[i] is None:
                        df = df.clear()
                        break
                    else:
                        df = df.filter(pl.col(groupBy[i]) == groupKeys[i])  # 현재 그룹 키에 해당하는 데이터 필터링
                        if i + 1 < len(groupBy):  # 다음 그룹화 컬럼에 대한 개수 정보 추가
                            group_counts_next = df.group_by(groupBy[i + 1]).agg(pl.len().alias("count"))  # 다음 그룹별 행 개수 계산
                            total_count = group_counts_next.select(pl.col("count")).collect().height # 전체 개수 (이 그룹에 속하는 모든 하위 그룹의 수)
                            additional_hier_group_info += f"{groupKeys[i]}: {total_count:,}, "  # 추가적인 계층 그룹 정보 문자열에 현재 그룹 키와 다음 그룹의 전체 개수 정보 추가
                if additional_hier_group_info.endswith(", "):  # 문자열 마무리 처리
                    row_counter_groupby += additional_hier_group_info[:-2] + ")"
                if len(groupKeys) != len(groupBy):
                    group_counts = df.group_by(groupBy[: len(groupKeys) + 1]).agg(pl.len().alias("childCount"))
                    if agg:  # 제공된 agg에 따라 집계를 수행하거나,
                        agg_expressions = [agg_function_mapping[agg_func](col_name).alias(col_name) for col_name, agg_func in agg.items()]
                        df_agg = df.group_by(groupBy[: len(groupKeys) + 1], maintain_order=True).agg(agg_expressions)
                    else:  # 없으면 각 그룹의 첫 번째 행을 선택
                        df_agg = df.group_by(groupBy[: len(groupKeys) + 1], maintain_order=True).agg([pl.col("*").first()])

                    df = df_agg.join(group_counts, on=groupBy[: len(groupKeys) + 1], how="left")  # 그룹별 자식 수와 집계 결과를 합침
                    if "waiver" in df.columns and "waiver" not in groupBy:
                        df = df.drop("waiver")
                        df = df.with_columns(pl.lit("").alias("waiver"))
                    df = df.with_columns(pl.lit(True).alias("group"))
                else:
                    df = df.with_columns(pl.lit(False).alias("group"))
            else:
                group_counts = df.group_by(groupBy[0]).agg(pl.len().alias("childCount"))  # no group_keys
                if agg:
                    agg_expressions = [
                        agg_function_mapping[agg_func](col_name).alias(col_name) for col_name, agg_func in agg.items()
                    ]  # 집계 함수 매핑을 사용하여 집계 표현식 리스트 생성
                    df_agg = df.group_by(groupBy[: len(groupKeys) + 1], maintain_order=True).agg(agg_expressions)
                else:
                    df_agg = df.group_by(groupBy[0], maintain_order=True).agg([pl.first("*")])
                df = df_agg.join(group_counts, on=groupBy[0], how="left")  # 그룹별 자식 수와 집계 결과를 합침
                if "waiver" in df.columns and "waiver" not in groupBy:
                    df = df.drop("waiver")
                    df = df.with_columns(pl.lit("").alias("waiver"))
                df = df.with_columns(pl.lit(True).alias("group"))
                #row_counter_groupby = f"{len(df):,}"
                row_counter_groupby = f"{df.select(pl.count()).collect().item():,}"
                
        SSDF.groupby_row_count = row_counter_groupby
        
        # 정렬을 그룹화 단계에 병합
        sortModel = request.get("sortModel", [])
        sorting = [sort["colId"] for sort in sortModel if sort["colId"] != "ag-Grid-AutoColumn"]
        asc = [sort["sort"] == "asc" for sort in sortModel if sort["colId"] != "ag-Grid-AutoColumn"]
        if len(groupBy) and "childCount" in df.collect_schema().names(): # grouped row 확인
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
                # 그룹 컬럼 정렬 시 childCount를 기준으로 정렬
                sort_columns = ["childCount"] + group_sort
                sort_directions = [group_asc[0]] + group_asc
                df = df.sort(
                    by=sort_columns,
                    descending=sort_directions
                )

                #df = df.sort(by=["childCount"], descending=group_asc[0])

                # 추가 그룹 컬럼이 있는 경우 2차 정렬 수행
                if len(group_sort) > 1:
                    df = df.sort(by=group_sort[1:], descending=group_asc[1:])

            elif non_group_sort:
                for col in non_group_sort:
                    df = df.with_columns(pl.col(col).cast(pl.Utf8))
                df = df.sort(non_group_sort, descending=non_group_asc)

        return df
    
        



        # 정렬 시 groupKeys 길이에 맞는 descending 리스트 생성
        sort_columns = groupBy[: len(groupKeys) + 1]
        descending = [False] * len(sort_columns)
        return df.sort(
            sort_columns,
            descending=descending,
            maintain_order=True
        )
    
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
