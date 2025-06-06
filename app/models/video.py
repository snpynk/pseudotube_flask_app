from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..context import db


class Video(db.Model):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    hidden: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=0
    )  # (0) public, (1) unlisted
    status: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=1
    )  # (0) ready, (1) processing, (2) failed

    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    uri: Mapped[str] = mapped_column(String(128), nullable=False)
    thumbnail_uri: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    comments = relationship(
        "Comment", cascade="all, delete-orphan", back_populates="video"
    )
    likes = relationship("Likes", cascade="all, delete-orphan", back_populates="video")
    views = relationship("Views", cascade="all, delete-orphan", back_populates="video")

    def __init__(
        self,
        title: str,
        description: str | None,
        hash: str,
        uri: str,
        thumbnail_uri: str,
        user_id: int,
        hidden: int = 0,
        status: int = 1,
    ):
        self.title = title
        self.description = description
        self.hash = hash
        self.uri = uri
        self.thumbnail_uri = thumbnail_uri
        self.user_id = user_id
        self.hidden = hidden
        self.status = status
