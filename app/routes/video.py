from flask import Blueprint, jsonify, request, session
from flask_login import current_user
from time import time
from ..context import db

from ..models.comment import Comment
from ..models.video import Video
from ..models.likes import Likes
from ..models.views import Views

route_video_bp = Blueprint("video", __name__, url_prefix="/video")


@route_video_bp.route("/comment/<video_hash>", methods=["POST"])
def route_video_comment(video_hash):
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


@route_video_bp.route("/like/<video_hash>", methods=["POST", "DELETE"])
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


@route_video_bp.route("/view/<watch_id>", methods=["POST"])
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

    if time() - watching["watch_start_ts"] <= video.duration * 0.15:
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


@route_video_bp.route("/<video_hash>", methods=["DELETE"])
def route_video_delete(video_hash):
    if not current_user.is_authenticated:
        return jsonify({"error": "User not authenticated"}), 401

    if not video_hash:
        return jsonify({"error": "Missing video hash"}), 400

    video = db.session.scalar(db.select(Video).where(Video.hash == video_hash))

    if not video:
        return jsonify({"error": "Video not found"}), 404

    if video.user_id != current_user.id:
        return jsonify(
            {"error": "You do not have permission to delete this video"}
        ), 403

    likes = db.session.scalars(db.select(Likes).where(Likes.video_id == video.id)).all()
    comments = db.session.scalars(
        db.select(Comment).where(Comment.video_id == video.id)
    ).all()
    views = db.session.scalars(db.select(Views).where(Views.video_id == video.id)).all()

    for like in likes:
        db.session.delete(like)
    for comment in comments:
        db.session.delete(comment)
    for view in views:
        db.session.delete(view)

    db.session.delete(video)
    db.session.commit()

    return jsonify({"message": "Video deleted successfully"}), 200
