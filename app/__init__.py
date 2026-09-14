import os

import click
from flask import Flask, redirect, request, url_for
from flask_login import current_user

from app.extensions import db, login_manager, migrate


def create_app(config_object: str | None = None) -> Flask:
    """Application factory. Registers each project's blueprint independently
    so new projects can be built out without touching existing ones."""
    app = Flask(__name__)

    app.config.from_object(config_object or os.environ.get("APP_CONFIG", "config.Config"))
    os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        from app.blueprints.auth.models import User

        return db.session.get(User, int(user_id))

    from app.blueprints.core.routes import core_bp
    from app.blueprints.wine_cellar.routes import wine_cellar_bp
    from app.blueprints.grocery_list.routes import grocery_list_bp
    from app.blueprints.recipe_tracker.routes import recipe_tracker_bp
    from app.blueprints.honeymoon.routes import honeymoon_bp
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.admin.routes import admin_bp

    app.register_blueprint(core_bp)
    app.register_blueprint(wine_cellar_bp, url_prefix="/wine-cellar")
    app.register_blueprint(grocery_list_bp, url_prefix="/grocery-list")
    app.register_blueprint(recipe_tracker_bp, url_prefix="/recipe-tracker")
    app.register_blueprint(honeymoon_bp, url_prefix="/honeymoon")
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Whole site requires login. Exempt only the routes needed to get a
    # session in the first place, plus static files.
    _EXEMPT_ENDPOINTS = {"auth.login", "auth.create_account", "static"}

    @app.before_request
    def require_login():
        if request.endpoint is None or request.endpoint in _EXEMPT_ENDPOINTS:
            return
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))

    if not app.config["DATABASE_URL"]:
        # No real database configured yet — auto-create tables in the local
        # SQLite fallback so the app works with zero setup. This file lives
        # in the container's own filesystem, so on Cloud Run it's wiped
        # whenever the instance restarts or scales: a throwaway dev
        # database, not persistent storage. See FEATURE_BACKLOG.md.
        #
        # This is separate from migrations (below): a real database
        # (DATABASE_URL set, e.g. Neon) is always managed via
        # `flask db upgrade`, never auto-created, so schema changes go
        # through a reviewable migration script instead of being applied
        # silently.
        with app.app_context():
            db.create_all()

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(username, password):
        """Create an admin user. Run once to bootstrap the first admin."""
        from app.blueprints.auth.models import User

        username = username.strip().lower()
        if User.query.filter_by(username=username).first() is not None:
            click.echo(f"User '{username}' already exists.")
            return

        user = User(username=username, is_admin=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Admin user '{username}' created.")

    return app
