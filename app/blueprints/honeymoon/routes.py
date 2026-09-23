from datetime import date

from flask import Blueprint, abort, redirect, render_template, request, session, url_for
from flask_login import current_user

from app.blueprints.auth.access import require_project_access
from app.extensions import db

from .models import Day

honeymoon_bp = Blueprint(
    "honeymoon",
    __name__,
    template_folder="templates",
)


@honeymoon_bp.before_request
def _check_access():
    require_project_access("honeymoon")


def _admin_view_active():
    """Admins default to seeing every card; the toggle switch lets them
    preview the user-facing (past-through-today only) view instead."""
    return current_user.is_admin and session.get("honeymoon_view_mode", "admin") == "admin"


@honeymoon_bp.route("/")
def index():
    all_days = Day.query.order_by(Day.date).all()
    admin_view = _admin_view_active()

    today = date.today()
    days = all_days if admin_view else [d for d in all_days if d.date <= today]

    stops = [
        {
            "name": d.location_name,
            "lat": d.location_lat,
            "lng": d.location_lng,
            "date": d.date.isoformat(),
        }
        for d in all_days
        if d.location_lat is not None and d.location_lng is not None
    ]

    return render_template(
        "honeymoon/index.html",
        days=days,
        today=today,
        admin_view=admin_view,
        stops=stops,
    )


@honeymoon_bp.route("/toggle-view", methods=["POST"])
def toggle_view():
    if not current_user.is_admin:
        abort(403)
    current_mode = session.get("honeymoon_view_mode", "admin")
    session["honeymoon_view_mode"] = "user" if current_mode == "admin" else "admin"
    return redirect(url_for("honeymoon.index"))


@honeymoon_bp.route("/<int:day_id>/edit", methods=["GET", "POST"])
def edit(day_id):
    if not current_user.is_admin:
        abort(403)
    day = db.get_or_404(Day, day_id)

    if request.method == "POST":
        for field in ("staying", "travel", "breakfast", "lunch", "dinner", "activities", "location_name"):
            setattr(day, field, request.form.get(field, "").strip() or None)
        lat = request.form.get("location_lat", "").strip()
        lng = request.form.get("location_lng", "").strip()
        day.location_lat = float(lat) if lat else None
        day.location_lng = float(lng) if lng else None
        db.session.commit()
        return redirect(url_for("honeymoon.index"))

    return render_template("honeymoon/edit.html", day=day)
