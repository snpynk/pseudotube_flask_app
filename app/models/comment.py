from datetime import datetime

from context import db
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(
        Integer(), ForeignKey("videos.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer(), ForeignKey("users.id"), nullable=False
    )
    text: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at = mapped_column(DateTime(), nullable=False, default=datetime.now)

    def __init__(self, video_id: int, user_id: int, text: str):
        self.video_id = video_id
        self.user_id = user_id
        self.text = text
