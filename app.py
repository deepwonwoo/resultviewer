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

# from utils.options import upload_to_workspace
# from utils.devworks_api import send_devworks_message

dash._dash_renderer._set_react_version("18.2.0")


def parse_arguments():
    parser = argparse.ArgumentParser(description="ResultViewer options")
    parser.add_argument("-csv", "--csv", help="표시할 CSV 파일 경로")
    parser.add_argument("-tool", "--tool", default="", help="사용할 도구")
    parser.add_argument("-host", "--host", default=None, help="호스트 주소")
    parser.add_argument("-port", "--port", default=0, type=int, help="포트 번호")
    parser.add_argument("-lib", "--lib", default="", help="사용할 라이브러리")
    parser.add_argument("-cell", "--cell", default="", help="셀 정보")

    args = parser.parse_args()
    SSDF.init_csv = args.csv
    SSDF.cp = {
        "host": args.host,
        "port": args.port,
        "lib": args.lib,
        "cell": args.cell,
        "tool": args.tool,
    }


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
