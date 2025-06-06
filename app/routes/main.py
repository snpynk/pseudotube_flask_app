from flask import Blueprint, render_template
from flask_login import current_user
from sqlalchemy import func, text

from ..context import (
    db,
)
from ..models.likes import Likes
from ..models.user import User
from ..models.video import Video
from ..models.views import Views

main_bp = Blueprint("main", __name__, url_prefix="/")


@main_bp.route("/", methods=["GET"])
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
