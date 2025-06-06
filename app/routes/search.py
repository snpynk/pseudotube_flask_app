from flask import request, url_for
from flask import Blueprint, render_template
from flask_login import current_user
from sqlalchemy import func

from ..context import (
    db,
)
from ..models.user import User
from ..models.video import Video
from ..models.views import Views

route_search_bp = Blueprint("search", __name__, url_prefix="/search")


@route_search_bp.route("/search", methods=["GET"])
def route_search():
    if request.method == "POST":
        search_query = request.form.get("search-query", "").strip()
    else:
        search_query = request.args.get("query", "").strip()

    if not search_query:
        return render_template(
            "redirect.html",
            redirect_url=url_for("main_bp.main.route_index"),
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
