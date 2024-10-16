import dash
import argparse
from flask import Flask, request
from flaskwebgui import FlaskUI
from dash import DiskcacheManager
from dash_extensions.enrich import DashProxy
from components.layout import ResultViewer
from utils.db_management import SSDF, get_ssdf
from utils.config import CONFIG

dash._dash_renderer._set_react_version("18.2.0")

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


app, application = create_dash_app()


@app.server.before_request
def initialize_ssdf():
    global SSDF
    # 새로운 앱 인스턴스에 대해 SSDF 초기화
    if request.endpoint == 'dash.index':
        SSDF = get_ssdf()


RV = ResultViewer(app)
app.layout = RV.layout()
app.run(debug=True)
