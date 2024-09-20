import dash
import argparse
from dash import DiskcacheManager
from dash_extensions.enrich import DashProxy
from flask import Flask
from utils.db_management import set_cache, APPCACHE
from components.layout import ResultViewer

dash._dash_renderer._set_react_version("18.2.0")

def parse_arguments() -> argparse.Namespace:
    """명령줄 인수를 파싱합니다."""
    parser = argparse.ArgumentParser(description="ResultViewer 옵션")
    parser.add_argument("-csv", "--csv", help="표시할 CSV")
    parser.add_argument("-tool", "--tool", default="")
    parser.add_argument("-host", "--host", default=None)
    parser.add_argument("-port", "--port", default=0, type=int)
    parser.add_argument("-lib", "--lib", default="")
    parser.add_argument("-cell", "--cell", default="")
    return parser.parse_args()

def setup_cache(args: argparse.Namespace) -> None:
    """디스크 캐시를 초기 값으로 설정합니다."""
    set_cache("init_csv", args.csv)
    set_cache("CP", {
        "host": args.host,
        "port": args.port,
        "lib": args.lib,
        "cell": args.cell,
        "tool": args.tool,
    })

def create_dash_app():
    """Dash 애플리케이션을 생성하고 구성합니다."""
    application = Flask(__name__)
    app = DashProxy(
        server=application,
        title="Signoff Result Viewer",
        suppress_callback_exceptions=True,
        prevent_initial_callbacks="initial_duplicate",
        background_callback_manager=DiskcacheManager(APPCACHE),
    )
    return application, app

def main() -> None:
    """애플리케이션의 진입점입니다."""
    args = parse_arguments()
    setup_cache(args)

    _, app = create_dash_app()

    result_viewer = ResultViewer(app)
    app.layout = result_viewer.layout()

    app.run(debug=True)

if __name__ == "__main__":
    main()
