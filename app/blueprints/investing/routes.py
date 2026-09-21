from flask import Blueprint, abort, render_template, request

from app.blueprints.auth.access import require_project_access

from .api_client import ACTIONS, call_action, get_action

investing_bp = Blueprint(
    "investing",
    __name__,
    template_folder="templates",
)


@investing_bp.before_request
def _check_access():
    require_project_access("investing")


@investing_bp.route("/")
def index():
    return render_template("investing/index.html", actions=ACTIONS, result=None, active_action=None)


@investing_bp.route("/run/<action_id>", methods=["POST"])
def run(action_id):
    action = get_action(action_id)
    if action is None:
        abort(404)
    result = call_action(action, request.form)
    return render_template(
        "investing/index.html",
        actions=ACTIONS,
        result=result,
        active_action=action_id,
        form_values=request.form,
    )
