from datetime import datetime

from ..context import db
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Likes(db.Model):
    __tablename__ = "likes"
    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    user = relationship("User", back_populates="likes")
    video = relationship("Video", back_populates="likes")

    def __init__(self, video_id: int, user_id: int):
        self.video_id = video_id
        self.user_id = user_id
