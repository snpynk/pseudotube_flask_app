from datetime import datetime

from context import db
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class Views(db.Model):
    __tablename__ = "views"
    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
