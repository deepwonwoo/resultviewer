import argparse
from typing import Dict, Any

import dash
from dash import DiskcacheManager
from dash_extensions.enrich import DashProxy
from flask import Flask
from flaskwebgui import FlaskUI

from components.layout import ResultViewer
from utils.db_management import CACHE
from utils.process_helpers import preprocess, postprocess, get_monitor_size

dash._dash_renderer._set_react_version("18.2.0")



def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="ResultViewer options")
    parser.add_argument("-csv", "--csv", help="CSV to Display")
    parser.add_argument("-tool", "--tool", default="")
    parser.add_argument("-host", "--host", default=None)
    parser.add_argument("-port", "--port", default=0, type=int)
    parser.add_argument("-lib", "--lib", default="")
    parser.add_argument("-cell", "--cell", default="")
    return parser.parse_args()



def setup_cache(args: argparse.Namespace) -> None:
    """Set up the disk cache with initial values."""
    CACHE.set("init_csv", args.csv)
    CACHE.set(
        "CP",
        {
            "host": args.host,
            "port": args.port,
            "lib": args.lib,
            "cell": args.cell,
            "tool": args.tool,
        },
    )


def create_dash_app() -> DashProxy:
    """Create and configure the Dash application."""
    application = Flask(__name__)
    app = DashProxy(
        server=application,
        title="Signoff Result Viewer",
        suppress_callback_exceptions=True,
        prevent_initial_callbacks="initial_duplicate",
        background_callback_manager=DiskcacheManager(CACHE),
    )
    return app



def main() -> None:
    """Entry point of the application."""
    args = parse_arguments()
    setup_cache(args)
    
    app = create_dash_app()

    # Initialize the layout of the app using ResultViewer component
    result_viewer = ResultViewer(app)
    app.layout = result_viewer.layout()
    
    app.run(debug=True)


    # Get monitor size and set FlaskUI parameters
    # width, height = get_monitor_size()
    # flask_ui_params = {
    #     "app": application,
    #     "server": "flask",
    #     "width": width,
    #     "height": height,
    #     "on_startup": preprocess,
    #     "on_shutdown": postprocess,
    # }
    # Run FlaskUI with the specified parameters
    # FlaskUI(**flask_ui_params).run()


if __name__ == "__main__":
    main()
