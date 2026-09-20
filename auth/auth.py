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

STUDENT_EMAIL_SUFFIX = "studente"

def _splitEmailName(email: str) -> tuple[str, str] | None:
    """Estrae (nome, cognome) da un'email studente `cognome.nome.studente@dominio`."""
    local_part = (email or "").split("@")[0]
    parts = local_part.split(".")

    if len(parts) == 3 and all(parts) and parts[2].lower() == STUDENT_EMAIL_SUFFIX:
        return parts[1], parts[0]

    return None

def getNameSurname(user: dict) -> tuple[str, str]:
    """
    Restituisce (nome, cognome) suggeriti per uno studente.

    Si usano prima `given_name`/`family_name` di Google (gestiscono nomi e
    cognomi composti); il campo mancante viene ricavato dall'email
    `cognome.nome.studente@dominio`.
    """
    name = (user.get("given_name") or "").strip()
    surname = (user.get("family_name") or "").strip()

    if not (name and surname):
        parsed = _splitEmailName(user.get("email"))

        if parsed:
            name = name or parsed[0]
            surname = surname or parsed[1]

    return name, surname
