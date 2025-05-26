import dash_mantine_components as dmc

from components.menu.edit.item.add_column import AddColumn
from components.menu.edit.item.del_column import DelColumn
from components.menu.edit.item.type_change import TypeChanges
from components.menu.edit.item.formula import Formula
from components.menu.edit.item.split_column import SplitColumn
from components.menu.edit.item.rename_headers import RenameHeaders
from components.menu.edit.item.fill_nan_values import FillNanValues
from components.menu.edit.item.find_and_replace import FindAndReplace


class EditMenu:
    def __init__(self) -> None:
        self.add_column = AddColumn()
        self.del_column = DelColumn()
        self.type_changes = TypeChanges()
        self.formula = Formula()
        self.split_column = SplitColumn()
        self.rename_headers = RenameHeaders()
        self.fill_nan_values = FillNanValues()
        self.find_and_replace = FindAndReplace()

    def layout(self):
        return dmc.Group(
            [
                self.add_column.button_layout(),
                self.del_column.button_layout(),
                self.rename_headers.button_layout(),
                self.type_changes.button_layout(),
                self.fill_nan_values.button_layout(),
                self.split_column.button_layout(),
                self.find_and_replace.button_layout(),
                self.formula.button_layout(),
            ],
            gap=2,
        )

    def register_callbacks(self, app):
        self.add_column.register_callbacks(app)
        self.del_column.register_callbacks(app)
        self.type_changes.register_callbacks(app)
        self.formula.register_callbacks(app)
        self.split_column.register_callbacks(app)
        self.rename_headers.register_callbacks(app)
        self.fill_nan_values.register_callbacks(app)
        self.find_and_replace.register_callbacks(app)
