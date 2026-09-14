from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from app.extensions import db

from .access import safe_redirect_target
from .models import User

auth_bp = Blueprint(
    "auth",
    __name__,
    template_folder="templates",
)

MIN_PASSWORD_LENGTH = 8


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("core.index"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip().lower()
        password = request.form.get("password") or ""

        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash("Invalid username or password.", "error")
            return render_template("auth/login.html", username=username)

        login_user(user)
        next_url = safe_redirect_target(request.form.get("next") or request.args.get("next"))
        return redirect(next_url or url_for("core.index"))

    return render_template("auth/login.html", username="", next=request.args.get("next", ""))


@auth_bp.route("/logout", methods=["POST"])
def logout():
    # No @login_required: the global before_request login gate in
    # create_app() already guarantees an authenticated user here (this
    # endpoint is never exempt from it), so this would be unreachable code.
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/create-account", methods=["GET", "POST"])
def create_account():
    if current_user.is_authenticated:
        return redirect(url_for("core.index"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        errors = []
        if not username:
            errors.append("Username is required.")
        elif User.query.filter_by(username=username).first() is not None:
            errors.append("That username is already taken.")

        if len(password) < MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        elif password != confirm:
            errors.append("Passwords do not match.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("auth/create_account.html", username=username)

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            # Concurrent signup with the same username raced past the
            # existence check above and won; treat it the same as if we'd
            # caught it there instead of surfacing a 500.
            db.session.rollback()
            flash("That username is already taken.", "error")
            return render_template("auth/create_account.html", username=username)

        login_user(user)
        flash("Account created. An admin needs to grant you access to any projects.", "success")
        return redirect(url_for("core.index"))

    return render_template("auth/create_account.html", username="")
