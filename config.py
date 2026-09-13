import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    # Neon Postgres connection string, e.g.
    # postgresql://user:password@ep-xxxx.neon.tech/dbname?sslmode=require
    # Only needed once a project blueprint actually starts reading/writing data.
    DATABASE_URL = os.environ.get("DATABASE_URL")
