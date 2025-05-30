from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ..context import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(96), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    picture: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, default=datetime.now
    )

    __table_args__ = (
        db.UniqueConstraint("email", "provider", name="uq_email_provider"),
    )

    def __init__(
        self, email: str, provider: str, name: str, picture: str | None = None
    ):
        self.email = email
        self.provider = provider
        self.name = name
        self.picture = picture
