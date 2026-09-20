from sqlalchemy import Column, String, ForeignKey, Integer, CheckConstraint, SmallInteger
from sqlalchemy.orm import relationship
from .base import Base

class JobOfferSkill(Base):
    __tablename__ = "job_offer_required_skills"

    job_offer_id = Column(Integer, ForeignKey("job_offers.id"), primary_key=True)
    name = Column(String, primary_key=True)
    livello_min = Column(SmallInteger, nullable=False)

    job_offer = relationship("JobOffer", back_populates="required_skills")

    __table_args__ = (
        CheckConstraint(
            "livello_min IN (1, 2, 3)",  # 1=base 2=intermedio 3=avanzato
            name="check_livello_min_valido"
        ),
    )
