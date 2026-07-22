from flask import Flask
from waitress import serve

from app.config import config
from app.routes.status import status_bp
from app.routes.today import today_bp
from app.routes.timeline import timeline_bp
from app.routes.history import history_bp
from app.routes.machine import machine_bp
from app.routes.export import export_bp


def create_app():
    app = Flask(
        __name__,
        template_folder="../web/templates",
        static_folder="../web/static",
        static_url_path="/static",
    )

    # Import Blueprints
    from app.routes.dashboard import dashboard_bp
    from app.routes.config import config_bp

    # Register Blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(status_bp)
    app.register_blueprint(today_bp)
    app.register_blueprint(timeline_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(machine_bp)
    app.register_blueprint(export_bp)

    return app


app = create_app()


if __name__ == "__main__":
    # Use Flask's development server only when DEBUG is enabled.
    if getattr(config, "DEBUG", False):
        app.run(
            host="0.0.0.0",
            port=8000,
            debug=True,
        )
    else:
        serve(
            app,
            host="0.0.0.0",
            port=8000,
            threads=8,
        )