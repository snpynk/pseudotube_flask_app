from context import db


class Views:
    __tablename__ = "views"
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    viewed_at = db.Column(
        db.DateTime, nullable=False, default=db.func.current_timestamp()
    )
