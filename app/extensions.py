from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
# render_as_batch: SQLite can't do most ALTER TABLE variants directly, so
# Alembic's "batch" mode (rebuild the table, copy data, swap) is needed for
# migrations to work against local SQLite, not just Neon Postgres.
migrate = Migrate(render_as_batch=True)
login_manager = LoginManager()
