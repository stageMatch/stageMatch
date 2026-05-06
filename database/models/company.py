from sqlalchemy import Column, String, Integer
from .base import Base

class Company(Base):
    __tablename__ = "companies"

    googleId = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    accessCode = Column(String)
    address = Column(String)
    picture = Column(String, nullable=True)