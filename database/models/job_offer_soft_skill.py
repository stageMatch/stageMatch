from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.orm import relationship
from .base import Base

class JobOfferSoftSkill(Base):
    __tablename__ = "job_offer_required_soft_skills"

    job_offer_id = Column(Integer, ForeignKey("job_offers.id"), primary_key=True)
    label = Column(String, primary_key=True)
    icon = Column(String, nullable=False)

    job_offer = relationship("JobOffer", back_populates="required_soft_skills")
