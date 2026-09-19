import os
from dotenv import load_dotenv
from auth.middleware.session_middleware import SessionMiddleware, renderAuthError  # noqa: F401 (riesportata: au.renderAuthError)
from auth.rate_limiter import RateLimiter

load_dotenv()

rate_limiter = RateLimiter(
    int(os.getenv("MAX_SESSIONS_PER_USER", 3)),
    int(os.getenv("MAX_SESSIONS_GLOBAL", 100)),
    int(os.getenv("SESSION_TTL_SECONDS", 28800))
)

session_middleware = SessionMiddleware(
    rate_limiter=rate_limiter
)

def _splitEmailName(email: str) -> tuple[str, str] | None:
    """Estrae (nome, cognome) da un'email nel formato `cognome.nome@dominio`."""
    local_part = (email or "").split("@")[0]
    parts = [part for part in local_part.split(".") if part]

    if len(parts) >= 2:
        return parts[1], parts[0]

    return None

def _splitFullName(full_name: str) -> tuple[str, str]:
    """Fallback: divide il nome completo fornito da Google in (nome, cognome)."""
    parts = (full_name or "").split()

    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])

    return (parts[0] if parts else ""), ""

def getName(email: str, full_name: str = "") -> str:
    parsed = _splitEmailName(email)

    return parsed[0] if parsed else _splitFullName(full_name)[0]

def getSurname(email: str, full_name: str = "") -> str:
    parsed = _splitEmailName(email)

    return parsed[1] if parsed else _splitFullName(full_name)[1]
