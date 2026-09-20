from sqlalchemy import Column, String, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from .base import Base

class Language(Base):
    __tablename__ = 'user_languages'

    user_id = Column(String, ForeignKey('users.googleId'), primary_key=True)
    name = Column(String, primary_key=True)
    level = Column(String, nullable=False)
    certification = Column(String, nullable=True)

    user = relationship("User", back_populates="languages")

    __table_args__ = (
        CheckConstraint(
            "level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')",
            name="check_livello_lingua_valido"
        ),
    )
