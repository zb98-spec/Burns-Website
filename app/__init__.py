import os

import click
from flask import Flask

from app.extensions import db


def create_app(config_object: str | None = None) -> Flask:
    """Application factory. Registers each project's blueprint independently
    so new projects can be built out without touching existing ones."""
    app = Flask(__name__)

    app.config.from_object(config_object or os.environ.get("APP_CONFIG", "config.Config"))
    os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)

    db.init_app(app)

    from app.blueprints.core.routes import core_bp
    from app.blueprints.wine_cellar.routes import wine_cellar_bp
    from app.blueprints.grocery_list.routes import grocery_list_bp
    from app.blueprints.recipe_tracker.routes import recipe_tracker_bp

    app.register_blueprint(core_bp)
    app.register_blueprint(wine_cellar_bp, url_prefix="/wine-cellar")
    app.register_blueprint(grocery_list_bp, url_prefix="/grocery-list")
    app.register_blueprint(recipe_tracker_bp, url_prefix="/recipe-tracker")

    if not app.config["DATABASE_URL"]:
        # No real database configured yet — auto-create tables in the local
        # SQLite fallback so the app works without a manual init-db step.
        # This file lives in the container's own filesystem, so on Cloud Run
        # it's wiped whenever the instance restarts or scales: a throwaway
        # dev database, not persistent storage. See FEATURE_BACKLOG.md.
        with app.app_context():
            db.create_all()

    @app.cli.command("init-db")
    def init_db():
        """Create all database tables for every registered blueprint."""
        from app.blueprints.wine_cellar import models  # noqa: F401
        from app.blueprints.grocery_list import models  # noqa: F401

        db.create_all()
        click.echo("Database tables created.")

    return app
