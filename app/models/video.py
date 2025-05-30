from datetime import datetime
from context import db


class Video(db.Model):
    __tablename__ = "videos"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(512), nullable=True)
    hidden = db.Column(
        db.Integer(16), nullable=False, default=0
    )  # (0) public, (1) unlisted
    hash_video = db.Column(db.String(64), nullable=False)
    hash_thumbnail = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
