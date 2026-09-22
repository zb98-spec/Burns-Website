from datetime import date, datetime

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import func, or_

from app.blueprints.auth.access import require_project_access
from app.extensions import db

from .models import Bottle, TastingHistory, TastingScore

wine_cellar_bp = Blueprint(
    "wine_cellar",
    __name__,
    template_folder="templates",
)


@wine_cellar_bp.before_request
def _check_access():
    require_project_access("wine_cellar")


def _parse_int(value):
    value = (value or "").strip()
    return int(value) if value else None


def _parse_decimal(value):
    value = (value or "").strip()
    return value if value else None


def _parse_date(value):
    value = (value or "").strip()
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _scores_from_form(form, errors):
    names = form.getlist("taster_name")
    raw_scores = form.getlist("score")

    scores = []
    for name, raw_score in zip(names, raw_scores):
        name = (name or "").strip()
        raw_score = (raw_score or "").strip()
        if not name and not raw_score:
            continue
        if not name:
            errors.append("Each score needs a taster name.")
            continue
        try:
            score = int(raw_score)
            if not (0 <= score <= 100):
                raise ValueError
        except ValueError:
            errors.append(f"{name}'s score must be a whole number between 0 and 100.")
            continue
        scores.append({"taster_name": name, "score": score})

    return scores


def _image_from_files(files, errors):
    image = files.get("image")
    if image is None or not image.filename:
        return None, None
    if not (image.mimetype or "").startswith("image/"):
        errors.append("Uploaded file must be an image.")
        return None, None
    return image.read(), image.mimetype


def _bottle_from_form(form, errors):
    name = (form.get("name") or "").strip()
    if not name:
        errors.append("Name is required.")

    quantity_raw = (form.get("quantity") or "1").strip()
    try:
        quantity = int(quantity_raw) if quantity_raw else 1
        if quantity < 0:
            raise ValueError
    except ValueError:
        errors.append("Quantity must be a non-negative whole number.")
        quantity = 1

    def parse_optional_int(field, label):
        raw = (form.get(field) or "").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            errors.append(f"{label} must be a whole number.")
            return None

    vintage = parse_optional_int("vintage", "Vintage")
    drink_window_start = parse_optional_int("drink_window_start", "Drink window start")
    drink_window_end = parse_optional_int("drink_window_end", "Drink window end")
    if (
        drink_window_start is not None
        and drink_window_end is not None
        and drink_window_start > drink_window_end
    ):
        errors.append("Drink window start must be before or equal to the end year.")

    purchase_price_raw = (form.get("purchase_price") or "").strip()
    purchase_price = None
    if purchase_price_raw:
        try:
            purchase_price = float(purchase_price_raw)
        except ValueError:
            errors.append("Purchase price must be a number.")

    purchase_date = None
    purchase_date_raw = (form.get("purchase_date") or "").strip()
    if purchase_date_raw:
        try:
            purchase_date = _parse_date(purchase_date_raw)
        except ValueError:
            errors.append("Purchase date must be a valid date.")

    return {
        "name": name,
        "producer": (form.get("producer") or "").strip() or None,
        "vintage": vintage,
        "varietal": (form.get("varietal") or "").strip() or None,
        "region": (form.get("region") or "").strip() or None,
        "quantity": quantity,
        "location": (form.get("location") or "").strip() or None,
        "purchase_price": purchase_price,
        "purchase_date": purchase_date,
        "purchase_source": (form.get("purchase_source") or "").strip() or None,
        "drink_window_start": drink_window_start,
        "drink_window_end": drink_window_end,
    }


@wine_cellar_bp.route("/")
def index():
    query = Bottle.query.filter(Bottle.quantity > 0)

    search = (request.args.get("q") or "").strip()
    if search:
        like = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Bottle.name).like(like),
                func.lower(Bottle.producer).like(like),
                func.lower(Bottle.varietal).like(like),
                func.lower(Bottle.region).like(like),
            )
        )

    bottles = query.order_by(Bottle.name.asc()).all()
    return render_template("wine_cellar/index.html", bottles=bottles, search=search)


@wine_cellar_bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        errors = []
        data = _bottle_from_form(request.form, errors)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("wine_cellar/form.html", bottle=data, form_title="Add Bottle")

        bottle = Bottle(**data)
        db.session.add(bottle)
        db.session.commit()
        flash(f"Added {bottle.name}.", "success")
        return redirect(url_for("wine_cellar.index"))

    return render_template("wine_cellar/form.html", bottle=None, form_title="Add Bottle")


