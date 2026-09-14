from flask import Blueprint, render_template

honeymoon_bp = Blueprint(
    "honeymoon",
    __name__,
    template_folder="templates/honeymoon",
)


@honeymoon_bp.route("/")
def index():
    return render_template(
        "placeholder.html",
        project_name="Honeymoon",
    )
