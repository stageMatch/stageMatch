from sqlalchemy import Column, String, ForeignKey, Integer, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime, timezone

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)

    job_offer_id = Column(Integer, ForeignKey("job_offers.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.googleId"), nullable=False)

    status = Column(String, nullable=False, default="inviata")  # inviata | vista | accettata | rifiutata
    message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    job_offer = relationship("JobOffer", back_populates="applications")
    user = relationship("User", back_populates="applications")

    __table_args__ = (
        UniqueConstraint("job_offer_id", "user_id", name="uq_application_offer_user"),
    )