@wine_cellar_bp.route("/<int:bottle_id>/edit", methods=["GET", "POST"])
def edit(bottle_id):
    bottle = db.get_or_404(Bottle, bottle_id)

    if request.method == "POST":
        errors = []
        data = _bottle_from_form(request.form, errors)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("wine_cellar/form.html", bottle=data, form_title="Edit Bottle", bottle_id=bottle_id)

        for key, value in data.items():
            setattr(bottle, key, value)
        db.session.commit()
        flash(f"Updated {bottle.name}.", "success")
        return redirect(url_for("wine_cellar.index"))

    return render_template("wine_cellar/form.html", bottle=bottle, form_title="Edit Bottle", bottle_id=bottle_id)


@wine_cellar_bp.route("/<int:bottle_id>/delete", methods=["POST"])
def delete(bottle_id):
    bottle = db.get_or_404(Bottle, bottle_id)
    TastingHistory.query.filter_by(bottle_id=bottle.id).update({"bottle_id": None})
    db.session.delete(bottle)
    db.session.commit()
    flash(f"Deleted {bottle.name}.", "success")
    return redirect(url_for("wine_cellar.index"))


@wine_cellar_bp.route("/<int:bottle_id>/drink", methods=["GET", "POST"])
def drink(bottle_id):
    bottle = db.get_or_404(Bottle, bottle_id)
    if bottle.quantity < 1:
        flash("There are no bottles left to drink.", "error")
        return redirect(url_for("wine_cellar.index"))

    if request.method == "POST":
        errors = []

        consumed_date_raw = (request.form.get("consumed_date") or "").strip()
        try:
            consumed_date = _parse_date(consumed_date_raw) or date.today()
        except ValueError:
            errors.append("Consumed date must be a valid date.")
            consumed_date = date.today()

        scores = _scores_from_form(request.form, errors)
        image_bytes, image_mimetype = _image_from_files(request.files, errors)

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("wine_cellar/drink.html", bottle=bottle, today=date.today().isoformat())

        bottle.quantity -= 1
        history = TastingHistory(
            bottle_id=bottle.id,
            wine_name=bottle.name,
            producer=bottle.producer,
            vintage=bottle.vintage,
            consumed_date=consumed_date,
            notes=(request.form.get("notes") or "").strip() or None,
            image=image_bytes,
            image_mimetype=image_mimetype,
            scores=[TastingScore(**s) for s in scores],
        )
        db.session.add(history)
        db.session.commit()
        flash(f"Logged a tasting of {bottle.name}.", "success")
        return redirect(url_for("wine_cellar.index"))

    return render_template("wine_cellar/drink.html", bottle=bottle, today=date.today().isoformat())


@wine_cellar_bp.route("/tastings/add", methods=["GET", "POST"])
def add_tasting():
    if request.method == "POST":
        errors = []

        wine_name = (request.form.get("wine_name") or "").strip()
        if not wine_name:
            errors.append("Wine name is required.")

        vintage_raw = (request.form.get("vintage") or "").strip()
        vintage = None
        if vintage_raw:
            try:
                vintage = int(vintage_raw)
            except ValueError:
                errors.append("Vintage must be a whole number.")

        consumed_date_raw = (request.form.get("consumed_date") or "").strip()
        try:
            consumed_date = _parse_date(consumed_date_raw) or date.today()
        except ValueError:
            errors.append("Consumed date must be a valid date.")
            consumed_date = date.today()

        scores = _scores_from_form(request.form, errors)
        image_bytes, image_mimetype = _image_from_files(request.files, errors)

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "wine_cellar/tasting_add.html", today=date.today().isoformat(), form_data=request.form
            )

        history = TastingHistory(
            bottle_id=None,
            wine_name=wine_name,
            producer=(request.form.get("producer") or "").strip() or None,
            vintage=vintage,
            consumed_date=consumed_date,
            notes=(request.form.get("notes") or "").strip() or None,
            image=image_bytes,
            image_mimetype=image_mimetype,
            scores=[TastingScore(**s) for s in scores],
        )
        db.session.add(history)
        db.session.commit()
        flash(f"Logged a tasting of {wine_name}.", "success")
        return redirect(url_for("wine_cellar.history"))

    return render_template("wine_cellar/tasting_add.html", today=date.today().isoformat(), form_data=None)


@wine_cellar_bp.route("/tastings/<int:tasting_id>/image")
def tasting_image(tasting_id):
    entry = db.get_or_404(TastingHistory, tasting_id)
    if not entry.image:
        abort(404)
    return Response(entry.image, mimetype=entry.image_mimetype or "application/octet-stream")


@wine_cellar_bp.route("/history")
def history():
    entries = TastingHistory.query.order_by(TastingHistory.consumed_date.desc()).all()
    return render_template("wine_cellar/history.html", entries=entries)
