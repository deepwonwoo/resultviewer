from dash import html
from components.menu.edit.item.column_operations import Columns
from components.menu.edit.item.column_order import ColumnOrder


class EditMenu:
    def __init__(self) -> None:
        self.cols = Columns()
        self.colOrder = ColumnOrder()

    def layout(self):
        return html.Div(
            [self.cols.layout()],
            className="d-grid gap-2 d-md-flex justify-content-md-start m-2",
        )

    def register_callbacks(self, app):
        self.cols.register_callbacks(app)
        self.colOrder.register_callbacks(app)
