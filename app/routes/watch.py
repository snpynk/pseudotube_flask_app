import time
import uuid

from sqlalchemy import func
from flask import Blueprint, render_template, session, url_for, redirect
from flask_login import current_user

from ..context import db, storage_manager

from ..models.comment import Comment
from ..models.likes import Likes
from ..models.user import User
from ..models.video import Video
from ..models.views import Views

route_watch_bp = Blueprint("watch", __name__, url_prefix="/watch")


@route_watch_bp.route("/<video_hash>", methods=["GET"])
def route_watch(video_hash):
    video = db.session.scalar(db.select(Video).where(Video.hash == video_hash))

    if not video:
        return render_template(
            "redirect.html",
            redirect_url=url_for("main.route_index"),
            message="Video not found.",
            timeout=60,
        )

    video_stream_url = None

    try:
        video_stream_url = storage_manager.get_public_url(
            f"transcoded/{video.hash}/manifest.mpd"
        )

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
        "video_url": video_stream_url,
        "uploader": db.session.scalar(db.select(User).where(User.id == video.user_id)),
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


@route_watch_bp.route("/waitfor/<video_hash>", methods=["GET"])
def route_waitfor(video_hash):
    video = db.session.scalar(db.select(Video).where(Video.hash == video_hash))

    if not video:
        return render_template(
            "redirect.html",
            redirect_url=url_for("main.route_index"),
            message="Video not found.",
            timeout=5,
        )

    if video.status == 0:
        return redirect(url_for("watch.route_watch", video_hash=video_hash))

    elif video.status in (1, 2):
        return render_template(
            "waitfor.html",
            user=current_user,
            video=video,
        )

    return render_template(
        "redirect.html",
        redirect_url=url_for("main.route_index"),
        message="Video processing failed.",
        timeout=5,
    )
