import dash_mantine_components as dmc

# from components.menu.script.item.chart_editor import ChartEditor
from components.menu.script.item.data_comparison import Compare
from components.menu.script.item.rule_table import RuleTable


class ScriptMenu:

    def __init__(self) -> None:
        # self.chart = ChartEditor()
        # self.profile = PandasProfile()
        self.compare = Compare()
        # self.masterName = MasterName()
        # self.categorizePart = CategorizePart()
        # self.diffUpdate = DiffUpdate()
        # self.migrateWaiver = MigrateWaiver()
        self.ruleTable = RuleTable()

    def layout(self):
        return dmc.Group(
            [
                # self.chart.layout(),
                dmc.Divider(orientation="vertical"),
                # self.profile.layout(),
                dmc.Divider(orientation="vertical"),
                self.compare.layout(),
                dmc.Divider(orientation="vertical"),
                self.ruleTable.layout(),
                # self.masterName.layout(),
                dmc.Divider(orientation="vertical"),
                # self.categorizePart.layout(),
                dmc.Divider(orientation="vertical"),
                # self.diffUpdate.layout(),
                dmc.Divider(orientation="vertical"),
                # self.migrateWaiver.layout(),
                dmc.Divider(orientation="vertical"),
            ],
            justify="flex-start",
            gap="xs",
        )

    def register_callbacks(self, app):
        # self.chart.register_callbacks(app)
        # self.profile.register_callbacks(app)
        self.compare.register_callbacks(app)
        self.ruleTable.register_callbacks(app)
        # self.masterName.register_callbacks(app)
        # self.categorizePart.register_callbacks(app)
        # self.diffUpdate.register_callbacks(app)
        # self.migrateWaiver.register_callbacks(app)
