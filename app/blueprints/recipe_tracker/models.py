from datetime import datetime

from app.extensions import db

# Fixed lists, not database-backed tables — define both the allowed values
# and the dropdown order. Extend by editing here, no migration needed.
CUISINES = [
    "American",
    "Italian",
    "Mexican",
    "Chinese",
    "Indian",
    "French",
    "Mediterranean",
    "Thai",
    "Japanese",
    "Other",
]

MEAL_TYPES = [
    "Breakfast",
    "Lunch",
    "Dinner",
    "Dessert",
    "Snack",
    "Appetizer",
    "Side",
    "Drink",
]


class Recipe(db.Model):
    __tablename__ = "recipe_recipes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    servings = db.Column(db.String(50))
    prep_time_minutes = db.Column(db.Integer)
    cook_time_minutes = db.Column(db.Integer)
    cuisine = db.Column(db.String(50))
    meal_type = db.Column(db.String(50))
    source_url = db.Column(db.String(500))
    source_name = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    ingredients = db.relationship(
        "RecipeIngredient",
        backref="recipe",
        order_by="RecipeIngredient.sort_order",
        cascade="all, delete-orphan",
    )


class RecipeIngredient(db.Model):
    __tablename__ = "recipe_ingredients"

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(
        db.Integer, db.ForeignKey("recipe_recipes.id", ondelete="CASCADE"), nullable=False
    )
    quantity = db.Column(db.String(50))
    unit = db.Column(db.String(50))
    name = db.Column(db.String(200), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
