from sqlalchemy import Column, String, Integer, Text
from sqlalchemy.orm import relationship
from .base import Base

class Company(Base):
    __tablename__ = "companies"

    googleId = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    access_code = Column(String)
    address = Column(String)
    picture = Column(String, nullable=True)
    settore = Column(String, nullable=True)
    descrizione = Column(Text, nullable=True)
    sito_web = Column(String, nullable=True)
    telefono = Column(String, nullable=True)

    job_offers = relationship(
        "JobOffer",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    notifications = relationship(
        "Notification",
        back_populates="company",
        cascade="all, delete-orphan",
        order_by="desc(Notification.id)"
    )
