from dash import html
from components.menu.edit.item.column_operations import Columns

from components.menu.edit.item.add_column import AddColumn
from components.menu.edit.item.del_column import DelColumn
from components.menu.edit.item.add_row import AddRow
from components.menu.edit.item.type_change import TypeChanges
from components.menu.edit.item.formula import Formula
from components.menu.edit.item.combining_dataframes import CombiningDataframes
from components.menu.edit.item.split_column import SplitColumn
from components.menu.edit.item.rename_headers import RenameHeaders

class EditMenu:
    def __init__(self) -> None:
        self.add_column = AddColumn()
        self.del_column = DelColumn()
        self.add_row = AddRow()
        self.type_changes = TypeChanges()
        self.formula = Formula()  
        self.combining_dataframes = CombiningDataframes()
        self.split_column = SplitColumn()
        self.rename_headers = RenameHeaders() 

    def layout(self):
        return dmc.Group([
            dbpc.Divider(),
            dmc.Group([
                self.add_column.button_layout(),
                self.del_column.button_layout(),
                self.rename_headers.button_layout()
            ], gap=2),
            dbpc.Divider(),
            self.add_row.button_layout(),
            dbpc.Divider(),
            self.type_changes.button_layout(),
            dbpc.Divider(),
            self.formula.button_layout(),
            dbpc.Divider(),
            self.combining_dataframes.button_layout(),
            dbpc.Divider(),
            self.split_column.button_layout(),

        ], gap=2)
    def register_callbacks(self, app):
        self.add_column.register_callbacks(app)
        self.del_column.register_callbacks(app) 
        self.add_row.register_callbacks(app)
        self.type_changes.register_callbacks(app)
        self.formula.register_callbacks(app)
        self.combining_dataframes.register_callbacks(app)
        self.split_column.register_callbacks(app)
        self.rename_headers.register_callbacks(app)


