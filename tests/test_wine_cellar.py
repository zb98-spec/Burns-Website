from app.blueprints.wine_cellar.models import Bottle, TastingHistory
from app.extensions import db


def add_bottle(client, **overrides):
    data = {
        "name": "2019 Barolo",
        "producer": "Vietti",
        "vintage": "2019",
        "varietal": "Nebbiolo",
        "region": "Piedmont",
        "quantity": "3",
        "location": "Rack A3",
        "drink_window_start": "2024",
        "drink_window_end": "2030",
        "purchase_price": "45.00",
        "purchase_date": "2021-05-01",
        "purchase_source": "Local shop",
    }
    data.update(overrides)
    return client.post("/wine-cellar/add", data=data, follow_redirects=True)


def test_add_bottle_appears_in_list(client):
    response = add_bottle(client)
    assert response.status_code == 200
    assert b"2019 Barolo" in response.data
    assert b"Drink now" in response.data  # 2019-2030 window, current year in range


def test_add_bottle_requires_name(client, app):
    response = add_bottle(client, name="")
    assert b"Name is required." in response.data
    with app.app_context():
        assert Bottle.query.count() == 0


def test_edit_bottle_updates_fields(client, app):
    add_bottle(client)
    with app.app_context():
        bottle_id = Bottle.query.first().id

    response = client.post(
        f"/wine-cellar/{bottle_id}/edit",
        data={
            "name": "2019 Barolo Riserva",
            "quantity": "2",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"2019 Barolo Riserva" in response.data

    with app.app_context():
        bottle = db.session.get(Bottle, bottle_id)
        assert bottle.name == "2019 Barolo Riserva"
        assert bottle.quantity == 2


def test_drink_decrements_quantity_and_logs_history(client, app):
    add_bottle(client, quantity="2")
    with app.app_context():
        bottle_id = Bottle.query.first().id

    response = client.post(
        f"/wine-cellar/{bottle_id}/drink",
        data={"consumed_date": "2026-01-01", "rating": "92", "notes": "Great with steak."},
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        bottle = db.session.get(Bottle, bottle_id)
        assert bottle.quantity == 1

        history = TastingHistory.query.one()
        assert history.wine_name == "2019 Barolo"
        assert history.rating == 92
        assert history.notes == "Great with steak."


def test_bottle_disappears_from_list_when_quantity_hits_zero(client, app):
    add_bottle(client, quantity="1")
    with app.app_context():
        bottle_id = Bottle.query.first().id

    client.post(f"/wine-cellar/{bottle_id}/drink", data={"consumed_date": "2026-01-01"})

    response = client.get("/wine-cellar/")
    assert b"No bottles in the cellar yet." in response.data

    history_response = client.get("/wine-cellar/history")
    assert b"2019 Barolo" in history_response.data


def test_delete_bottle_removes_it(client, app):
    add_bottle(client)
    with app.app_context():
        bottle_id = Bottle.query.first().id

    client.post(f"/wine-cellar/{bottle_id}/delete", follow_redirects=True)

    with app.app_context():
        assert Bottle.query.count() == 0


def test_search_filters_bottles(client):
    add_bottle(client, name="2019 Barolo")
    add_bottle(client, name="2020 Chablis", varietal="Chardonnay", region="Burgundy")

    response = client.get("/wine-cellar/?q=chablis")
    assert b"2020 Chablis" in response.data
    assert b"2019 Barolo" not in response.data
