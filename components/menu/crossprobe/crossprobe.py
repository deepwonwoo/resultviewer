import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from components.menu.crossprobe.item.schemeditor import SchemEditor


class CrossProbeMenu:

    def __init__(self):
        self.schem = SchemEditor()

    def layout(self):
        return dbpc.ButtonGroup(
            [dbpc.Divider(), self.schem.layout()], style={"height": 35}
        )

    def register_callbacks(self, app):

        self.schem.register_callbacks(app)
