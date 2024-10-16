import polars as pl
from utils.logging_utils import logger, debugging_decorator
from utils.db_management import SSDF


@debugging_decorator
def apply_filters(df, request):
    filterModel = request.get("filterModel")
    if not filterModel:
        SSDF.filtered_row_count = 0
        return df

    def apply_filter_condition(df, condition):
        col = condition["colId"]
        filter_type = condition.get("type")
        filter_value = condition.get("filter")

        if condition["filterType"] == "boolean":
            return df.filter(pl.col(col) == condition["type"])

        if filter_type in [
            "contains",
            "notContains",
            "startsWith",
            "notStartsWith",
            "endsWith",
            "notEndsWith",
        ]:
            method = getattr(pl.col(col).str, filter_type.replace("not", "").lower())
            expr = (
                method(filter_value)
                if "not" not in filter_type
                else ~method(filter_value)
            )
            return df.filter(expr)

        if filter_type in ["equals", "notEqual"]:
            return df.filter(
                pl.col(col) == filter_value
                if filter_type == "equals"
                else pl.col(col) != filter_value
            )

        if filter_type in ["blank", "notBlank"]:
            return df.filter(
                pl.col(col).is_null()
                if filter_type == "blank"
                else pl.col(col).is_not_null()
            )

        if condition["filterType"] == "number":
            if filter_type == "inRange":
                return df.filter(
                    pl.col(col).is_between(filter_value, condition.get("filterTo"))
                )
            comparisons = {
                "greaterThanOrEqual": ">=",
                "lessThanOrEqual": "<=",
                "lessThan": "<",
                "greaterThan": ">",
                "notEqual": "!=",
                "equals": "==",
            }
            return df.filter(
                eval(f"pl.col(col) {comparisons[filter_type]} filter_value")
            )

        return df

    def process_conditions(df, conditions, operator):
        if operator == "AND":
            for condition in conditions:
                df = (
                    process_conditions(df, condition["conditions"], condition["type"])
                    if "conditions" in condition
                    else apply_filter_condition(df, condition)
                )
        elif operator == "OR":
            filtered_dfs = [
                (
                    process_conditions(
                        df.clone(), condition["conditions"], condition["type"]
                    )
                    if "conditions" in condition
                    else apply_filter_condition(df.clone(), condition)
                )
                for condition in conditions
            ]
            df = pl.concat(filtered_dfs).unique(maintain_order=True)
        return df

    try:
        SSDF.filtered_row_count = 0
        df = (
            apply_filter_condition(df, filterModel)
            if "colId" in filterModel
            else process_conditions(
                df, filterModel["conditions"], filterModel.get("type", "AND")
            )
        )
        SSDF.filtered_row_count = len(df)
        return df
    except Exception as e:
        logger.error(f"Error in apply_filters: {e}")
        raise


