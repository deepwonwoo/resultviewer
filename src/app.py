import dash
import argparse
from dash import DiskcacheManager
from dash_extensions.enrich import DashProxy
from flask import Flask
from utils.db_management import set_cache, APPCACHE
from components.layout import ResultViewer

dash._dash_renderer._set_react_version("18.2.0")

def parse_arguments() -> argparse.Namespace:
    """명령줄 인수를 파싱하고 반환합니다."""
    parser = argparse.ArgumentParser(description="ResultViewer 옵션")
    parser.add_argument("-csv", "--csv", help="표시할 CSV 파일 경로")
    parser.add_argument("-tool", "--tool", default="", help="사용할 도구")
    parser.add_argument("-host", "--host", default=None, help="호스트 주소")
    parser.add_argument("-port", "--port", default=0, type=int, help="포트 번호")
    parser.add_argument("-lib", "--lib", default="", help="사용할 라이브러리")
    parser.add_argument("-cell", "--cell", default="", help="셀 정보")
    return parser.parse_args()

def setup_cache(args: argparse.Namespace) -> None:
    """명령줄 인수를 기반으로 디스크 캐시를 초기화합니다."""
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
    """애플리케이션의 메인 실행 함수입니다."""
    # 명령줄 인수 파싱
    args = parse_arguments()
    
    # 캐시 설정
    setup_cache(args)
    
    # Dash 앱 생성
    _, app = create_dash_app()
    
    # ResultViewer 인스턴스 생성 및 레이아웃 설정
    result_viewer = ResultViewer(app)
    app.layout = result_viewer.layout()
    
    # 앱 실행
    app.run(debug=True)

if __name__ == "__main__":
    main()