from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..context import db


class Video(db.Model):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String(384), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    hidden: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=0
    )  # (0) public, (1) unlisted
    status: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=1
    )  # (0) ready, (1) processing, (2) failed
    job: Mapped[str | None] = mapped_column(
        String(384), nullable=True
    )  # Transcoder job ID
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    duration: Mapped[float | None] = mapped_column(Float(), nullable=True)

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
        thumbnail_url: str,
        user_id: int,
        hidden: int = 0,
        status: int = 1,
        duration: float = 0,
        job: str | None = None,
    ):
        self.title = title
        self.description = description
        self.hash = hash
        self.thumbnail_url = thumbnail_url
        self.user_id = user_id
        self.hidden = hidden
        self.status = status
        self.duration = duration
        self.job = job
