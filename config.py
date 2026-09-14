import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    # Neon Postgres connection string, e.g.
    # postgresql://user:password@ep-xxxx.neon.tech/dbname?sslmode=require
    # Falls back to a local SQLite file so projects can be built out before
    # a Neon database is wired up.
    DATABASE_URL = os.environ.get("DATABASE_URL")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or "sqlite:///" + os.path.join(
        BASE_DIR, "instance", "dev.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
