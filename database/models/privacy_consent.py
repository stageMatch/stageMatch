from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import Base

class PrivacyConsent(Base):
    """Consenso privacy di uno studente o di un'azienda. Una riga per ogni versione
    dell'informativa accettata, così da mantenere lo storico."""

    __tablename__ = "privacy_consents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.googleId"), nullable=True, index=True)
    company_id = Column(String, ForeignKey("companies.googleId"), nullable=True, index=True)
    privacy_version = Column(String, nullable=False)
    accepted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="privacy_consents")
    company = relationship("Company", back_populates="privacy_consents")

    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND company_id IS NULL) OR (user_id IS NULL AND company_id IS NOT NULL)",
            name="check_consent_owner"
        ),
    )
