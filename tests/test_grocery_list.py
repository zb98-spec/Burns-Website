from app.blueprints.grocery_list.models import GroceryItem
from app.extensions import db


def add_item(client, **overrides):
    data = {
        "name": "Milk",
        "category": "Dairy & Eggs",
        "quantity": "1 gallon",
        "note": "whole",
    }
    data.update(overrides)
    return client.post("/grocery-list/add", data=data, follow_redirects=True)


def test_add_item_appears_on_active_list(client):
    response = add_item(client)
    assert response.status_code == 200
    assert b"Milk" in response.data
    assert b"Dairy" in response.data


def test_add_item_requires_name(client, app):
    response = add_item(client, name="")
    assert b"Name is required." in response.data
    with app.app_context():
        assert GroceryItem.query.count() == 0


def test_add_item_defaults_unknown_category_to_other(client, app):
    add_item(client, category="Not A Real Category")
    with app.app_context():
        item = GroceryItem.query.first()
        assert item.category == "Other"


def test_edit_item_updates_fields(client, app):
    add_item(client)
    with app.app_context():
        item_id = GroceryItem.query.first().id

    response = client.post(
        f"/grocery-list/{item_id}/edit",
        data={"name": "Oat Milk", "category": "Dairy & Eggs"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Oat Milk" in response.data

    with app.app_context():
        item = db.session.get(GroceryItem, item_id)
        assert item.name == "Oat Milk"


def test_toggle_removes_item_from_active_list_but_keeps_it_in_catalog(client, app):
    add_item(client)
    with app.app_context():
        item_id = GroceryItem.query.first().id

    client.post(f"/grocery-list/{item_id}/toggle", data={"next": "index"})

    index_response = client.get("/grocery-list/")
    assert b"Milk" not in index_response.data

    catalog_response = client.get("/grocery-list/catalog")
    assert b"Milk" in catalog_response.data

    with app.app_context():
        item = db.session.get(GroceryItem, item_id)
        assert item.on_list is False


def test_toggle_back_on_from_catalog_readds_to_active_list(client, app):
    add_item(client)
    with app.app_context():
        item_id = GroceryItem.query.first().id
    client.post(f"/grocery-list/{item_id}/toggle", data={"next": "catalog"})

    client.post(f"/grocery-list/{item_id}/toggle", data={"next": "catalog"})

    index_response = client.get("/grocery-list/")
    assert b"Milk" in index_response.data


def test_delete_item_removes_it_entirely(client, app):
    add_item(client)
    with app.app_context():
        item_id = GroceryItem.query.first().id

    client.post(f"/grocery-list/{item_id}/delete", data={"next": "catalog"}, follow_redirects=True)

    with app.app_context():
        assert GroceryItem.query.count() == 0


def test_clear_all_turns_off_active_items_without_deleting(client, app):
    add_item(client, name="Milk")
    add_item(client, name="Eggs")

    client.post("/grocery-list/clear-all", follow_redirects=True)

    index_response = client.get("/grocery-list/")
    assert b"Milk" not in index_response.data
    assert b"Eggs" not in index_response.data

    with app.app_context():
        assert GroceryItem.query.count() == 2
        assert all(not item.on_list for item in GroceryItem.query.all())

    catalog_response = client.get("/grocery-list/catalog")
    assert b"Milk" in catalog_response.data
    assert b"Eggs" in catalog_response.data


def test_items_grouped_by_category(client):
    add_item(client, name="Apples", category="Produce")
    add_item(client, name="Milk", category="Dairy & Eggs")

    response = client.get("/grocery-list/")
    text = response.data.decode()
    # Produce sorts before Dairy & Eggs in the fixed category order.
    assert text.index("Produce") < text.index("Apples") < text.index("Dairy &amp; Eggs")
