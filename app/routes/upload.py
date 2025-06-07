from threading import Thread

import json
import os
import subprocess
from fractions import Fraction
from time import time
from uuid import uuid4

import requests
from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    session,
    url_for,
    current_app,
)
from flask_login import current_user
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from ..context import db, gae, storage_manager, transcoder_service
from ..models.video import Video

route_upload_bp = Blueprint("upload", __name__, url_prefix="/upload")


@route_upload_bp.route("/", methods=["GET", "POST"])
def route_upload():
    if request.method == "POST":
        return upload()
    else:
        return generate_upload_url()


def generate_upload_url():
    if not current_user.is_authenticated:
        return render_template(
            "redirect.html",
            redirect_url=url_for("main.route_index"),
            message="You must be logged in to upload a video.",
            timeout=5,
        )

    if "last_upload_timestamp" in session:
        last_upload_timestamp = session["last_upload_timestamp"]

        if time() - last_upload_timestamp < 60 * 5:
            return jsonify(
                {
                    "upload_url": session.get("last_upload_url"),
                    "upload_hash": session.get("last_upload_hash"),
                },
            )

    try:
        upload_hash = uuid4().hex
        upload_url = storage_manager.generate_upload_url(f"uploads/{upload_hash}")

        session["last_upload_timestamp"] = time()
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


def upload():
    if not current_user.is_authenticated:
        return render_template(
            "redirect.html",
            redirect_url=url_for("main.route_index"),
            message="You must be logged in to upload a video.",
            timeout=5,
        )

    if "last_upload_url" not in session or "last_upload_hash" not in session:
        return render_template(
            "redirect.html",
            redirect_url=url_for("main.route_index"),
            message="No upload URL found. Please generate a new upload URL.",
            timeout=5,
        )

    upload_hash = session["last_upload_hash"]

    if not storage_manager.path_exists(f"uploads/{upload_hash}"):
        return render_template(
            "redirect.html",
            redirect_url=url_for("main.route_index"),
            message="Upload file not found. Please try uploading again.",
            timeout=5,
        )

    data = request.get_json()
    title = data.get("title", "Untitled Video")
    description = data.get("description", "")

    db.session.add(
        Video(
            title=title,
            description=description,
            hash=upload_hash,
            thumbnail_url="",
            user_id=current_user.id,
            hidden=0,
            status=2,
        )
    )

    db.session.commit()

    thread = Thread(
        target=create_upload_job,
        args=(
            current_app._get_current_object(),
            upload_hash,
        ),
    )
    thread.start()

    session.pop("last_upload_timestamp")
    session.pop("last_upload_url")
    session.pop("last_upload_hash")

    return render_template(
        "redirect.html",
        redirect_url=url_for("watch.route_waitfor", video_hash=upload_hash),
        message="Video upload done successfully. It will be processed shortly.",
        timeout=3,
    )


def get_video_metadata(upload_hash):
    metadata = {}
    if "IS_GAE" in os.environ:
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

        metadata = response.json()
    else:
        url = storage_manager.get_public_url(f"uploads/{upload_hash}")

        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,r_frame_rate,duration",
                "-of",
                "json",
                url,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        decoded_result = json.loads(result.stdout.decode())
        stream = decoded_result["streams"][0]

        fps = float(Fraction(stream["r_frame_rate"]))

        metadata = {
            "width": stream["width"],
            "height": stream["height"],
            "fps": fps,
            "duration": float(stream.get("duration", 0)),
        }

    if not metadata:
        raise ValueError("Failed to extract video metadata.")

    return metadata


def create_upload_job(app, upload_hash):
    with app.app_context():
        video = Video.query.filter_by(hash=upload_hash).first()

        if not video:
            raise ValueError(f"Video ({upload_hash}) not found in the database.")

        try:
            metadata = get_video_metadata(upload_hash)

            job = transcoder_service.create_transcoder_job(
                f"gs://{gae.GCP_BUCKET_NAME}/uploads/{upload_hash}",
                f"gs://{gae.GCP_BUCKET_NAME}/transcoded/{upload_hash}/",
                metadata["width"],
                metadata["height"],
                metadata["fps"],
                metadata["duration"],
            )

            if not job:
                raise ValueError("Failed to create transcoder job.")

            if not video:
                raise ValueError(f"Video ({upload_hash}) not found in the database.")

            video.job = job.name
            video.status = 1

            db.session.commit()

        except Exception:
            video.status = 3
            db.session.commit()
            print(f"Error processing video {upload_hash}: {str(Exception)}")
