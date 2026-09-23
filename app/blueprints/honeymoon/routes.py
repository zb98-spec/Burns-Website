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


def _format_date_range(start, end):
    if start == end:
        return start.strftime("%b %-d")
    if start.month == end.month:
        return f"{start.strftime('%b %-d')}–{end.strftime('%-d')}"
    return f"{start.strftime('%b %-d')}–{end.strftime('%b %-d')}"


def _stops_for(days):
    """Collapse consecutive same-location days into one map pin per stay,
    so a multi-night stop doesn't stack duplicate markers."""
    stays = []
    for d in days:
        if d.location_lat is None or d.location_lng is None:
            continue
        key = (d.location_name, d.location_lat, d.location_lng)
        if stays and stays[-1]["key"] == key:
            stays[-1]["end"] = d.date
        else:
            stays.append({
                "key": key,
                "name": d.location_name,
                "lat": d.location_lat,
                "lng": d.location_lng,
                "url": d.location_url,
                "image_url": d.location_image_url,
                "start": d.date,
                "end": d.date,
            })

    return [
        {
            "name": s["name"],
            "lat": s["lat"],
            "lng": s["lng"],
            "url": s["url"],
            "image_url": s["image_url"],
            "date_range": _format_date_range(s["start"], s["end"]),
        }
        for s in stays
    ]


@honeymoon_bp.route("/")
def index():
    all_days = Day.query.order_by(Day.date).all()
    admin_view = _admin_view_active()

    today = date.today()
    days = all_days if admin_view else [d for d in all_days if d.date <= today]

    stops = _stops_for(days)

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
        for field in ("staying", "travel", "breakfast", "lunch", "dinner", "activities", "location_name", "location_url", "location_image_url"):
            setattr(day, field, request.form.get(field, "").strip() or None)
        lat = request.form.get("location_lat", "").strip()
        lng = request.form.get("location_lng", "").strip()
        day.location_lat = float(lat) if lat else None
        day.location_lng = float(lng) if lng else None
        db.session.commit()
        return redirect(url_for("honeymoon.index"))

    return render_template("honeymoon/edit.html", day=day)
