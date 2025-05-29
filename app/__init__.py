import secrets

from flask import Flask, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from .context import db, login_manager, provider_manager
from .models.user import User


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = secrets.token_urlsafe(16)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"

    login_manager.init_app(app)
    db.init_app(app)

    provider_manager.setup()

    @login_manager.user_loader
    def user_loader(user_id):
        return db.session.get(User, int(user_id))

    @app.route("/")
    def route_index():
        return render_template("index.html", user=current_user)

    @app.route("/search", methods=["GET", "POST"])
    def route_search():
        return "Hey"

    @app.route("/upload", methods=["POST"])
    def route_upload():
        dom_video_input_name = "video_file"

        if not (
            request and request.files and dom_video_input_name in request.files.keys()
        ):
            return "No file part in the request", 400

        file = request.files[dom_video_input_name]

        if file.filename == "":
            return "File name is empty", 400

        if not file:
            return "No file selected", 400

        # Bucket logic

        return "Video uploaded successfully", 200

    @app.route("/video/<video_id>", methods=["GET"])
    def route_video(video_id):
        return f"Video ID: {video_id}"

    @app.route("/logout")
    def route_logout():
        if current_user.is_authenticated:
            logout_user()
            return "Logged out successfully", 200

        return "You are not logged in", 400

    @app.route("/authorize/<provider>")
    def route_oauth2_authorize(provider):
        if not current_user.is_anonymous:
            return redirect(url_for("route_index"))

        try:
            response = provider_manager.authorize(provider)
        except ValueError as e:
            return str(e), 400

        return response

    @app.route("/auth_callback/<provider>")
    def route_oauth2_callback(provider):
        if not current_user.is_anonymous:
            return redirect(url_for("route_index"))

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
        return redirect(url_for("route_index"))

    with app.app_context():
        db.create_all()

    return app
