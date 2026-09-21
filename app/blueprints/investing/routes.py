from flask import Blueprint, render_template

from app.blueprints.auth.access import require_project_access

investing_bp = Blueprint(
    "investing",
    __name__,
    template_folder="templates/investing",
)


@investing_bp.before_request
def _check_access():
    require_project_access("investing")


@investing_bp.route("/")
def index():
    return render_template(
        "placeholder.html",
        project_name="Investing",
    )
