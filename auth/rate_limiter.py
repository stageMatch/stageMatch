"""
Rate limiting delle sessioni attive, persistito su database (tabella active_sessions).
"""

import logging

from database import database_helper

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiting basato su sessioni attive, persistite su database.

    Criteri implementati:
    1. maxSessionsPerUser  - numero massimo di sessioni simultanee per lo stesso utente.
       Se superato, la sessione più vecchia dello stesso utente viene eliminata
       automaticamente per far posto alla nuova.
    2. maxSessionsGlobal   - numero massimo di sessioni attive totali nell'applicazione.

    Le sessioni "scadute" (più vecchie di sessionTtlSeconds) vengono pulite automaticamente.
    """

    def __init__(self,
                 max_sessions_per_user: int = 3,
                 max_sessions_global: int = 100,
                 session_ttl_seconds: int = 28800):  # 8 ore
        self.maxSessionsPerUser = max_sessions_per_user
        self.maxSessionsGlobal = max_sessions_global
        self.sessionTtlSeconds = session_ttl_seconds

        logger.info(
            f"RateLimiter inizializzato: max_per_user={max_sessions_per_user}, "
            f"max_global={max_sessions_global}, ttl={session_ttl_seconds}s"
        )

    def registerSession(self, session_id: str, email: str) -> tuple[bool, str]:
        """
        Registra una nuova sessione.

        Returns:
            (True, "") se accettata
            (False, motivo) se rifiutata per rate limiting
        """
        database_helper.deleteExpiredActiveSessions(self.sessionTtlSeconds)

        if database_helper.countActiveSessions() >= self.maxSessionsGlobal:
            logger.warning(f"Limite globale sessioni raggiunto ({self.maxSessionsGlobal})")

            return False, f"Il servizio ha raggiunto il numero massimo di sessioni attive ({self.maxSessionsGlobal}). Riprova tra qualche minuto."

        user_sessions = database_helper.getActiveSessionsByEmail(email)

        if len(user_sessions) >= self.maxSessionsPerUser:
            oldest = user_sessions[0]
            database_helper.removeActiveSession(oldest.session_id)
            logger.info(f"Sessione più vecchia rimossa per {email} (limite per utente raggiunto)")

        database_helper.addActiveSession(session_id, email)
        logger.info(f"Sessione registrata: {email}")

        return True, ""

    def touchSession(self, session_id: str):
        """Aggiorna il timestamp last_seen per tenere viva la sessione."""
        database_helper.touchActiveSession(session_id)

    def removeSession(self, session_id: str):
        """Rimuove una sessione (logout)."""
        database_helper.removeActiveSession(session_id)

    def isSessionValid(self, session_id: str) -> bool:
        """Verifica se un session_id è ancora registrato e non scaduto."""
        return database_helper.isActiveSessionValid(session_id, self.sessionTtlSeconds)

    def getStats(self) -> dict:
        """Ritorna statistiche correnti (per admin/debug)."""
        database_helper.deleteExpiredActiveSessions(self.sessionTtlSeconds)

        return {
            "total_sessions": database_helper.countActiveSessions(),
            "max_global": self.maxSessionsGlobal,
            "max_per_user": self.maxSessionsPerUser
        }
