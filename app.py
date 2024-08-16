import dash
dash._dash_renderer._set_react_version("18.2.0")
import argparse
from flask import Flask
from flaskwebgui import FlaskUI
from dash import DiskcacheManager
from dash_extensions.enrich import DashProxy
from components.RV import ResultViewer
from utils.process_helpers import preprocess, postprocess, get_monitor_size
from utils.db_management import CACHE


def main():
    """Entry point of the application."""
    parser = argparse.ArgumentParser(description="ResultViewer options")
    parser.add_argument("-csv", "--csv", help="CSV to Display")
    parser.add_argument("-tool", "--tool", default="")
    parser.add_argument("-host", "--host", default=None)
    parser.add_argument("-port", "--port", default=0, type=int)
    parser.add_argument("-lib", "--lib", default="")
    parser.add_argument("-cell", "--cell", default="")
    args = parser.parse_args()

    # add CrossProbing info to Disk cache CACHE
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

    # Initialize Flask and Dash
    application = Flask(__name__)
    app = DashProxy(
        server=application,
        title="Signoff Result Viewer",
        suppress_callback_exceptions=True,
        prevent_initial_callbacks="initial_duplicate",
        background_callback_manager=DiskcacheManager(CACHE),
    )

    # Initialize the layout of the app using ResultViewer component
    RV = ResultViewer(app)
    app.layout = RV.layout()

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
