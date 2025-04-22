import os
import sys
import dash
import argparse
import screeninfo
from flask import Flask
from flaskwebgui import FlaskUI, get_free_port
from dash import DiskcacheManager
from dash_extensions.enrich import DashProxy
from components.RV import ResultViewer
from utils.config import CONFIG
from utils.db_management import SSDF

dash._dash_renderer._set_react_version("18.2.0")


def parse_arguments():
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


def main():
    parse_arguments()
    app, application = create_dash_app()
    RV = ResultViewer(app)
    app.layout = RV.layout()
    app.run(debug=True)


if __name__ == "__main__":
    main()
