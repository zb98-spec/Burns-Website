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
    # Neon can silently close idle connections server-side; pre-ping tests a
    # pooled connection before use and transparently reconnects instead of
    # surfacing "SSL connection has been closed unexpectedly" as a 500.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Session cookie hardening. CSRF tokens (Flask-WTF) are deferred (see
    # FEATURE_BACKLOG.md), so SameSite=Lax is doing real work here: it stops
    # the session cookie from being sent on cross-site POSTs at all in
    # compliant browsers. SECURE defaults to "does DATABASE_URL look like
    # prod" but is explicitly overridable via SESSION_COOKIE_SECURE — needed
    # because local dev can also point DATABASE_URL at a real Postgres
    # database for testing (see DEVELOPMENT_PLAN.md) while still being
    # served over plain HTTP, where a hardcoded Secure cookie would silently
    # never get set, making login look like it worked and then immediately
    # appear logged-out.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get(
        "SESSION_COOKIE_SECURE", "true" if DATABASE_URL else "false"
    ).lower() == "true"

    # Investing API (separate service — see INVESTMENT_ENGINE_HANDOFF.md).
    # Server-to-server only: the API key never reaches the browser.
    INVESTING_API_URL = os.environ.get("INVESTING_API_URL", "http://localhost:8000")
    INVESTING_API_KEY = os.environ.get("INVESTING_API_KEY")
