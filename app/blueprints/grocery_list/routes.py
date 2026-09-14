from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.blueprints.auth.access import require_project_access
from app.extensions import db

from .models import CATEGORIES, GroceryItem

grocery_list_bp = Blueprint(
    "grocery_list",
    __name__,
    template_folder="templates",
)


@grocery_list_bp.before_request
def _check_access():
    require_project_access("grocery_list")


def _item_from_form(form, errors):
    name = (form.get("name") or "").strip()
    if not name:
        errors.append("Name is required.")

    category = (form.get("category") or "").strip()
    if category not in CATEGORIES:
        category = "Other"

    return {
        "name": name,
        "category": category,
        "quantity": (form.get("quantity") or "").strip() or None,
        "note": (form.get("note") or "").strip() or None,
    }


def _group_by_category(items):
    by_category = {}
    for item in items:
        by_category.setdefault(item.category, []).append(item)

    groups = []
    for category in CATEGORIES:
        if category in by_category:
            groups.append(
                (category, sorted(by_category[category], key=lambda i: i.name.lower()))
            )
    return groups


def _next_url():
    if request.form.get("next") == "catalog":
        return url_for("grocery_list.catalog")
    return url_for("grocery_list.index")


@grocery_list_bp.route("/")
def index():
    items = GroceryItem.query.filter_by(on_list=True).all()
    return render_template(
        "grocery_list/index.html", groups=_group_by_category(items), has_items=bool(items)
    )


@grocery_list_bp.route("/catalog")
def catalog():
    items = GroceryItem.query.all()
    return render_template("grocery_list/catalog.html", groups=_group_by_category(items))


@grocery_list_bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        errors = []
        data = _item_from_form(request.form, errors)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "grocery_list/form.html", item=data, form_title="Add Item", categories=CATEGORIES
            )

        item = GroceryItem(**data)
        db.session.add(item)
        db.session.commit()
        flash(f"Added {item.name}.", "success")
        return redirect(url_for("grocery_list.index"))

    return render_template(
        "grocery_list/form.html", item=None, form_title="Add Item", categories=CATEGORIES
    )


@grocery_list_bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
def edit(item_id):
    item = db.get_or_404(GroceryItem, item_id)

    if request.method == "POST":
        errors = []
        data = _item_from_form(request.form, errors)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "grocery_list/form.html",
                item=data,
                form_title="Edit Item",
                categories=CATEGORIES,
                item_id=item_id,
            )

        for key, value in data.items():
            setattr(item, key, value)
        db.session.commit()
        flash(f"Updated {item.name}.", "success")
        return redirect(url_for("grocery_list.catalog"))

    return render_template(
        "grocery_list/form.html",
        item=item,
        form_title="Edit Item",
        categories=CATEGORIES,
        item_id=item_id,
    )


@grocery_list_bp.route("/<int:item_id>/toggle", methods=["POST"])
def toggle(item_id):
    item = db.get_or_404(GroceryItem, item_id)
    item.on_list = not item.on_list
    db.session.commit()
    return redirect(_next_url())


@grocery_list_bp.route("/<int:item_id>/delete", methods=["POST"])
def delete(item_id):
    item = db.get_or_404(GroceryItem, item_id)
    db.session.delete(item)
    db.session.commit()
    flash(f"Deleted {item.name}.", "success")
    return redirect(_next_url())


@grocery_list_bp.route("/clear-all", methods=["POST"])
def clear_all():
    GroceryItem.query.filter_by(on_list=True).update({"on_list": False})
    db.session.commit()
    flash("Cleared the list.", "success")
    return redirect(url_for("grocery_list.index"))
