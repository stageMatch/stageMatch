from sqlalchemy import Column, String, ForeignKey, Integer, Float, DateTime
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime, timezone

class UserRoute(Base):
    __tablename__ = "user_routes"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(String, ForeignKey("users.googleId"), nullable=False)

    start_address = Column(String, nullable=False)
    end_address = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    distance_km = Column(Float, nullable=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = relationship("User", back_populates="routes")
