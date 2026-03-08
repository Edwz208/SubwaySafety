from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.connection import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    camera_id: Mapped[int] = mapped_column(
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)

    video_clip_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    camera = relationship("Camera", back_populates="events")