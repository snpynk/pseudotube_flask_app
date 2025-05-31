import secrets
import uuid

from flask import Flask, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from . import video
from .context import db, login_manager, provider_manager, storage_manager
from .models.user import User
from .models.video import Video


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = secrets.token_urlsafe(16)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"

    db.init_app(app)

    login_manager.init_app(app)

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
        if not current_user.is_authenticated:
            return render_template(
                "redirect.html",
                redirect_url=url_for("route_index"),
                message="You must be logged in to upload a video.",
                timeout=5,
            )

        if not (request and request.files and "file-upload" in request.files.keys()):
            return render_template(
                "redirect.html",
                redirect_url=url_for("route_index"),
                message="No file part in the request.",
                timeout=5,
            )

        file = request.files["file-upload"]

        if file.filename == "":
            return render_template(
                "redirect.html",
                redirect_url=url_for("route_index"),
                message="File is empty",
                timeout=5,
            )

        content_type = file.content_type or ""
        if not content_type.startswith("video/"):
            return render_template(
                "redirect.html",
                redirect_url=url_for("route_index"),
                message="File is not a video.",
                timeout=5,
            )

        video_hash = uuid.uuid4().hex
        file_extension = os.path.splitext(file.filename)[-1]
        tmp_file_path = f"instance/{video_hash}.{file_extension}"

        with open(tmp_file_path, "wb") as f:
            f.write(file.read())

        try:
            video.validate_video_streamable(tmp_file_path)
        except video.VideoStreamingError as err:
            return render_template(
                "redirect.html",
                redirect_url=url_for("route_index"),
                message=f"Video validation failed: {err}",
                timeout=5,
            )

        video_uri = storage_manager.upload_video(
            tmp_file_path,
            f"videos/{video_hash}.{content_type.split('/')[-1]}",
        )

        thumbnail_uri = storage_manager.upload_thumbnail(
            video.generate_thumbnail(tmp_file_path),
            f"thumbnails/{video_hash}.jpg",
        )

        db.session.add(
            Video(
                title=request.form.get("video-title", "Untitled Video"),
                description=request.form.get("video-description", None),
                hash=video_hash,
                uri=video_uri,
                thumbnail_uri=thumbnail_uri,
                user_id=current_user.id,
            )
        )

        db.session.commit()

        os.remove(tmp_file_path)
        return video_uri, 200

    @app.route("/video/<video_id>", methods=["GET"])
    def route_video(video_id):
        return f"Video ID: {video_id}"

    @app.route("/logout")
    def route_logout():
        if current_user.is_authenticated:
            logout_user()
            return render_template(
                "redirect.html",
                redirect_url=url_for("route_index"),
                message="You have been logged out.",
            )

        return render_template(
            "redirect.html",
            redirect_url=url_for("route_index"),
            message="You are not logged in.",
        )

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
