from sqlalchemy import Column, String, ForeignKey, Integer, Text, Boolean, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime, timezone

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(String, ForeignKey("users.googleId"), nullable=True)
    company_id = Column(String, ForeignKey("companies.googleId"), nullable=True)

    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    sender = Column(String, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="notifications")
    company = relationship("Company", back_populates="notifications")

    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND company_id IS NULL) OR (user_id IS NULL AND company_id IS NOT NULL)",
            name="check_notification_single_recipient"
        ),
    )
