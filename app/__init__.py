import os

from flask import Flask


def create_app(config_object: str | None = None) -> Flask:
    """Application factory. Registers each project's blueprint independently
    so new projects can be built out without touching existing ones."""
    app = Flask(__name__)

    app.config.from_object(config_object or os.environ.get("APP_CONFIG", "config.Config"))

    from app.blueprints.core.routes import core_bp
    from app.blueprints.wine_cellar.routes import wine_cellar_bp
    from app.blueprints.grocery_list.routes import grocery_list_bp
    from app.blueprints.recipe_tracker.routes import recipe_tracker_bp

    app.register_blueprint(core_bp)
    app.register_blueprint(wine_cellar_bp, url_prefix="/wine-cellar")
    app.register_blueprint(grocery_list_bp, url_prefix="/grocery-list")
    app.register_blueprint(recipe_tracker_bp, url_prefix="/recipe-tracker")

    return app
