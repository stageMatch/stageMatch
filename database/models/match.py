from sqlalchemy import Column, String, ForeignKey, Integer, Float, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime, timezone

class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(String, ForeignKey("users.googleId"), nullable=False)
    job_offer_id = Column(Integer, ForeignKey("job_offers.id"), nullable=False)

    deterministic_score = Column(Float, nullable=False)
    ai_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=False)
    explanation = Column(Text, nullable=True)
    ai_status = Column(String, nullable=False, default="disabled")  # ok | fallback | disabled

    computed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="matches")
    job_offer = relationship("JobOffer", back_populates="matches")

    __table_args__ = (
        UniqueConstraint("user_id", "job_offer_id", name="uq_match_user_offer"),
    )
