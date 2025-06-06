import os
import json
import secrets
import time
import uuid
from urllib.parse import quote_plus
import google.auth
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import func, text

from .context import (
    db,
    gae,
    login_manager,
    provider_manager,
    storage_manager,
    transcoder_service,
)
from .models.comment import Comment
from .models.likes import Likes
from .models.user import User
from .models.video import Video
from .models.views import Views


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = secrets.token_urlsafe(16)

    load_dotenv()

    DB_USER = os.getenv("PSEUDOTUBE_DB_USER", "root")
    DB_PASS = os.getenv("PSEUDOTUBE_DB_PASS", "password")
    DB_INSTANCE = os.getenv("PSEUDOTUBE_DB_INSTANCE", "")
    DB_NAME = os.getenv("PSEUDOTUBE_DB_NAME", "")

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASS)}"
        f"@/{DB_NAME}?unix_socket={DB_INSTANCE}"
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
            .where(Video.hidden == 0)
            .where(Video.status == 0)
            .group_by(Video.id, User.picture)
            .order_by(func.count(Views.id).desc())
            .limit(4)
        ).all()

        most_liked = db.session.execute(
            db.select(Video, func.count(Views.id).label("view_count"), User.picture)
            .outerjoin(Views, Video.id == Views.video_id)  # For view count
            .join(Likes, Video.id == Likes.video_id)  # For like count ordering
            .join(User, User.id == Video.user_id)
            .where(Video.hidden == 0)
            .group_by(Video.id, User.picture)
            .order_by(func.count(Likes.id).desc())
            .limit(4)
        ).all()

        trending = db.session.execute(
            db.select(Video, func.count(Views.id).label("view_count"), User.picture)
            .outerjoin(Views, Video.id == Views.video_id)
            .join(User, User.id == Video.user_id)
            .where(Views.created_at >= text("NOW() - INTERVAL 1 DAY"))
            .where(Video.hidden == 0)
            .where(Video.status == 0)
            .group_by(Video.id, User.picture)
            .order_by(func.count(Views.id).desc())
            .limit(4)
        ).all()

        random_videos = db.session.execute(
            db.select(Video, func.count(Views.id).label("view_count"), User.picture)
            .outerjoin(Views, Video.id == Views.video_id)
            .join(User, User.id == Video.user_id)
            .where(Video.hidden == 0)
            .where(Video.status == 0)
            .group_by(Video.id, User.picture)
            .order_by(db.func.random())
            .limit(4)
        ).all()

        most_recent = db.session.execute(
            db.select(Video, func.count(Views.id).label("view_count"), User.picture)
            .outerjoin(Views, Video.id == Views.video_id)
            .join(User, User.id == Video.user_id)
            .where(Video.hidden == 0)
            .where(Video.status == 0)
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
                .where(Video.hidden == 0)
                .where(Video.status == 0)
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
            .where(Video.status == 0)
            .where(Video.title.ilike(f"%{search_query}%"))
            .group_by(Video.id, User.picture)
        ).all()

        return render_template(
            "search_results.html",
            user=current_user,
            search_query=search_query,
            videos=videos,
        )

    @app.route("/generate_upload_url", methods=["POST"])
    def generate_upload_url():
        if not current_user.is_authenticated:
            return render_template(
                "redirect.html",
                redirect_url=url_for("route_index"),
                message="You must be logged in to upload a video.",
                timeout=5,
            )

        if "last_upload_timestamp" in session:
            last_upload_timestamp = session["last_upload_timestamp"]

            if time.time() - last_upload_timestamp < 60 * 5:
                return jsonify(
                    {
                        "upload_url": session.get("last_upload_url"),
                        "upload_hash": session.get("last_upload_hash"),
                    },
                )

        try:
            upload_hash = uuid.uuid4().hex
            upload_url = storage_manager.generate_upload_url(f"uploads/{upload_hash}")

            session["last_upload_timestamp"] = time.time()
            session["last_upload_url"] = upload_url
            session["last_upload_hash"] = upload_hash

            return jsonify(
                {
                    "upload_url": upload_url,
                    "upload_hash": upload_hash,
                }
            )

        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/upload", methods=["POST"])
    def route_upload():
        if not current_user.is_authenticated:
            return render_template(
                "redirect.html",
                redirect_url=url_for("route_index"),
                message="You must be logged in to upload a video.",
                timeout=5,
            )

        if "last_upload_url" not in session or "last_upload_hash" not in session:
            return render_template(
                "redirect.html",
                redirect_url=url_for("route_index"),
                message="No upload URL found. Please generate a new upload URL.",
                timeout=5,
            )

        upload_hash = session["last_upload_hash"]

        if not storage_manager.path_exists(f"uploads/{upload_hash}"):
            return render_template(
                "redirect.html",
                redirect_url=url_for("route_index"),
                message="Upload file not found. Please try uploading again.",
                timeout=5,
            )

        data = request.get_json()

        auth_req = google_requests.Request()
        token = id_token.fetch_id_token(auth_req, gae.GCF_FFPROBE)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            gae.GCF_FFPROBE,
            headers=headers,
            data=json.dumps(
                {"gcs_path": f"gs://{gae.GCP_BUCKET_NAME}/uploads/{upload_hash}"}
            ),
        )

        if response.status_code != 200:
            return render_template(
                "redirect.html",
                redirect_url=url_for("route_index"),
                message="Failed to get video metadata. Please try again later.",
                timeout=5,
            )

        metadata = response.json()

        job = transcoder_service.create_transcoder_job(
            f"gs://{gae.GCP_BUCKET_NAME}/uploads/{upload_hash}",
            f"gs://{gae.GCP_BUCKET_NAME}/transcoded/{upload_hash}/",
            metadata["width"],
            metadata["height"],
            metadata["fps"],
            metadata["duration"],
        )

        db.session.add(
            Video(
                title=data.get("title"),
                description=data.get("description", None),
                hash=upload_hash,
                thumbnail_url="",
                user_id=current_user.id,
                hidden=0,
                status=1,
                duration=metadata["duration"],
                job=job.name,
            )
        )

        db.session.commit()

        session.pop("last_upload_timestamp")
        session.pop("last_upload_url")
        session.pop("last_upload_hash")

        return render_template(
            "redirect.html",
            redirect_url=url_for("route_waitfor", video_hash=upload_hash),
            message="Video upload done successfully. It will be processed shortly.",
            timeout=3,
        )

    @app.route("/waitfor/<video_hash>", methods=["GET"])
    def route_waitfor(video_hash):
        video = db.session.scalar(db.select(Video).where(Video.hash == video_hash))

        if not video:
            return render_template(
                "redirect.html",
                redirect_url=url_for("route_index"),
                message="Video not found.",
                timeout=5,
            )

        if video.status == 0:
            return redirect(url_for("route_watch", video_hash=video_hash))

        if video.status == 1:
            return render_template(
                "waitfor.html",
                user=current_user,
                video=video,
            )

        return render_template(
            "redirect.html",
            redirect_url=url_for("route_index"),
            message="Video processing failed.",
            timeout=5,
        )

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

        video_stream_url = None

        try:
            video_stream_url = storage_manager.get_public_url(
                f"transcoded/{video.hash}/manifest.mpd"
            )

            video_orig_url = storage_manager.get_public_url(f"uploads/{video.hash}")

            if video.status != 0:
                video.status = 0
                video.thumbnail_url = storage_manager.get_public_url(
                    f"transcoded/{video.hash}/small-thumbnail0000000000.jpeg"
                )

        except RuntimeError as e:
            if "does not exist in the bucket" in str(e) and video.status == 0:
                video.status = 1

        db.session.commit()

        video_info = {
            "video": video,
            "video_url": (video_stream_url),
            "video_orig_url": (video_orig_url),
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
                    db.select(Comment, User.picture.label("user_picture"))
                    .join(User, Comment.user_id == User.id)
                    .where(Comment.video_id == video.id)
                    .order_by(Comment.created_at.desc())
                ).all()
            ),
            "liked": (
                db.session.scalar(
                    db.select(Likes).where(
                        Likes.video_id == video.id,
                        Likes.user_id == current_user.id
                        if current_user.is_authenticated
                        else None,
                    )
                )
                is not None
            ),
        }

        watch_id = uuid.uuid4().hex

        if "watching_list" not in session:
            session["watching_list"] = {}

        watching_list = session["watching_list"]
        watching_list[watch_id] = {
            "video_hash": video.hash,
            "watch_start_ts": time.time(),
            "watched": False,
        }

        session["watching_list"] = watching_list

        return render_template(
            "watch.html", user=current_user, video_info=video_info, watch_id=watch_id
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

    @app.route("/api/video/like/<video_hash>", methods=["GET", "POST", "DELETE"])
    def route_video_like(video_hash):
        if not current_user.is_authenticated:
            return jsonify({"error": "User not authenticated"}), 401

        if not video_hash:
            return jsonify({"error": "Missing video hash"}), 400

        video = db.session.scalar(db.select(Video).where(Video.hash == video_hash))

        if not video:
            return jsonify({"error": "Video not found"}), 404

        if video.status != 0:
            return jsonify({"error": "Video is not available"}), 404

        existing_like = db.session.scalar(
            db.select(Likes).where(
                Likes.video_id == video.id, Likes.user_id == current_user.id
            )
        )

        method = request.method

        if method == "DELETE":
            if not existing_like:
                return jsonify({"error": "Like not found"}), 404

            db.session.delete(existing_like)
            db.session.commit()

            return jsonify({"message": "Video like removed successfully"}), 200

        elif method == "POST":
            if existing_like:
                return jsonify({"error": "Video already liked"}), 400

            db.session.add(Likes(video_id=video.id, user_id=current_user.id))
            db.session.commit()

            return jsonify({"message": "Video liked successfully"}), 200

        else:
            return jsonify({"liked": existing_like}), 200

    # should work for any kind of user
    @app.route("/api/video/view/<watch_id>", methods=["POST"])
    def route_video_view(watch_id):
        if "watching_list" not in session:
            return jsonify({"error": "No video watch session found"}), 400

        watching_list = session["watching_list"]

        if watch_id not in watching_list:
            return jsonify({"error": "Invalid watch session ID"}), 400

        watching = watching_list[watch_id]

        if watching["watched"]:
            return jsonify({"error": "Video already watched"}), 400

        video_hash = watching["video_hash"]

        video = db.session.scalar(db.select(Video).where(Video.hash == video_hash))

        if time.time() - watching["watch_start_ts"] <= video.duration * 0.15:
            return jsonify({"error": "Video view too soon after start"}), 400

        if not video:
            return jsonify({"error": "Video not found"}), 404

        if video.status != 0:
            return jsonify({"error": "Video is not available"}), 404

        db.session.add(
            Views(
                video_id=video.id,
                user_id=current_user.id if current_user.is_authenticated else None,
            )
        )

        db.session.commit()

        session["watching_list"][watch_id]["watched"] = True

        return jsonify({"message": "Video view recorded successfully"}), 200

    @app.route("/api/video/comment/<video_hash>", methods=["POST"])
    def route_comment(video_hash):
        if not current_user.is_authenticated:
            return jsonify({"error": "User not authenticated"}), 401

        if not video_hash:
            return jsonify({"error": "Missing video hash"}), 400

        video = db.session.scalar(db.select(Video).where(Video.hash == video_hash))

        if not video:
            return jsonify({"error": "Video not found"}), 404

        if video.status != 0:
            return jsonify({"error": "Video is not available"}), 404

        data = request.get_json()
        text = data.get("text", "").strip()

        if not text:
            return jsonify({"error": "Comment content cannot be empty"}), 400

        comment = Comment(
            text=text,
            user_id=current_user.id,
            video_id=video.id,
        )

        db.session.add(comment)
        db.session.commit()

        return jsonify({"message": "Comment added successfully"}), 201

    @app.route("/api/video/<video_hash>", methods=["DELETE"])
    def route_remove_video(video_hash):
        if not current_user.is_authenticated:
            return jsonify({"error": "User not authenticated"}), 401

        if not video_hash:
            return jsonify({"error": "Missing video hash"}), 400

        video = db.session.scalar(db.select(Video).where(Video.hash == video_hash))

        if not video:
            return jsonify({"error": "Video not found"}), 404

        if video.user_id != current_user.id:
            return jsonify(
                {"error": "You do not have permission to remove this video"}
            ), 403

        likes = db.session.scalars(
            db.select(Likes).where(Likes.video_id == video.id)
        ).all()
        comments = db.session.scalars(
            db.select(Comment).where(Comment.video_id == video.id)
        ).all()
        views = db.session.scalars(
            db.select(Views).where(Views.video_id == video.id)
        ).all()

        for like in likes:
            db.session.delete(like)
        for comment in comments:
            db.session.delete(comment)
        for view in views:
            db.session.delete(view)

        db.session.delete(video)
        db.session.commit()

        return jsonify({"message": "Video removed successfully"}), 200

    @app.route("/api/transcoder/status", methods=["GET", "POST"])
    def route_transcoder_status():
        if request.method == "POST":
            data = request.get_json()
            job_id = data.get("job_id")
            state = data.get("state")

            if not job_id or not state:
                return jsonify({"error": "Missing job_id or job_state"}), 400

            video = db.session.scalar(db.select(Video).where(Video.job == job_id))

            if not video:
                return jsonify({"error": "Video not found"}), 404

            if video.status == 0:
                return jsonify({"message": "Video already processed"}), 200

            if not storage_manager.path_exists(f"transcoded/{video.hash}/manifest.mpd"):
                return jsonify({"error": "Video file is still unavailable"}), 404

            video.job = None

            if state == "SUCCEEDED":
                video.status = 0
                video.thumbnail_url = storage_manager.get_public_url(
                    f"transcoded/{video.hash}/small-thumbnail0000000000.jpeg"
                )
            elif state == "FAILED":
                video.status = 2  # Failed status
            else:
                return jsonify({"error": "Invalid job state"}), 400

            db.session.commit()

            return jsonify({"message": "Job status updated successfully"}), 200
        else:
            timestamp = time.time()
            if "last_request_timestamp" in session:
                last_request_timestamp = session.get("last_request_timestamp", 0)

                if timestamp - last_request_timestamp < 1:
                    return jsonify({"error": "Rate limit exceeded"}), 429

            video_hash = request.args.get("video_hash")

            if not video_hash:
                return jsonify({"error": "Missing video hash"}), 400

            video = db.session.scalar(db.select(Video).where(Video.hash == video_hash))

            if not video:
                return jsonify({"error": "Video not found"}), 404

            if video.status == 0:
                return jsonify({"status": "processed"}), 200
            else:
                if storage_manager.path_exists(f"transcoded/{video.hash}/manifest.mpd"):
                    video.status = 0
                    video.thumbnail_url = storage_manager.get_public_url(
                        f"transcoded/{video.hash}/small-thumbnail0000000000.jpeg"
                    )
                    db.session.commit()
                    return jsonify({"status": "processed"}), 200

                if video.status == 1:
                    return jsonify({"status": "processing"}), 200
                elif video.status == 2:
                    return jsonify({"status": "failed"}), 200
                else:
                    return jsonify({"error": "Unknown video status"}), 500

    with app.app_context():
        db.create_all()

    return app
