from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..context import db


class Video(db.Model):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    hidden: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=0
    )  # (0) public, (1) unlisted
    hash_video: Mapped[str] = mapped_column(String(64), nullable=False)
    hash_thumbnail: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    def __init__(
        self,
        title: str,
        description: str | None,
        hash_video: str,
        user_id: int,
        hidden: int = 0,
    ):
        self.title = title
        self.description = description
        self.hash_video = hash_video
        self.user_id = user_id
        self.hidden = hidden
