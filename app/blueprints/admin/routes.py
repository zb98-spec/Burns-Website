from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.blueprints.auth.models import User, UserProjectAccess
from app.blueprints.core.routes import PROJECTS
from app.extensions import db

admin_bp = Blueprint(
    "admin",
    __name__,
    template_folder="templates",
)

MIN_PASSWORD_LENGTH = 8


@admin_bp.before_request
@login_required
def require_admin():
    if not current_user.is_admin:
        abort(403)


@admin_bp.route("/")
def index():
    users = User.query.order_by(User.username.asc()).all()
    granted = {(row.user_id, row.project_key) for row in UserProjectAccess.query.all()}
    return render_template(
        "admin/users.html", users=users, projects=PROJECTS, granted=granted
    )


@admin_bp.route("/users/<int:user_id>/toggle-project/<project_key>", methods=["POST"])
def toggle_project(user_id, project_key):
    user = db.get_or_404(User, user_id)
    if project_key not in {p["key"] for p in PROJECTS}:
        abort(404)

    existing = UserProjectAccess.query.filter_by(
        user_id=user.id, project_key=project_key
    ).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(UserProjectAccess(user_id=user.id, project_key=project_key))
    db.session.commit()
    return redirect(url_for("admin.index"))


@admin_bp.route("/users/<int:user_id>/toggle-admin", methods=["POST"])
def toggle_admin(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("You can't change your own admin status.", "error")
        return redirect(url_for("admin.index"))

    user.is_admin = not user.is_admin
    db.session.commit()
    return redirect(url_for("admin.index"))


@admin_bp.route("/users/<int:user_id>/set-password", methods=["POST"])
def set_password(user_id):
    user = db.get_or_404(User, user_id)
    password = request.form.get("password") or ""

    if len(password) < MIN_PASSWORD_LENGTH:
        flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "error")
        return redirect(url_for("admin.index"))

    user.set_password(password)
    db.session.commit()
    flash(f"Password updated for {user.username}.", "success")
    return redirect(url_for("admin.index"))
