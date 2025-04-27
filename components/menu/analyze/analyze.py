import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import html

from components.menu.analyze.item.ai import LLMAnalysis

class AnalyzeMenu:
    def __init__(self) -> None:
        self.ai = LLMAnalysis()
        # 향후 추가될 다른 기능들의 인스턴스 생성

    def layout(self):
        return dmc.Group([
            dbpc.Divider(),
            self.ai.button_layout(),
            dbpc.Divider(),
        ], gap=2)
    def register_callbacks(self, app):
        self.ai.register_callbacks(app)



