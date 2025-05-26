import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from components.menu.home.item.open import Opener


class HomeMenu:

    def __init__(self):
        self.opener = Opener()

    def layout(self):
        return dbpc.ButtonGroup(
            [
                dbpc.Divider(),
                self.opener.layout(),
                dbpc.Divider(),
            ],
            style={"height": 35},
        )

    def register_callbacks(self, app):
        self.opener.register_callbacks(app)
