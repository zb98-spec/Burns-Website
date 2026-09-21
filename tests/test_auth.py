import pytest

from app.blueprints.auth.models import User

PROJECT_ROUTES = [
    "/wine-cellar/",
    "/grocery-list/",
    "/recipe-tracker/",
    "/honeymoon/",
    "/investing/",
]


def create_account(client, **overrides):
    data = {
        "username": "newuser",
        "password": "password123",
        "confirm_password": "password123",
    }
    data.update(overrides)
    return client.post("/create-account", data=data, follow_redirects=True)


def test_create_account_succeeds_with_no_project_access(anon_client, app):
    response = create_account(anon_client)
    assert response.status_code == 200
    assert b"An admin needs to grant you access" in response.data

    with app.app_context():
        user = User.query.filter_by(username="newuser").first()
        assert user is not None
        assert user.is_admin is False
        assert user.project_access == []


def test_create_account_rejects_duplicate_username(anon_client, app):
    create_account(anon_client)
    anon_client.post("/logout")
    response = create_account(anon_client, username="newuser")
    assert b"already taken" in response.data

    with app.app_context():
        assert User.query.filter_by(username="newuser").count() == 1


def test_create_account_rejects_short_password(anon_client):
    response = create_account(anon_client, password="short", confirm_password="short")
    assert b"at least 8 characters" in response.data


def test_create_account_rejects_mismatched_passwords(anon_client):
    response = create_account(anon_client, password="password123", confirm_password="different123")
    assert b"do not match" in response.data


def test_login_succeeds_with_correct_credentials(anon_client, app):
    create_account(anon_client, username="loginuser")
    anon_client.post("/logout")

    response = anon_client.post(
        "/login",
        data={"username": "loginuser", "password": "password123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Projects" in response.data


def test_login_fails_with_wrong_password(anon_client):
    create_account(anon_client, username="loginuser2")
    anon_client.post("/logout")

    response = anon_client.post(
        "/login",
        data={"username": "loginuser2", "password": "wrongpassword"},
    )
    assert b"Invalid username or password." in response.data


def test_login_fails_with_unknown_username(anon_client):
    response = anon_client.post(
        "/login",
        data={"username": "nosuchuser", "password": "whatever123"},
    )
    assert b"Invalid username or password." in response.data


def test_logout_requires_post(anon_client):
    response = anon_client.get("/logout")
    assert response.status_code == 405


def test_anonymous_user_redirected_to_login(anon_client):
    response = anon_client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"] == "/login?next=/"


def test_next_param_round_trip_after_login(anon_client):
    create_account(anon_client, username="roundtrip")
    anon_client.post("/logout")

    response = anon_client.get("/wine-cellar/", follow_redirects=False)
    assert response.headers["Location"] == "/login?next=/wine-cellar/"

    login_response = anon_client.post(
        "/login",
        data={"username": "roundtrip", "password": "password123", "next": "/wine-cellar/"},
        follow_redirects=False,
    )
    # No wine_cellar access yet, but the redirect target itself is what's
    # under test here: it goes back to /wine-cellar/, not the dashboard.
    assert login_response.headers["Location"] == "/wine-cellar/"


def test_open_redirect_is_rejected(anon_client):
    create_account(anon_client, username="redirtest")
    anon_client.post("/logout")

    for malicious_next in ["https://evil.com", "//evil.com"]:
        response = anon_client.post(
            "/login",
            data={
                "username": "redirtest",
                "password": "password123",
                "next": malicious_next,
            },
            follow_redirects=False,
        )
        assert response.headers["Location"] == "/"
        anon_client.post("/logout")


@pytest.mark.parametrize("route", PROJECT_ROUTES)
def test_user_without_project_access_gets_403(anon_client, route):
    create_account(anon_client, username="noaccess")
    response = anon_client.get(route)
    assert response.status_code == 403


@pytest.mark.parametrize("route", PROJECT_ROUTES)
def test_user_with_project_access_gets_200(client, route):
    # `client` fixture already has access to every project.
    response = client.get(route)
    assert response.status_code == 200


def test_dashboard_hides_tiles_without_access(anon_client):
    create_account(anon_client, username="dashboardtest")
    response = anon_client.get("/")
    assert b"No bottles" not in response.data  # sanity: not accidentally on wine cellar page
    assert b"Wine Cellar Tracker" not in response.data
    assert b"Grocery List" not in response.data
    assert b"Recipe Tracker" not in response.data


def test_dashboard_shows_all_tiles_for_full_access_user(client):
    response = client.get("/")
    assert b"Wine Cellar Tracker" in response.data
    assert b"Grocery List" in response.data
    assert b"Recipe Tracker" in response.data


def test_create_admin_cli_command(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["create-admin", "--username", "clitest", "--password", "clipassword123"])
    assert "Admin user 'clitest' created." in result.output

    with app.app_context():
        user = User.query.filter_by(username="clitest").first()
        assert user is not None
        assert user.is_admin is True
        assert user.check_password("clipassword123")


def test_create_admin_cli_rejects_existing_username(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["create-admin", "--username", "dupe", "--password", "clipassword123"])
    result = runner.invoke(args=["create-admin", "--username", "dupe", "--password", "otherpassword123"])
    assert "already exists" in result.output

    with app.app_context():
        assert User.query.filter_by(username="dupe").count() == 1
