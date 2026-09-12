from sqlalchemy import Column, String, ForeignKey, Integer, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime, timezone

class JobOffer(Base):
    __tablename__ = "job_offers"

    id = Column(Integer, primary_key=True, autoincrement=True)

    company_id = Column(String, ForeignKey("companies.googleId"), nullable=False)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    attivo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    company = relationship("Company", back_populates="job_offers")

    required_skills = relationship(
        "JobOfferSkill",
        back_populates="job_offer",
        cascade="all, delete-orphan"
    )

    required_soft_skills = relationship(
        "JobOfferSoftSkill",
        back_populates="job_offer",
        cascade="all, delete-orphan"
    )

    applications = relationship(
        "Application",
        back_populates="job_offer",
        cascade="all, delete-orphan"
    )

    matches = relationship(
        "Match",
        back_populates="job_offer",
        cascade="all, delete-orphan"
    )