@debugging_decorator
def apply_group(df, request):
    agg_function_mapping = {
        "avg": pl.mean,
        "count": pl.count,
        "first": pl.first,
        "last": pl.last,
        "min": pl.min,
        "max": pl.max,
        "sum": pl.sum,
    }

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
                row_counter_groupby = f"{len(group_counts['childCount']):,} "
                additional_hier_group_info = "("
                for i in range(len(groupKeys)):
                    if groupKeys[i] is None:
                        df = df.clear()
                        break
                    else:
                        df = df.filter(pl.col(groupBy[i]) == groupKeys[i])
                        if i + 1 < len(groupBy):
                            group_counts_next = df.group_by(groupBy[i + 1]).agg(
                                pl.len().alias("count")
                            )
                            total_count = len(group_counts_next["count"])
                            additional_hier_group_info += (
                                f"{groupKeys[i]}: {total_count}, "
                            )
                if additional_hier_group_info.endswith(", "):
                    row_counter_groupby += additional_hier_group_info[:-2] + ")"

                if len(groupKeys) != len(groupBy):
                    group_counts = df.group_by(groupBy[: len(groupKeys) + 1]).agg(
                        pl.len().alias("childCount")
                    )
                    df_agg = (
                        df.group_by(
                            groupBy[: len(groupKeys) + 1], maintain_order=True
                        ).agg(
                            [
                                agg_function_mapping[agg_func](col_name).alias(col_name)
                                for col_name, agg_func in agg.items()
                            ]
                        )
                        if agg
                        else df.group_by(
                            groupBy[: len(groupKeys) + 1], maintain_order=True
                        ).agg([pl.col("*").first()])
                    )
                    df = df_agg.join(
                        group_counts, on=groupBy[: len(groupKeys) + 1], how="left"
                    )
                    if "waiver" in df.columns and "waiver" not in groupBy:
                        df = df.drop("waiver").with_columns(pl.lit("").alias("waiver"))
                    df = df.with_columns(pl.lit(True).alias("group"))
                else:
                    df = df.with_columns(pl.lit(False).alias("group"))

            else:
                group_counts = df.group_by(groupBy[0]).agg(pl.len().alias("childCount"))

                df_agg = (
                    df.group_by(groupBy[: len(groupKeys) + 1], maintain_order=True).agg(
                        [
                            agg_function_mapping[agg_func](col_name).alias(col_name)
                            for col_name, agg_func in agg.items()
                        ]
                    )
                    if agg
                    else df.group_by(groupBy[0], maintain_order=True).agg(
                        [pl.first("*")]
                    )
                )
                df = df_agg.join(group_counts, on=groupBy[0], how="left")
                if "waiver" in df.columns and "waiver" not in groupBy:
                    df = df.drop("waiver").with_columns(pl.lit("").alias("waiver"))
                df = df.with_columns(pl.lit(True).alias("group"))
                row_counter_groupby = f"{len(df):,}"
        SSDF.groupby_row_count = row_counter_groupby
        return df

    except Exception as e:
        logger.error(f"Error in apply_group: {e}")
        raise


@debugging_decorator
def apply_sort(df, request):
    sort_model = request.get("sortModel")
    if not sort_model:
        return df

    try:
        sorting = [
            sort["colId"]
            for sort in sort_model
            if sort["colId"] != "ag-Grid-AutoColumn"
        ]
        asc = [
            sort["sort"] == "asc"
            for sort in sort_model
            if sort["colId"] != "ag-Grid-AutoColumn"
        ]
        groupBy = [col["id"] for col in request.get("rowGroupCols", [])]

        if groupBy and "childCount" in df.columns:
            group_sort = [s for s in sorting if s in groupBy]
            non_group_sort = [s for s in sorting if s not in groupBy]
            group_asc = [asc[sorting.index(s)] for s in group_sort]
            non_group_asc = [asc[sorting.index(s)] for s in non_group_sort]

            if group_sort:
                df = df.sort(by=["childCount"], descending=not group_asc[0])
            elif non_group_sort:
                df = df.with_columns(
                    [pl.col(col).cast(pl.Utf8) for col in non_group_sort]
                )
                df = df.sort(non_group_sort, descending=[not a for a in non_group_asc])
        else:
            df = df.sort(
                [s for s in sorting if s in df.columns],
                descending=[not a for a in asc if sorting[asc.index(a)] in df.columns],
            )

        return df
    except Exception as e:
        logger.error(f"Error in apply_sort: {e}")
        raise


@debugging_decorator
def extract_rows_from_data(request):
    print(f"request:{request}")
    try:
        dff = SSDF.dataframe
        SSDF.request = request
        dff = apply_filters(dff, request)
        # if SSDF.tree_mode == "no-label-tree":
        #     dff = apply_tree(dff, request)
        # elif SSDF.tree_mode == "labeled-tree":
        #     dff = apply_labeled_tree(dff, request)
        #     dff = apply_sort(dff, request)
        # else:
        #     dff = apply_sort(dff, request)
        #     dff = apply_group(dff, request)
        dff = apply_sort(dff, request)
        dff = apply_group(dff, request)
        dff = apply_sort(dff, request)
    except Exception as e:
        logger.error(f"extract_rows_from_data: {e}")
        dff = SSDF.dataframe
    start_row = request.get("startRow", 0)
    end_row = request.get("endRow", 1000)
    partial_df = dff.slice(start_row, end_row - start_row)
    return {"rowData": partial_df.to_dicts(), "rowCount": dff.height}
