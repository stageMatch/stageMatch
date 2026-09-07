from sqlalchemy import Column, String, DateTime
from .base import Base

class ActiveSession(Base):
    __tablename__ = "active_sessions"

    session_id = Column(String, primary_key=True)
    email = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
