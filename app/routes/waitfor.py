from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user
from ..context import db
from ..models.video import Video

route_waitfor_bp = Blueprint("waitfor", __name__, url_prefix="/waitfor")


@route_waitfor_bp.route("/<video_hash>", methods=["GET"])
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
        return redirect(url_for("route_watch", video_hash=video_hash))

    if video.status == 1:
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
