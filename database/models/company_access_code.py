from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String

from .base import Base

class CompanyAccessCode(Base):
    """Codice monouso generato da un amministratore e consegnato a un'azienda,
    da inserire in fase di registrazione."""

    __tablename__ = "company_access_codes"

    code = Column(String, primary_key=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    used_by_company_id = Column(String, ForeignKey("companies.googleId"), nullable=True)
    used_at = Column(DateTime, nullable=True)
