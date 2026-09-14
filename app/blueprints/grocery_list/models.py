from datetime import datetime

from app.extensions import db

# Defines both the allowed values and the display/grouping order.
CATEGORIES = [
    "Produce",
    "Dairy & Eggs",
    "Meat & Seafood",
    "Bakery",
    "Frozen",
    "Pantry",
    "Beverages",
    "Household",
    "Other",
]


class GroceryItem(db.Model):
    __tablename__ = "grocery_items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False, default="Other")
    quantity = db.Column(db.String(50))
    note = db.Column(db.String(300))
    on_list = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
