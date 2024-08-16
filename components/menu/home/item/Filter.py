import os
import datetime
import shutil
import subprocess
import dash_mantine_components as dmc
from dash import Input, Output, State, html, exceptions, ctx, no_update, ALL, dcc
from components.grid.DAG.columnDef import generate_column_definitions
from utils.process_helpers import *
from utils.db_management import (
    WORKSPACE,
    USERNAME,
    SCRIPT,
    CACHE,
    DATAFRAME,
    USER_RV_DIR,
)
from utils.process_helpers import create_notification, backup_file
from utils.logging_config import logger
from components.menu.home.item.fileExplorer import FileExplorer


class Filter:
    def __init__(self) -> None:
        self.max_filters = 10  # 최대 필터 수 설정 가능
        self.filter_yaml = f"{USER_RV_DIR}/filter.yaml"

    def filter_model_to_expression(self, filter_model):
        """필터 모델을 표현식으로 변환."""
        operator_map = {
            "contains": "contains",
            "notContains": "does not contain",
            "equals": "=",
            "notEqual": "!=",
            "startsWith": "begins with",
            "endsWith": "ends with",
            "blank": "is blank",
            "notBlank": "is not blank",
            "greaterThan": ">",
            "greaterThanOrEqual": ">=",
            "lessThan": "<",
            "lessThanOrEqual": "<=",
            "true": "is true",
            "false": "is false",
        }

        def build_expression(condition):
            if condition.get("filterType") == "join":
                expressions = [build_expression(c) for c in condition["conditions"]]
                join_type = " AND " if condition["type"] == "AND" else " OR "
                return f"({join_type.join(expressions)})"
            else:
                operator = operator_map.get(condition["type"], condition["type"])
                filter_value = (
                    f'"{condition["filter"]}"' if isinstance(condition["filter"], str) else condition["filter"]
                )
                return f"[{condition['colId']}] {operator} {filter_value}"

        return build_expression(filter_model)

    def layout(self):
        return dmc.Group(
            [
                dmc.Text(f"Filters: ", fw=500, size="sm", c="gray"),
                dmc.Tooltip(
                    dmc.ActionIcon(
                        get_icon("bx-filter-alt"),
                        variant="outline",
                        id="open-filter-storage-btn",
                        n_clicks=0,
                        color="grey",
                    ),
                    label="Open Filter Storage",
                    withArrow=True,
                    position="bottom",
                    color="grey",
                ),
                dcc.Store(id="advancedFilterModel-store"),
                self.store_filter_condition_modal(),
            ],
            gap=2,
        )

    def store_filter_condition_modal(self):
        """필터 저장 모달."""
        return dmc.Modal(
            title="Filter Storage",
            id="filter-store-modal",
            zIndex=1000,
            size="lg",
            children=[
                dmc.TextInput(
                    label="Current Filter:",
                    value="",
                    rightSection=dmc.Button(
                        "store",
                        id="store-filter-condition-btn",
                        size="xs",
                        variant="outline",
                        color="grey",
                        style={"width": 100},
                    ),
                    disabled=True,
                    rightSectionWidth=100,
                    required=True,
                    id="store-filter-condition-input",
                ),
                dmc.Space(h="sm"),
                dmc.List([], id="saved-filter-models", size="sm"),
                dmc.Space(h=20),
                dmc.Group(
                    [
                        dmc.Button(
                            "Clear Filters",
                            color="blue",
                            variant="outline",
                            id="clear-filters-btn",
                        ),
                        dmc.Button(
                            "Close",
                            color="red",
                            variant="outline",
                            id="close-filter-storage-btn",
                        ),
                    ],
                ),
            ],
        )
