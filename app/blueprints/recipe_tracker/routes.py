from flask import Blueprint, render_template

recipe_tracker_bp = Blueprint(
    "recipe_tracker",
    __name__,
    template_folder="templates/recipe_tracker",
)


@recipe_tracker_bp.route("/")
def index():
    return render_template(
        "placeholder.html",
        project_name="Recipe Tracker",
    )
