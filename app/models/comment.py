from datetime import datetime

from sqlalchemy.orm import mapped_column
from context import db


class Comment(db.Model):
    __tablename__ = "comments"
    id = mapped_column(primary_key=True)
    video_id = mapped_column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    user_id = mapped_column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    text = mapped_column(db.String(1024), nullable=False)
    created_at = mapped_column(db.DateTime, nullable=False, default=datetime.utcnow)
