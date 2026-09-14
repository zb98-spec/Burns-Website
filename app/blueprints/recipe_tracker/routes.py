from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import func, or_

from app.blueprints.auth.access import require_project_access
from app.extensions import db

from .models import CUISINES, MEAL_TYPES, Recipe, RecipeIngredient

recipe_tracker_bp = Blueprint(
    "recipe_tracker",
    __name__,
    template_folder="templates",
)


@recipe_tracker_bp.before_request
def _check_access():
    require_project_access("recipe_tracker")


def _parse_optional_int(form, field, label, errors):
    raw = (form.get(field) or "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
        if value < 0:
            raise ValueError
        return value
    except ValueError:
        errors.append(f"{label} must be a non-negative whole number.")
        return None


def _parse_choice(form, field, allowed):
    raw = (form.get(field) or "").strip()
    return raw if raw in allowed else None


def _ingredients_from_form(form, errors):
    quantities = form.getlist("ingredient_quantity")
    units = form.getlist("ingredient_unit")
    names = form.getlist("ingredient_name")

    ingredients = []
    for quantity, unit, name in zip(quantities, units, names):
        name = (name or "").strip()
        if not name:
            continue
        ingredients.append(
            {
                "quantity": (quantity or "").strip() or None,
                "unit": (unit or "").strip() or None,
                "name": name,
                "sort_order": len(ingredients),
            }
        )

    if not ingredients:
        errors.append("At least one ingredient is required.")

    return ingredients


def _recipe_from_form(form, errors):
    title = (form.get("title") or "").strip()
    if not title:
        errors.append("Title is required.")

    instructions = (form.get("instructions") or "").strip()
    if not instructions:
        errors.append("Instructions are required.")

    return {
        "title": title,
        "instructions": instructions,
        "servings": (form.get("servings") or "").strip() or None,
        "prep_time_minutes": _parse_optional_int(form, "prep_time_minutes", "Prep time", errors),
        "cook_time_minutes": _parse_optional_int(form, "cook_time_minutes", "Cook time", errors),
        "cuisine": _parse_choice(form, "cuisine", CUISINES),
        "meal_type": _parse_choice(form, "meal_type", MEAL_TYPES),
        "source_url": (form.get("source_url") or "").strip() or None,
        "source_name": (form.get("source_name") or "").strip() or None,
    }


@recipe_tracker_bp.route("/")
def index():
    query = Recipe.query

    search = (request.args.get("q") or "").strip()
    if search:
        like = f"%{search.lower()}%"
        query = query.outerjoin(RecipeIngredient).filter(
            or_(
                func.lower(Recipe.title).like(like),
                func.lower(RecipeIngredient.name).like(like),
            )
        )

    cuisine = (request.args.get("cuisine") or "").strip()
    if cuisine in CUISINES:
        query = query.filter(Recipe.cuisine == cuisine)

    meal_type = (request.args.get("meal_type") or "").strip()
    if meal_type in MEAL_TYPES:
        query = query.filter(Recipe.meal_type == meal_type)

    recipes = query.distinct().order_by(Recipe.title.asc()).all()
    return render_template(
        "recipe_tracker/index.html",
        recipes=recipes,
        search=search,
        cuisine=cuisine,
        meal_type=meal_type,
        cuisines=CUISINES,
        meal_types=MEAL_TYPES,
    )


@recipe_tracker_bp.route("/<int:recipe_id>")
def detail(recipe_id):
    recipe = db.get_or_404(Recipe, recipe_id)
    return render_template("recipe_tracker/detail.html", recipe=recipe)


@recipe_tracker_bp.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        errors = []
        data = _recipe_from_form(request.form, errors)
        ingredients = _ingredients_from_form(request.form, errors)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "recipe_tracker/form.html",
                recipe=data,
                ingredients=ingredients,
                form_title="Add Recipe",
                cuisines=CUISINES,
                meal_types=MEAL_TYPES,
            )

        recipe = Recipe(**data)
        recipe.ingredients = [RecipeIngredient(**ingredient) for ingredient in ingredients]
        db.session.add(recipe)
        db.session.commit()
        flash(f"Added {recipe.title}.", "success")
        return redirect(url_for("recipe_tracker.detail", recipe_id=recipe.id))

    return render_template(
        "recipe_tracker/form.html",
        recipe=None,
        ingredients=[],
        form_title="Add Recipe",
        cuisines=CUISINES,
        meal_types=MEAL_TYPES,
    )


@recipe_tracker_bp.route("/<int:recipe_id>/edit", methods=["GET", "POST"])
def edit(recipe_id):
    recipe = db.get_or_404(Recipe, recipe_id)

    if request.method == "POST":
        errors = []
        data = _recipe_from_form(request.form, errors)
        ingredients = _ingredients_from_form(request.form, errors)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "recipe_tracker/form.html",
                recipe=data,
                ingredients=ingredients,
                form_title="Edit Recipe",
                recipe_id=recipe_id,
                cuisines=CUISINES,
                meal_types=MEAL_TYPES,
            )

        for key, value in data.items():
            setattr(recipe, key, value)
        recipe.ingredients = [RecipeIngredient(**ingredient) for ingredient in ingredients]
        db.session.commit()
        flash(f"Updated {recipe.title}.", "success")
        return redirect(url_for("recipe_tracker.detail", recipe_id=recipe.id))

    return render_template(
        "recipe_tracker/form.html",
        recipe=recipe,
        ingredients=[
            {"quantity": i.quantity, "unit": i.unit, "name": i.name}
            for i in recipe.ingredients
        ],
        form_title="Edit Recipe",
        recipe_id=recipe_id,
        cuisines=CUISINES,
        meal_types=MEAL_TYPES,
    )


@recipe_tracker_bp.route("/<int:recipe_id>/delete", methods=["POST"])
def delete(recipe_id):
    recipe = db.get_or_404(Recipe, recipe_id)
    db.session.delete(recipe)
    db.session.commit()
    flash(f"Deleted {recipe.title}.", "success")
    return redirect(url_for("recipe_tracker.index"))
