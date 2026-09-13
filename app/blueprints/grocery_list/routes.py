from flask import Blueprint, render_template

grocery_list_bp = Blueprint(
    "grocery_list",
    __name__,
    template_folder="templates/grocery_list",
)


@grocery_list_bp.route("/")
def index():
    return render_template(
        "placeholder.html",
        project_name="Grocery List",
    )
