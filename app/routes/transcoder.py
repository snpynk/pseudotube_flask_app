from time import time
from ..models.video import Video
from flask import Blueprint, request, jsonify, session
from ..context import db, storage_manager

route_transcoder_bp = Blueprint("transcoder", __name__, url_prefix="/api/transcoder")


@route_transcoder_bp.route("/status", methods=["GET", "POST"])
def route_transcoder_status():
    if request.method == "POST":
        data = request.get_json()["job"]
        job_id = data.get("name")
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
            video.status = 3  # Failed status
        else:
            return jsonify({"error": "Invalid job state"}), 400

        db.session.commit()

        return jsonify({"message": "Job status updated successfully"}), 200
    else:
        timestamp = time()
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
                return jsonify({"status": "preparing"}), 200
            elif video.status == 3:
                return jsonify({"status": "failed"}), 200
            else:
                return jsonify({"error": "Unknown video status"}), 500
