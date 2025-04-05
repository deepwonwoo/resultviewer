from dash import html
from components.menu.edit.item.column_operations import Columns


class EditMenu:
    def __init__(self) -> None:
        self.cols = Columns()

    def layout(self):
        return self.cols.layout()

    def register_callbacks(self, app):
        self.cols.register_callbacks(app)
