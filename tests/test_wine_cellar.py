import io

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


def add_tasting(client, **overrides):
    data = {
        "wine_name": "2018 Chateauneuf-du-Pape",
        "consumed_date": "2026-01-01",
    }
    data.update(overrides)
    return client.post("/wine-cellar/tastings/add", data=data, follow_redirects=True)


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
        data={"consumed_date": "2026-01-01", "notes": "Great with steak."},
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        bottle = db.session.get(Bottle, bottle_id)
        assert bottle.quantity == 1

        history = TastingHistory.query.one()
        assert history.wine_name == "2019 Barolo"
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


# ---------------------------------------------------------------------------
# Standalone tastings (no cellar bottle required)
# ---------------------------------------------------------------------------

def test_add_tasting_without_bottle(client, app):
    response = add_tasting(client, producer="Test Cellars", vintage="2018")
    assert response.status_code == 200
    assert b"2018 Chateauneuf-du-Pape" in response.data

    with app.app_context():
        history = TastingHistory.query.one()
        assert history.bottle_id is None
        assert history.wine_name == "2018 Chateauneuf-du-Pape"
        assert history.producer == "Test Cellars"
        assert history.vintage == 2018


def test_add_tasting_requires_wine_name(client, app):
    response = add_tasting(client, wine_name="")
    assert b"Wine name is required." in response.data
    with app.app_context():
        assert TastingHistory.query.count() == 0


def test_add_tasting_does_not_touch_cellar(client, app):
    add_bottle(client, quantity="2")
    add_tasting(client)
    with app.app_context():
        bottle = Bottle.query.one()
        assert bottle.quantity == 2


# ---------------------------------------------------------------------------
# Per-person scores
# ---------------------------------------------------------------------------

def test_tasting_scores_compute_average(client, app):
    add_tasting(client, taster_name=["Zach", "Sam"], score=["90", "80"])
    with app.app_context():
        history = TastingHistory.query.one()
        assert history.average_score == 85
        assert {s.taster_name: s.score for s in history.scores} == {"Zach": 90, "Sam": 80}


def test_tasting_with_invalid_score_shows_error_and_does_not_save(client, app):
    response = add_tasting(client, taster_name=["Zach"], score=["150"])
    assert b"must be a whole number between 0 and 100." in response.data
    with app.app_context():
        assert TastingHistory.query.count() == 0


# ---------------------------------------------------------------------------
# Image upload
# ---------------------------------------------------------------------------

def test_add_tasting_with_image_serves_back_identical_bytes(client, app):
    image_bytes = b"\x89PNG\r\n\x1a\nfake-but-good-enough-for-a-byte-round-trip"
    response = add_tasting(client, image=(io.BytesIO(image_bytes), "wine.png", "image/png"))
    assert response.status_code == 200

    with app.app_context():
        history = TastingHistory.query.one()
        tasting_id = history.id
        assert history.image == image_bytes
        assert history.image_mimetype == "image/png"

    image_response = client.get(f"/wine-cellar/tastings/{tasting_id}/image")
    assert image_response.status_code == 200
    assert image_response.data == image_bytes
    assert image_response.mimetype == "image/png"


def test_add_tasting_rejects_non_image_upload(client, app):
    response = add_tasting(client, image=(io.BytesIO(b"not an image"), "notes.txt", "text/plain"))
    assert b"Uploaded file must be an image." in response.data
    with app.app_context():
        assert TastingHistory.query.count() == 0


def test_tasting_image_404_when_none_uploaded(client, app):
    add_tasting(client)
    with app.app_context():
        tasting_id = TastingHistory.query.one().id
    assert client.get(f"/wine-cellar/tastings/{tasting_id}/image").status_code == 404


def test_tasting_image_404_for_unknown_tasting(client):
    assert client.get("/wine-cellar/tastings/9999/image").status_code == 404
