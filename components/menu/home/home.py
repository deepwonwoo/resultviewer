import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from components.menu.home.item.open import Opener
from components.menu.home.item.ai import LLMAnalysis


class HomeMenu:

    def __init__(self):
        self.opener = Opener()
        self.ai = LLMAnalysis()

        
    def layout(self):
        return dbpc.ButtonGroup(
            [
                dbpc.Divider(),
                self.opener.layout(),
                dbpc.Divider(),
                self.ai.button_layout(),

            ],
            style={"height": 35}
        )

    def register_callbacks(self, app):
        self.opener.register_callbacks(app)
        self.ai.register_callbacks(app)
