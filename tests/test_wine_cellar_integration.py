"""Integration tests: full HTTP request/response cycles through the app
factory, routing, templates, and the SQLite-backed database, exercising
multi-step flows across the wine cellar, core dashboard, and placeholder
blueprints."""

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


# ---------------------------------------------------------------------------
# Cross-blueprint navigation
# ---------------------------------------------------------------------------

def test_dashboard_lists_all_three_projects(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Wine Cellar Tracker" in response.data
    assert b"Grocery List" in response.data
    assert b"Recipe Tracker" in response.data


def test_grocery_list_is_live(client):
    response = client.get("/grocery-list/")
    assert response.status_code == 200
    assert b"Grocery List" in response.data


def test_recipe_tracker_is_live(client):
    response = client.get("/recipe-tracker/")
    assert response.status_code == 200
    assert b"Recipe Tracker" in response.data


# ---------------------------------------------------------------------------
# Full bottle lifecycle: add -> edit -> drink -> drink again -> delete
# ---------------------------------------------------------------------------

def test_full_bottle_lifecycle(client, app):
    add_bottle(client, quantity="2")
    with app.app_context():
        bottle_id = Bottle.query.one().id

    # Edit: resubmitting the full form should persist every field.
    edit_response = client.post(
        f"/wine-cellar/{bottle_id}/edit",
        data={
            "name": "2019 Barolo Riserva",
            "producer": "Vietti",
            "vintage": "2019",
            "varietal": "Nebbiolo",
            "region": "Piedmont",
            "quantity": "2",
            "location": "Rack A3",
            "drink_window_start": "2024",
            "drink_window_end": "2030",
        },
        follow_redirects=True,
    )
    assert edit_response.status_code == 200
    assert b"Updated 2019 Barolo Riserva." in edit_response.data

    # Drink once: quantity drops, still visible in the list.
    client.post(
        f"/wine-cellar/{bottle_id}/drink",
        data={"consumed_date": "2026-01-01", "rating": "90"},
        follow_redirects=True,
    )
    list_response = client.get("/wine-cellar/")
    assert b"2019 Barolo Riserva" in list_response.data

    # Drink again: quantity hits zero, bottle drops out of the active list.
    client.post(
        f"/wine-cellar/{bottle_id}/drink",
        data={"consumed_date": "2026-01-02", "rating": "88"},
        follow_redirects=True,
    )
    empty_list_response = client.get("/wine-cellar/")
    assert b"No bottles in the cellar yet." in empty_list_response.data

    with app.app_context():
        assert TastingHistory.query.count() == 2

    # Delete: the bottle row is gone, but tasting history survives with
    # bottle_id nulled out rather than being cascade-deleted.
    client.post(f"/wine-cellar/{bottle_id}/delete", follow_redirects=True)
    with app.app_context():
        assert Bottle.query.count() == 0
        histories = TastingHistory.query.all()
        assert len(histories) == 2
        assert all(h.bottle_id is None for h in histories)
        # History snapshots the name as of the time it was drunk, i.e. after
        # the rename to "Riserva" above.
        assert all(h.wine_name == "2019 Barolo Riserva" for h in histories)

    history_response = client.get("/wine-cellar/history")
    assert history_response.status_code == 200
    assert history_response.data.count(b"2019 Barolo Riserva") >= 2


def test_edit_with_partial_form_clears_unset_fields(client, app):
    """The edit route rebuilds the record from whatever fields are posted;
    omitted optional fields are written back as None rather than left
    untouched. This is surprising round-trip behavior worth pinning down."""
    add_bottle(client)
    with app.app_context():
        bottle_id = Bottle.query.one().id

    client.post(
        f"/wine-cellar/{bottle_id}/edit",
        data={"name": "2019 Barolo", "quantity": "2"},
        follow_redirects=True,
    )

    with app.app_context():
        bottle = db.session.get(Bottle, bottle_id)
        assert bottle.producer is None
        assert bottle.region is None
        assert bottle.drink_window_start is None


# ---------------------------------------------------------------------------
# Validation round-trips preserve user input
# ---------------------------------------------------------------------------

def test_add_with_invalid_data_rerenders_form_with_entered_values(client):
    response = add_bottle(client, name="", producer="Vietti")
    assert b"Name is required." in response.data
    assert b"Vietti" in response.data


def test_add_with_inverted_drink_window_shows_error_and_does_not_save(client, app):
    response = add_bottle(client, drink_window_start="2030", drink_window_end="2020")
    assert b"Drink window start must be before or equal to the end year." in response.data
    with app.app_context():
        assert Bottle.query.count() == 0


# ---------------------------------------------------------------------------
# Drinking edge cases
# ---------------------------------------------------------------------------

def test_drink_blocked_when_quantity_is_zero(client, app):
    add_bottle(client, quantity="0")
    with app.app_context():
        bottle_id = Bottle.query.one().id

    response = client.get(f"/wine-cellar/{bottle_id}/drink", follow_redirects=True)
    assert b"There are no bottles left to drink." in response.data
    with app.app_context():
        assert TastingHistory.query.count() == 0


def test_drink_without_notes_logs_history_with_nulls(client, app):
    add_bottle(client, quantity="1")
    with app.app_context():
        bottle_id = Bottle.query.one().id

    client.post(
        f"/wine-cellar/{bottle_id}/drink",
        data={"consumed_date": "2026-01-01"},
        follow_redirects=True,
    )
    with app.app_context():
        history = TastingHistory.query.one()
        assert history.notes is None
        assert history.average_score is None


# ---------------------------------------------------------------------------
# 404s for unknown bottles
# ---------------------------------------------------------------------------

def test_edit_unknown_bottle_returns_404(client):
    assert client.get("/wine-cellar/9999/edit").status_code == 404


def test_drink_unknown_bottle_returns_404(client):
    assert client.get("/wine-cellar/9999/drink").status_code == 404


def test_delete_unknown_bottle_returns_404(client):
    assert client.post("/wine-cellar/9999/delete").status_code == 404


# ---------------------------------------------------------------------------
# Search across multiple persisted rows
# ---------------------------------------------------------------------------

def test_search_is_case_insensitive_across_fields(client):
    add_bottle(client, name="2019 Barolo", producer="Vietti", region="Piedmont")
    add_bottle(
        client,
        name="2020 Chablis",
        producer="Louis Jadot",
        varietal="Chardonnay",
        region="Burgundy",
    )

    by_producer = client.get("/wine-cellar/?q=VIETTI")
    assert b"2019 Barolo" in by_producer.data
    assert b"2020 Chablis" not in by_producer.data

    by_region = client.get("/wine-cellar/?q=burgundy")
    assert b"2020 Chablis" in by_region.data
    assert b"2019 Barolo" not in by_region.data


def test_search_with_no_matches_shows_message(client):
    add_bottle(client, name="2019 Barolo")
    response = client.get("/wine-cellar/?q=nonexistent-wine")
    assert b"No bottles matching" in response.data
    assert b"2019 Barolo" not in response.data


def test_wine_cellar_pages_have_no_dashboard_back_link(client, app):
    """The dashboard link now lives only in the top bar (base.html); the old
    per-page 'Back to dashboard' paragraph was removed from the wine cellar
    pages specifically."""
    add_bottle(client, quantity="1")
    with app.app_context():
        bottle_id = Bottle.query.one().id
    for path in (
        "/wine-cellar/",
        "/wine-cellar/history",
        f"/wine-cellar/{bottle_id}/edit",
        f"/wine-cellar/{bottle_id}/drink",
    ):
        response = client.get(path)
        assert b"Back to dashboard" not in response.data


# ---------------------------------------------------------------------------
# Two pages: Wine Cellar and Wine Tasting cross-link, and a standalone
# tasting shows up on the tasting page without ever touching the cellar.
# ---------------------------------------------------------------------------

def test_wine_cellar_and_tasting_pages_cross_link(client):
    cellar_response = client.get("/wine-cellar/")
    assert b'href="/wine-cellar/history"' in cellar_response.data

    tasting_response = client.get("/wine-cellar/history")
    assert b'href="/wine-cellar/"' in tasting_response.data
    assert b'href="/wine-cellar/tastings/add"' in tasting_response.data


def test_standalone_tasting_appears_on_tasting_page_not_cellar(client, app):
    client.post(
        "/wine-cellar/tastings/add",
        data={"wine_name": "2015 Pinot Noir", "consumed_date": "2026-01-01"},
        follow_redirects=True,
    )
    cellar_response = client.get("/wine-cellar/")
    assert b"2015 Pinot Noir" not in cellar_response.data

    tasting_response = client.get("/wine-cellar/history")
    assert b"2015 Pinot Noir" in tasting_response.data


# ---------------------------------------------------------------------------
# Tasting card: average-score badge and per-taster hover breakdown
# ---------------------------------------------------------------------------

def test_tasting_card_shows_average_badge_and_per_taster_breakdown(client, app):
    add_bottle(client, quantity="1")
    with app.app_context():
        bottle_id = Bottle.query.one().id

    client.post(
        f"/wine-cellar/{bottle_id}/drink",
        data={
            "consumed_date": "2026-01-01",
            "taster_name": ["Zach", "Sam"],
            "score": ["90", "80"],
        },
    )

    response = client.get("/wine-cellar/history")
    assert b'badge badge--score">85</span>' in response.data
    assert b"Zach: 90" in response.data
    assert b"Sam: 80" in response.data


def test_history_orders_entries_most_recent_first(client, app):
    add_bottle(client, quantity="2")
    with app.app_context():
        bottle_id = Bottle.query.one().id

    client.post(
        f"/wine-cellar/{bottle_id}/drink",
        data={"consumed_date": "2025-01-01", "notes": "older tasting"},
    )
    client.post(
        f"/wine-cellar/{bottle_id}/drink",
        data={"consumed_date": "2026-01-01", "notes": "newer tasting"},
    )

    with app.app_context():
        entries = TastingHistory.query.order_by(TastingHistory.consumed_date.desc()).all()
        assert [e.notes for e in entries] == ["newer tasting", "older tasting"]

    response = client.get("/wine-cellar/history")
    newer_pos = response.data.find(b"newer tasting")
    older_pos = response.data.find(b"older tasting")
    assert newer_pos != -1 and older_pos != -1
    assert newer_pos < older_pos
