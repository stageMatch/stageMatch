import os
from dotenv import load_dotenv
from auth.middleware.session_middleware import SessionMiddleware, renderAuthError
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

def getName(email: str) -> str:
    local_part = email.split("@")[0]

    return local_part.split(".")[1]

def getSurname(email: str) -> str:
    local_part = email.split("@")[0]

    return local_part.split(".")[0]
