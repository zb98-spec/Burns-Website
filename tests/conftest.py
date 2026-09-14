import pytest

from app import create_app
from app.blueprints.auth.models import User, UserProjectAccess
from app.blueprints.core.routes import PROJECTS
from app.extensions import db


@pytest.fixture
def app():
    app = create_app("config.Config")
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        WTF_CSRF_ENABLED=False,
    )

    with app.app_context():
        db.create_all()

    # Deliberately NOT wrapping `yield app` in `with app.app_context()`.
    # Flask's test client reuses an already-active app context instead of
    # pushing a fresh one per request when one's already on the stack — so
    # an ambient context held open for the whole test causes Flask-Login's
    # per-request `current_user` cache (stored on `g`, which is scoped to
    # the app context) to leak across different test clients used in the
    # same test. Keeping create_all/drop_all in their own short-lived
    # `with` blocks means no context is active while the test body actually
    # runs, so every test-client request gets its own isolated context.
    yield app

    with app.app_context():
        db.drop_all()


def _log_in(test_client, user):
    with test_client.session_transaction() as sess:
        # Flask-Login's session key; must be a string. login_user() itself
        # needs a request context, which a fixture doesn't have, so this
        # writes the session directly instead — the documented pattern for
        # testing Flask-Login-protected views. Must match User.get_id()'s
        # "<id>:<password_hash fingerprint>" format, since load_user()
        # rejects anything else as a stale/invalidated session.
        sess["_user_id"] = user.get_id()
        sess["_fresh"] = True


@pytest.fixture
def client(app):
    """A logged-in, non-admin user with access to every project — so all
    the existing feature tests keep exercising the same routes as before
    auth existed, without needing admin rights."""
    test_client = app.test_client()
    with app.app_context():
        user = User(username="testuser")
        user.set_password("testpassword123")
        db.session.add(user)
        db.session.flush()
        for project in PROJECTS:
            db.session.add(UserProjectAccess(user_id=user.id, project_key=project["key"]))
        db.session.commit()
        _log_in(test_client, user)
    return test_client


@pytest.fixture
def anon_client(app):
    """A fresh, unauthenticated client — for testing login/logout/redirect
    and permission-denied behavior."""
    return app.test_client()


@pytest.fixture
def admin_client(app):
    """A logged-in admin user (implicitly has access to everything)."""
    test_client = app.test_client()
    with app.app_context():
        user = User(username="testadmin", is_admin=True)
        user.set_password("testpassword123")
        db.session.add(user)
        db.session.commit()
        _log_in(test_client, user)
    return test_client
