import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import html

from components.menu.edit.item.add_column import AddColumn
from components.menu.edit.item.del_column import DelColumn
from components.menu.edit.item.add_row import AddRow
from components.menu.edit.item.type_change import TypeChanges
from components.menu.edit.item.formula import Formula
from components.menu.edit.item.combining_dataframes import CombiningDataframes
from components.menu.edit.item.split_column import SplitColumn
from components.menu.edit.item.rename_headers import RenameHeaders
from components.menu.edit.item.fill_nan_values import FillNanValues
from components.menu.edit.item.find_and_replace import FindAndReplace


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
        self.fill_nan_values = FillNanValues()
        self.find_and_replace = FindAndReplace()

    def layout(self):
        return dmc.Group([
            self.add_column.button_layout(),
            self.del_column.button_layout(),
            self.rename_headers.button_layout(),
            self.add_row.button_layout(),
            self.type_changes.button_layout(),
            self.formula.button_layout(),
            self.combining_dataframes.button_layout(),
            self.split_column.button_layout(),
            self.fill_nan_values.button_layout(), 
            self.find_and_replace.button_layout()
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
        self.fill_nan_values.register_callbacks(app)
        self.find_and_replace.register_callbacks(app)


