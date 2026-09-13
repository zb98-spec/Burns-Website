from flask import Blueprint, render_template

wine_cellar_bp = Blueprint(
    "wine_cellar",
    __name__,
    template_folder="templates/wine_cellar",
)


@wine_cellar_bp.route("/")
def index():
    return render_template(
        "placeholder.html",
        project_name="Wine Cellar Tracker",
    )
