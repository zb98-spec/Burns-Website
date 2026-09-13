from flask import Blueprint, render_template

core_bp = Blueprint(
    "core",
    __name__,
    template_folder="templates",
)

# Each tile links to a project's index route. Status controls the badge
# shown on the landing page ("live" vs "coming soon").
PROJECTS = [
    {
        "name": "Wine Cellar Tracker",
        "description": "Track bottles, vintages, and drink windows.",
        "endpoint": "wine_cellar.index",
        "status": "live",
    },
    {
        "name": "Grocery List",
        "description": "A running household grocery list.",
        "endpoint": "grocery_list.index",
        "status": "coming soon",
    },
    {
        "name": "Recipe Tracker",
        "description": "Save and organize recipes.",
        "endpoint": "recipe_tracker.index",
        "status": "coming soon",
    },
]


@core_bp.route("/")
def index():
    return render_template("core/index.html", projects=PROJECTS)
