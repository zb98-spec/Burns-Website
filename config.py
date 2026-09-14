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

    # Session cookie hardening. CSRF tokens (Flask-WTF) are deferred (see
    # FEATURE_BACKLOG.md), so SameSite=Lax is doing real work here: it stops
    # the session cookie from being sent on cross-site POSTs at all in
    # compliant browsers. SECURE must stay conditional on DATABASE_URL being
    # set (i.e. "are we in prod") — local dev is plain HTTP, and a hardcoded
    # Secure cookie would silently never get set there, making login look
    # like it worked and then immediately appear logged-out.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = bool(DATABASE_URL)
