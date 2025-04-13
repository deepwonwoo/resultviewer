import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import html

from components.menu.edit.item.add_column import AddColumn
from components.menu.edit.item.del_column import DelColumn
from components.menu.edit.item.add_row import AddRow
from components.menu.edit.item.del_row import DelRow
# 향후 추가될 다른 기능들의 import 문

class EditMenu:
    def __init__(self) -> None:
        self.add_column = AddColumn()
        self.del_column = DelColumn()
        self.add_row = AddRow()
        self.del_row = DelRow()

        # 향후 추가될 다른 기능들의 인스턴스 생성

    def layout(self):
        return dmc.Group([
            dbpc.Divider(),
            # 컬럼 관련 버튼들
            dmc.Group([
                self.add_column.button_layout(),
                self.del_column.button_layout(),
            ], gap=2),
            dbpc.Divider(),
            # 행 관련 버튼들
            dmc.Group([
                self.add_row.button_layout(),
                self.del_row.button_layout(),
            ], gap=2),
            dbpc.Divider(),
            # 향후 추가될 다른 기능들의 버튼 레이아웃
        ], gap=2)
    def register_callbacks(self, app):
        self.add_column.register_callbacks(app)
        self.del_column.register_callbacks(app) 
        self.add_row.register_callbacks(app)
        self.del_row.register_callbacks(app)




