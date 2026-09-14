from app.blueprints.recipe_tracker.models import Recipe, RecipeIngredient
from app.extensions import db


def add_recipe(client, **overrides):
    data = {
        "title": "Weeknight Chili",
        "instructions": "Brown the beef. Add everything else. Simmer 30 minutes.",
        "servings": "4-6",
        "prep_time_minutes": "15",
        "cook_time_minutes": "45",
        "cuisine": "American",
        "meal_type": "Dinner",
        "source_name": "Family recipe",
        "source_url": "",
        "ingredient_quantity": ["1", "1", "2"],
        "ingredient_unit": ["lb", "can", "cloves"],
        "ingredient_name": ["ground beef", "diced tomatoes", "garlic"],
    }
    data.update(overrides)
    return client.post("/recipe-tracker/new", data=data, follow_redirects=True)


def test_add_recipe_appears_in_list(client):
    response = add_recipe(client)
    assert response.status_code == 200
    assert b"Weeknight Chili" in response.data


def test_add_recipe_requires_title(client, app):
    response = add_recipe(client, title="")
    assert b"Title is required." in response.data
    with app.app_context():
        assert Recipe.query.count() == 0


def test_add_recipe_requires_at_least_one_ingredient(client, app):
    response = add_recipe(
        client, ingredient_quantity=[""], ingredient_unit=[""], ingredient_name=[""]
    )
    assert b"At least one ingredient is required." in response.data
    with app.app_context():
        assert Recipe.query.count() == 0


def test_recipe_detail_shows_ingredients_and_instructions(client, app):
    add_recipe(client)
    with app.app_context():
        recipe_id = Recipe.query.first().id

    response = client.get(f"/recipe-tracker/{recipe_id}")
    assert b"ground beef" in response.data
    assert b"garlic" in response.data
    assert b"Simmer 30 minutes." in response.data


def test_edit_recipe_updates_fields_and_ingredients(client, app):
    add_recipe(client)
    with app.app_context():
        recipe_id = Recipe.query.first().id

    response = client.post(
        f"/recipe-tracker/{recipe_id}/edit",
        data={
            "title": "Weeknight Chili (Spicy)",
            "instructions": "Brown the beef. Add everything else plus chili powder. Simmer 30 minutes.",
            "cuisine": "Mexican",
            "meal_type": "Dinner",
            "ingredient_quantity": ["1"],
            "ingredient_unit": ["lb"],
            "ingredient_name": ["ground beef"],
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Weeknight Chili (Spicy)" in response.data

    with app.app_context():
        recipe = db.session.get(Recipe, recipe_id)
        assert recipe.title == "Weeknight Chili (Spicy)"
        assert recipe.cuisine == "Mexican"
        assert [i.name for i in recipe.ingredients] == ["ground beef"]


def test_delete_recipe_removes_it_and_ingredients(client, app):
    add_recipe(client)
    with app.app_context():
        recipe_id = Recipe.query.first().id

    client.post(f"/recipe-tracker/{recipe_id}/delete", follow_redirects=True)

    with app.app_context():
        assert Recipe.query.count() == 0
        assert RecipeIngredient.query.count() == 0


def test_search_filters_by_title_and_ingredient(client):
    add_recipe(client, title="Weeknight Chili")
    add_recipe(
        client,
        title="Pancakes",
        cuisine="American",
        meal_type="Breakfast",
        ingredient_quantity=["2"],
        ingredient_unit=["cups"],
        ingredient_name=["flour"],
    )

    response = client.get("/recipe-tracker/?q=flour")
    assert b"Pancakes" in response.data
    assert b"Weeknight Chili" not in response.data


def test_filter_by_cuisine_and_meal_type(client):
    add_recipe(client, title="Weeknight Chili", cuisine="American", meal_type="Dinner")
    add_recipe(
        client,
        title="Pancakes",
        cuisine="American",
        meal_type="Breakfast",
        ingredient_quantity=["2"],
        ingredient_unit=["cups"],
        ingredient_name=["flour"],
    )

    response = client.get("/recipe-tracker/?meal_type=Breakfast")
    assert b"Pancakes" in response.data
    assert b"Weeknight Chili" not in response.data
