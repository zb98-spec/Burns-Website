from flask import Blueprint, render_template
from flask_login import current_user

core_bp = Blueprint(
    "core",
    __name__,
    template_folder="templates",
)

# Each tile links to a project's index route. Status controls the badge
# shown on the landing page ("live" vs "coming soon"). "key" is the
# access-control identifier used by UserProjectAccess — independent of
# routing, so it stays stable even if a blueprint's URL prefix changes.
PROJECTS = [
    {
        "key": "wine_cellar",
        "name": "Wine Cellar Tracker",
        "description": "Track bottles, vintages, and drink windows.",
        "endpoint": "wine_cellar.index",
        "status": "live",
    },
    {
        "key": "grocery_list",
        "name": "Grocery List",
        "description": "A running household grocery list.",
        "endpoint": "grocery_list.index",
        "status": "live",
    },
    {
        "key": "recipe_tracker",
        "name": "Recipe Tracker",
        "description": "Save and organize recipes.",
        "endpoint": "recipe_tracker.index",
        "status": "live",
    },
    {
        "key": "honeymoon",
        "name": "Honeymoon",
        "description": "Plan the honeymoon.",
        "endpoint": "honeymoon.index",
        "status": "coming soon",
    },
]


@core_bp.route("/")
def index():
    visible_projects = [p for p in PROJECTS if current_user.has_access(p["key"])]
    return render_template("core/index.html", projects=visible_projects)
