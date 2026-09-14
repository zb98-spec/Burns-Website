from app.blueprints.auth.models import User, UserProjectAccess
from app.extensions import db


def create_account(client, username, **overrides):
    data = {"username": username, "password": "password123", "confirm_password": "password123"}
    data.update(overrides)
    return client.post("/create-account", data=data, follow_redirects=True)


def test_admin_panel_rejected_for_non_admin(client):
    response = client.get("/admin/")
    assert response.status_code == 403


def test_admin_panel_rejected_for_anonymous(anon_client):
    response = anon_client.get("/admin/")
    # Global login-required redirect fires before the admin check.
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_admin_panel_lists_users(admin_client, anon_client):
    create_account(anon_client, "listeduser")
    response = admin_client.get("/admin/")
    assert response.status_code == 200
    assert b"listeduser" in response.data
    assert b"testadmin" in response.data


def test_admin_can_grant_and_revoke_project_access(admin_client, anon_client, app):
    create_account(anon_client, "granttest")
    with app.app_context():
        user_id = User.query.filter_by(username="granttest").first().id

    # Grant
    admin_client.post(f"/admin/users/{user_id}/toggle-project/wine_cellar")
    with app.app_context():
        assert (
            UserProjectAccess.query.filter_by(user_id=user_id, project_key="wine_cellar").count()
            == 1
        )
    assert anon_client.get("/wine-cellar/").status_code == 200

    # Revoke (toggle again)
    admin_client.post(f"/admin/users/{user_id}/toggle-project/wine_cellar")
    with app.app_context():
        assert (
            UserProjectAccess.query.filter_by(user_id=user_id, project_key="wine_cellar").count()
            == 0
        )
    assert anon_client.get("/wine-cellar/").status_code == 403


def test_admin_cannot_toggle_unknown_project_key(admin_client, app):
    with app.app_context():
        user_id = User.query.filter_by(username="testadmin").first().id
    response = admin_client.post(f"/admin/users/{user_id}/toggle-project/not-a-real-project")
    assert response.status_code == 404


def test_admin_can_promote_and_demote_other_user(admin_client, anon_client, app):
    create_account(anon_client, "promotee")
    with app.app_context():
        user_id = User.query.filter_by(username="promotee").first().id

    admin_client.post(f"/admin/users/{user_id}/toggle-admin")
    with app.app_context():
        assert db.session.get(User, user_id).is_admin is True

    admin_client.post(f"/admin/users/{user_id}/toggle-admin")
    with app.app_context():
        assert db.session.get(User, user_id).is_admin is False


def test_admin_cannot_demote_self(admin_client, app):
    with app.app_context():
        admin_id = User.query.filter_by(username="testadmin").first().id

    response = admin_client.post(f"/admin/users/{admin_id}/toggle-admin", follow_redirects=True)
    assert b"can&#39;t change your own admin status" in response.data or b"can't change your own admin status" in response.data
    with app.app_context():
        assert db.session.get(User, admin_id).is_admin is True


def test_admin_can_reset_a_users_password(admin_client, anon_client, app):
    create_account(anon_client, "resettarget")
    with app.app_context():
        user_id = User.query.filter_by(username="resettarget").first().id

    admin_client.post(f"/admin/users/{user_id}/set-password", data={"password": "newpassword123"})

    login_response = anon_client.post(
        "/login",
        data={"username": "resettarget", "password": "newpassword123"},
        follow_redirects=True,
    )
    assert b"Projects" in login_response.data


def test_admin_password_reset_rejects_short_password(admin_client, anon_client, app):
    create_account(anon_client, "shortpwtarget")
    with app.app_context():
        user_id = User.query.filter_by(username="shortpwtarget").first().id

    response = admin_client.post(
        f"/admin/users/{user_id}/set-password", data={"password": "short"}, follow_redirects=True
    )
    assert b"at least 8 characters" in response.data
