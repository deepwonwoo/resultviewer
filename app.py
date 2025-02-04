import dash
import argparse
from flask import Flask, request
from flaskwebgui import FlaskUI
from dash import DiskcacheManager
from dash_extensions.enrich import DashProxy
from components.layout import ResultViewer
from utils.db_management import SSDF
from utils.config import CONFIG

dash._dash_renderer._set_react_version("18.2.0")

parser = argparse.ArgumentParser(description="ResultViewer options")
parser.add_argument("-csv", "--csv", help="표시할 CSV 파일 경로")
args = parser.parse_args()
SSDF.init_csv = args.csv


def create_dash_app():
    application = Flask(__name__)
    app = DashProxy(
        server=application,
        title="Signoff Result Viewer",
        suppress_callback_exceptions=True,
        prevent_initial_callbacks="initial_duplicate",
        background_callback_manager=DiskcacheManager(CONFIG.APPCACHE),
    )
    return app, application


app, application = create_dash_app()


RV = ResultViewer(app)
app.layout = RV.layout()
app.run(debug=True)
