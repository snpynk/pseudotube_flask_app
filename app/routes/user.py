from flask import Blueprint, render_template, url_for, redirect, request
from flask_login import current_user, logout_user, login_user

from ..context import provider_manager, login_manager, db
from ..models.user import User


route_user_bp = Blueprint("user", __name__)


@login_manager.user_loader
def user_loader(user_id):
    return db.session.get(User, int(user_id))


@route_user_bp.route("/authorize/<provider>")
def route_oauth2_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for("main_bp.main.route_index"))

    try:
        response = provider_manager.authorize(provider)
    except ValueError as e:
        return str(e), 400

    return response


@route_user_bp.route("/auth_callback/<provider>")
def route_oauth2_callback(provider):
    if not current_user.is_anonymous:
        return redirect(url_for("main.route_index"))

    try:
        response_data = provider_manager.oauth_callback(request, provider)
    except ValueError as e:
        return str(e), 400

    if not response_data:
        return "No data received from the OAuth provider", 400

    user = db.session.scalar(
        db.select(User).where(User.email == response_data.get("email"))
    )

    if not user:
        authorized_user = User(
            response_data.get("email"),
            provider,
            response_data.get("name", "Unknown User"),
            response_data.get("picture", None),
        )
    else:
        authorized_user = user
        authorized_user.name = response_data.get("name", user.name)
        authorized_user.picture = response_data.get("picture", user.picture)

    db.session.add(authorized_user)
    db.session.commit()

    login_user(authorized_user)
    return redirect(url_for("main.route_index"))


@route_user_bp.route("/logout", methods=["GET"])
def route_logout():
    if current_user.is_authenticated:
        logout_user()
        return render_template(
            "redirect.html",
            redirect_url=url_for("main.route_index"),
            message="You have been logged out.",
        )

    return render_template(
        "redirect.html",
        redirect_url=url_for("main.route_index"),
        message="You are not logged in.",
    )
