import polars as pl
import dash_mantine_components as dmc

from dash import html, Input, Output, State, ALL, MATCH, no_update, exceptions, ctx, dcc
from utils.db_management import DATAFRAME, CACHE, USERNAME
from components.dag.column_definitions import generate_column_definitions
from utils.process_helpers import create_notification
from utils.logging_utils import logger
from components.menu.edit.item.column_operations import Columns
from components.menu.edit.item.column_order import columnOrder
#from components.menu.edit.item.item.propagation import Propagation


class EditMenu:
    def __init__(self) -> None:
        self.cols = Columns()
        self.colOrder = columnOrder()
        #self.propagation = Propagation()

    def layout(self):
        return html.Div(
            [
                self.cols.layout(),
            ],
            className="d-grid gap-2 d-md-flex justify-content-md-start m-2",
        )

    def register_callbacks(self, app):
        self.cols.register_callbacks(app)
        self.colOrder.register_callbacks(app)
        #self.propagation.register_callbacks(app)
