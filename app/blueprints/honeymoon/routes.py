from flask import Blueprint, render_template

from app.blueprints.auth.access import require_project_access

honeymoon_bp = Blueprint(
    "honeymoon",
    __name__,
    template_folder="templates/honeymoon",
)


@honeymoon_bp.before_request
def _check_access():
    require_project_access("honeymoon")


@honeymoon_bp.route("/")
def index():
    return render_template(
        "placeholder.html",
        project_name="Honeymoon",
    )
