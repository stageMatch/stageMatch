"""
Middleware di sessione per l'applicazione Flask.
Fornisce: creazione/validazione della sessione server-side e rate-limiting.
"""

import secrets
import logging
from datetime import datetime, timezone
from functools import wraps
from flask import request, redirect, session, url_for, render_template_string

logger = logging.getLogger(__name__)


# ============================================================
# SESSION MIDDLEWARE
# ============================================================

class SessionMiddleware:
    """
    Middleware che gestisce la sessione applicativa dopo il login (Google OAuth):
    creazione della sessione server-side, protezione delle rotte e rate limiting.
    """

    def __init__(self,
                 session_timeout: int = 28800,
                 rate_limiter=None):
        self.sessionTimeout = session_timeout
        self.rateLimiter = rate_limiter

    def createSession(self, user_data: dict, flask_session, session_id: str = None):
        """Crea una sessione server-side per l'utente."""
        sid = session_id or secrets.token_hex(32)

        flask_session.permanent = True
        flask_session['user'] = {
            'email': user_data.get('email'),
            'name': user_data.get('name', ''),
            'googleId': user_data.get('googleId', ''),
            'picture': user_data.get('picture', ''),
            'authenticated_at': datetime.now(timezone.utc).isoformat()
        }
        flask_session['session_id'] = sid
        logger.info(f"Sessione creata per: {user_data.get('email')}")

        return sid

    def _loginUrlForRole(self, role: str | None, notice: str) -> str:
        if role == "company":
            endpoint = "loginCompany"
        elif role == "user":
            endpoint = "loginStudent"
        else:
            endpoint = "login"

        return url_for(endpoint, notice=notice)

    def loginRequired(self, role: str | None = None):
        """
        Decorator per proteggere le route.
        Verifica sessione valida e rate limit (touch).

        `role` ("user" | "company") indica a quale pagina di login rimandare
        se la sessione manca/è scaduta. Se omesso, si usa session['auth_type']
        (impostato al momento del login); se anche questo manca, il ruolo è
        sconosciuto e si rimanda alla pagina di scelta login (`/login`).
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                target_role = role or session.get("auth_type")

                if 'user' not in session:
                    logger.warning("Accesso senza sessione - redirect al login")

                    return redirect(self._loginUrlForRole(target_role, "login_required"))

                if self.rateLimiter:
                    sid = session.get('session_id')

                    if sid:
                        if not self.rateLimiter.isSessionValid(sid):
                            session.clear()

                            return redirect(self._loginUrlForRole(target_role, "session_expired"))

                        self.rateLimiter.touchSession(sid)

                return f(*args, **kwargs)
            
            return decorated_function

        return decorator


# ============================================================
# ERROR PAGE TEMPLATE
# ============================================================

ERROR_TEMPLATE = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Accesso</title>
    <style>
        :root {
            --midnight-blue: #0A0E1A;
            --midnight-blue-light: #111625;
            --emerald-green: #2ECC71;
            --emerald-green-dark: #27AE60;

            --bg: var(--midnight-blue);
            --panel: var(--midnight-blue-light);
            --accent: var(--emerald-green);
            --text: #E8E6F4;
            --text-muted: #7B74A0;
            --border: rgba(46, 204, 113, 0.15);
            --border-glow: rgba(46, 204, 113, 0.3);

            --radius-lg: 12px;
            --radius-md: 8px;
            --transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--bg);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            box-shadow: 0 24px 64px rgba(0,0,0,0.4);
            max-width: 480px;
            width: 100%;
            padding: 48px 40px;
            text-align: center;
        }
        .icon { font-size: 56px; margin-bottom: 20px; }
        h1 { color: var(--text); font-size: 22px; margin-bottom: 12px; font-weight: 600; }
        .message { color: var(--text-muted); font-size: 15px; line-height: 1.7; margin-bottom: 32px; }
        .btn {
            display: inline-block;
            background: var(--accent);
            color: var(--midnight-blue);
            padding: 13px 32px;
            border-radius: var(--radius-md);
            text-decoration: none;
            font-size: 15px;
            font-weight: 600;
            transition: var(--transition);
        }
        .btn:hover {
            background: var(--emerald-green-dark);
            transform: translateY(-1px);
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">{{ icon }}</div>
        <h1>{{ title }}</h1>
        <p class="message">{{ error_message }}</p>
        <a href="{{ back_url }}" class="btn">← {{ back_label }}</a>
    </div>
</body>
</html>
"""


def renderAuthError(error_message: str, back_url: str,
                     status_code: int = 401,
                     title: str = "Accesso Negato",
                     icon: str = "🔒",
                     back_label: str = "Torna indietro"):
    """Renderizza una pagina di errore di autenticazione/accesso."""
    return render_template_string(
        ERROR_TEMPLATE,
        error_message=error_message,
        back_url=back_url,
        title=title,
        icon=icon,
        back_label=back_label
    ), status_code
