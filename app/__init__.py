import os
import secrets
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import func, text

from . import video
from .context import db, login_manager, provider_manager, storage_manager
from .models.likes import Likes
from .models.user import User
from .models.video import Video
from .models.views import Views
from .models.comment import Comment


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = secrets.token_urlsafe(16)

    load_dotenv()

    DB_USER = os.getenv("PSEUDOTUBE_DB_USER", "root")
    DB_PASS = os.getenv("PSEUDOTUBE_DB_PASS", "password")
    CONNECTION_PREFIX = os.getenv("PSEUDOTUBE_DB_CONN_PREFIX", "")
    CONNECTION_SUFFIX = os.getenv(
        "PSEUDOTUBE_DB_CONN_SUFFIX", "pseudotube-db?unix_socket=/cloudsql/pseudotube-db"
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{DB_USER}:{DB_PASS}@{CONNECTION_PREFIX}/{CONNECTION_SUFFIX}"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    login_manager.init_app(app)

    provider_manager.setup()

    @login_manager.user_loader
    def user_loader(user_id):
        return db.session.get(User, int(user_id))

    @app.route("/")
    def route_index():
        most_watched = db.session.execute(
            db.select(Video, func.count(Views.id).label("view_count"), User.picture)
            .outerjoin(Views, Video.id == Views.video_id)
            .join(User, User.id == Video.user_id)
            .group_by(Video.id, User.picture)
            .order_by(func.count(Views.id).desc())
            .limit(4)
        ).all()

        most_liked = db.session.execute(
            db.select(Video, func.count(Views.id).label("view_count"), User.picture)
            .outerjoin(Views, Video.id == Views.video_id)  # For view count
            .join(Likes, Video.id == Likes.video_id)  # For like count ordering
            .join(User, User.id == Video.user_id)
            .group_by(Video.id, User.picture)
            .order_by(func.count(Likes.id).desc())
            .limit(4)
        ).all()

        trending = db.session.execute(
            db.select(Video, func.count(Views.id).label("view_count"), User.picture)
            .outerjoin(Views, Video.id == Views.video_id)
            .join(User, User.id == Video.user_id)
            .where(Views.created_at >= text("NOW() - INTERVAL 1 DAY"))
            .group_by(Video.id, User.picture)
            .order_by(func.count(Views.id).desc())
            .limit(4)
        ).all()

        random_videos = db.session.execute(
            db.select(Video, func.count(Views.id).label("view_count"), User.picture)
            .outerjoin(Views, Video.id == Views.video_id)
            .join(User, User.id == Video.user_id)
            .group_by(Video.id, User.picture)
            .order_by(db.func.random())
            .limit(4)
        ).all()

        most_recent = db.session.execute(
            db.select(Video, func.count(Views.id).label("view_count"), User.picture)
            .outerjoin(Views, Video.id == Views.video_id)
            .join(User, User.id == Video.user_id)
            .group_by(Video.id, User.picture)
            .order_by(db.desc(Video.id))
            .limit(4)
        ).all()

        user_videos = []
        if current_user.is_authenticated:
            user_videos = db.session.execute(
                db.select(Video, func.count(Views.id).label("view_count"), User.picture)
                .outerjoin(Views, Video.id == Views.video_id)
                .join(User, User.id == Video.user_id)
                .where(Video.user_id == current_user.id)
                .group_by(Video.id, User.picture)
                .order_by(db.desc(Video.id))
                .limit(4)
            ).all()

        return render_template(
            "index.html",
            user=current_user,
            most_watched=most_watched,
            most_liked=most_liked,
            trending=trending,
            random_videos=random_videos,
            user_videos=user_videos,
            most_recent=most_recent,
        )

    @app.route("/search", methods=["GET", "POST"])
    def route_search():
        if request.method == "POST":
            search_query = request.form.get("search-query", "").strip()
        else:
            search_query = request.args.get("query", "").strip()

        if not search_query:
            return render_template(
                "redirect.html",
                redirect_url=url_for("route_index"),
                message="Search query cannot be empty.",
                timeout=5,
            )

        videos = db.session.execute(
            db.select(Video, func.count(Views.id).label("view_count"), User.picture)
            .outerjoin(Views, Video.id == Views.video_id)
            .join(User, User.id == Video.user_id)
            .where(Video.title.ilike(f"%{search_query}%"))
            .group_by(Video.id, User.picture)
        ).all()

        return render_template(
            "search_results.html",
            user=current_user,
            search_query=search_query,
            videos=videos,
        )

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

        return jsonify({"redirect_url": url_for("route_watch", video_hash=video_hash)})

    @app.route("/watch/<video_hash>", methods=["GET"])
    def route_watch(video_hash):
        video = db.session.scalar(db.select(Video).where(Video.hash == video_hash))

        if not video:
            return render_template(
                "redirect.html",
                redirect_url=url_for("route_index"),
                message="Video not found.",
                timeout=5,
            )

        video_info = {
            "video": video,
            "uploader": db.session.scalar(
                db.select(User).where(User.id == video.user_id)
            ),
            "view_count": (
                db.session.execute(
                    db.select(func.count(Views.id)).where(Views.video_id == video.id)
                ).scalar_one_or_none()
                or 0
            ),
            "like_count": (
                db.session.execute(
                    db.select(func.count(Likes.id)).where(Likes.video_id == video.id)
                ).scalar_one_or_none()
                or 0
            ),
            # include user avatar per comment
            "comments": (
                db.session.execute(
                    db.select(Comment, User)
                    .join(User, Comment.user_id == User.id)
                    .where(Comment.video_id == video.id)
                    .order_by(Comment.created_at.desc())
                ).all()
            ),
        }

        return render_template(
            "watch.html",
            user=current_user,
            video_info=video_info,
        )

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
