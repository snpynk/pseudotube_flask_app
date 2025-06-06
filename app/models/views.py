from datetime import datetime

from ..context import db
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Views(db.Model):
    __tablename__ = "views"
    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    user = relationship("User", back_populates="views")
    video = relationship("Video", back_populates="views")

    def __init__(self, video_id: int, user_id: int | None = None):
        self.video_id = video_id
        self.user_id = user_id
