import os
import secrets
import logging
import requests
from functools import wraps
from flask import Flask, render_template, redirect, request, session, url_for, jsonify, abort
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import timedelta
from urllib.parse import urlparse
import auth.auth as au
from auth.auth_google.auth import initGoogleAuth, getGoogleUserInfo
from database import database_helper
from database.database_helper import ApplicationAlreadyExistsError, InvalidAccessCodeError, UserAlreadyExistsError
from matching import worker as matching_worker
from matching import engine as matching_engine
from matching import geo as matching_geo
import validation

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

DEBUG = os.getenv("DEBUG", "False").lower() == "true"
PRIVACY_POLICY_VERSION = os.getenv("PRIVACY_POLICY_VERSION", "1.0")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "")
ADMIN_EMAILS = {
    email.strip().lower()
    for email in os.getenv("ADMIN_EMAILS", "").split(",")
    if email.strip()
}

CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://unpkg.com",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: https:",
    "connect-src 'self' https://raw.githubusercontent.com",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'"
])

TRANSPORT_MODE_LABELS = {
    "driving-car": "Auto",
    "foot-walking": "A piedi",
    "cycling-regular": "Bicicletta"
}
TRANSPORT_MODE_ICONS = {
    "driving-car": "i-car",
    "foot-walking": "i-walk",
    "cycling-regular": "i-bike"
}

VALID_TRANSPORT_MODES = tuple(TRANSPORT_MODE_LABELS)

app = Flask(
    __name__,
    static_folder="./resources",
    template_folder="./resources"
)
google = initGoogleAuth(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
app.secret_key = os.getenv("SERVER_SECRET_KEY")
app.permanent_session_lifetime = timedelta(hours=8)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

if not app.secret_key:
    raise RuntimeError("SERVER_SECRET_KEY non impostata: copia .env.example in .env e valorizzala")

app.config.update(
    SESSION_COOKIE_SECURE=not DEBUG,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)

try:
    db_conn = os.getenv("DB_CONNECTION_STRING", "database.db")
    db_dir = os.path.dirname(db_conn)

    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    database_helper.initDB(db_conn)
except Exception as e:
    app.logger.error(f"[ERROR] database initialization failed: {e}")
    raise e

matching_worker.startWorker()
matching_worker.enqueue(matching_engine.recomputeMissingMatches, name="recompute-missing-matches")

@app.before_request
def rejectCrossSiteWrites():
    """Difesa CSRF: le richieste che modificano dati devono partire dallo stesso sito."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return None

    origin = request.headers.get("Origin")

    if origin:
        if urlparse(origin).netloc != request.host:
            abort(403)
    elif request.headers.get("Sec-Fetch-Site") == "cross-site":
        abort(403)

@app.after_request
def addSecurityHeaders(response):
    response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

    return response

def _jsonError(message: str, status: int):
    return jsonify({"error": message}), status

def _parseId(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def _notificationToDict(notification) -> dict:
    return {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "sender": notification.sender,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat()
    }

def _splitAddress(raw_address: str | None) -> list[str]:
    return [part.strip() for part in (raw_address or "").split("££")]

def adminRequired(f):
    """Limita la route agli account Google elencati in ADMIN_EMAILS."""
    @wraps(f)
    @au.session_middleware.loginRequired()
    def decorated(*args, **kwargs):
        if session["user"]["email"].lower() not in ADMIN_EMAILS:
            abort(403)

        return f(*args, **kwargs)

    return decorated

def _completeLogin(user_data: dict):
    email = user_data.get("email", "")

    session_id = secrets.token_hex(32)
    allowed, reason = au.rate_limiter.registerSession(session_id, email)

    if not allowed:
        app.logger.warning(f"rate limit reached (googleId={user_data.get('googleId')})")

        auth_type = session.get("auth_type", "user")

        return au.renderAuthError(
            reason,
            url_for("loginCompany" if auth_type == "company" else "loginStudent"),
            429,
            "Too many active sessions",
            "⏱️",
            "Vai al login"
        )

    app.logger.info(f"login riuscito (googleId={user_data.get('googleId')})")

    au.session_middleware.createSession(user_data, session, session_id)

    return redirect(url_for("completeLogin"))

@app.route('/')
def mainPage():
    color_mode = None
    auth_type = None
    if "user" in session:
        auth_type = session.get("auth_type", "user")
        google_id = session["user"]["googleId"]
        if auth_type == "company":
            company = database_helper.getCompanyByGoogleId(google_id)
            color_mode = company.color_mode if company else None
        else:
            preferences = database_helper.getUserPreferences(google_id)
            color_mode = preferences.color_mode if preferences else None

    return render_template(
        "html/landing.html",
        color_mode=color_mode,
        auth_type=auth_type
    )

@app.route('/login')
def login():
    return render_template("/html/login.html")

@app.route('/login/student')
def loginStudent():
    return render_template("/html/login-student.html")

@app.route("/login/company")
def loginCompany():
    return render_template("/html/login-company.html")

@app.route("/privacy")
def privacy():
    return render_template(
        "/html/privacy.html",
        privacy_version=PRIVACY_POLICY_VERSION,
        support_email=SUPPORT_EMAIL
    )

@app.route("/terms")
def terms():
    return render_template("/html/terms.html", support_email=SUPPORT_EMAIL)

@app.route("/auth/login")
def authLogin():
    session["auth_type"] = "user"

    return redirect(url_for("googleLogin"))

@app.route("/auth/google/login")
def googleLogin():
    redirect_uri = url_for("googleCallback", _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/auth/google/callback")
def googleCallback():
    try:
        user_data = getGoogleUserInfo()

        if not user_data:
            auth_type = session.get("auth_type", "user")

            return au.renderAuthError(
                "Impossibile recuperare i dati utente da Google.",
                url_for("loginCompany" if auth_type == "company" else "loginStudent"),
                401,
                "Accesso Negato",
                "🔒",
                "Vai al login"
            )

        return _completeLogin(user_data)
    except Exception:
        app.logger.exception("Google callback failed")
        auth_type = session.get("auth_type", "user")

        return au.renderAuthError(
            "Autenticazione Google fallita.",
            url_for("loginCompany" if auth_type == "company" else "loginStudent"),
            401,
            "Accesso Negato",
            "🔒",
            "Vai al login"
        )

@app.route("/auth/logout")
def authLogout():
    session_id: str = session.get("session_id")
    auth_type = session.get("auth_type", "user")

    if session_id:
        au.rate_limiter.removeSession(session_id)

    session.clear()

    return redirect(url_for(
        "loginCompany" if auth_type == "company" else "loginStudent",
        notice="logged_out"
    ))

@app.route("/auth/company/login", methods=["GET", "POST"])
def authCompanyLogin():
    if request.method == "POST":
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({"error": "Dati invalidi"}), 400

        if data.get("terms_ack") is not True:
            return jsonify({"error": "Devi accettare i Termini e Condizioni e l'informativa privacy"}), 400

        try:
            pending = {
                "name": validation.cleanText(data.get("name"), "nome azienda", required=True),
                "access_code": validation.cleanText(data.get("access_code"), "codice di accesso", 100, required=True),
                "via": validation.cleanText(data.get("via"), "via", required=True),
                "civico": validation.cleanText(data.get("civico"), "civico", 20, required=True),
                "cap": validation.cleanText(data.get("cap"), "CAP", 10, required=True),
                "citta": validation.cleanText(data.get("citta"), "città", required=True),
                "color_mode": data.get("color_mode") if data.get("color_mode") in validation.COLOR_MODES else "dark"
            }
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        for field in ("via", "civico", "cap", "citta"):
            pending[field] = pending[field].replace("££", " ")

        if not database_helper.isAccessCodeAvailable(pending["access_code"]):
            return jsonify({"error": "Codice di accesso non valido o già utilizzato"}), 403

        session["pending_company_data"] = pending
        session["auth_type"] = "company"
        return jsonify({"message": "Dati ricevuti, procedi con l'autenticazione"}), 200

    # Se è GET, impostiamo il tipo di autenticazione e reindirizziamo a Google
    session["auth_type"] = "company"
    return redirect(url_for("googleLogin"))

@app.route("/logged/complete", methods=["GET", "POST"])
@au.session_middleware.loginRequired()
def completeLogin():
    user = session["user"]
    auth_type = session.get("auth_type")

    if auth_type == "company":
        if database_helper.existCompany(user["googleId"]):
            return redirect(url_for("dashboardCompany"))

        pending_data = session.get("pending_company_data")
        if pending_data:
            try:
                company_data = {
                    "googleId": user["googleId"],
                    "name": pending_data["name"],
                    "email": user["email"],
                    "address": f"{pending_data['via']} ££ {pending_data['civico']} ££ {pending_data['cap']} ££ {pending_data['citta']}",
                    "picture": user["picture"],
                    "color_mode": pending_data.get("color_mode", "dark")
                }
                database_helper.addCompany(
                    company_data,
                    access_code=pending_data["access_code"],
                    privacy_version=PRIVACY_POLICY_VERSION
                )
            except KeyError:
                session.pop("pending_company_data", None)

                return au.renderAuthError(
                    "Dati di registrazione incompleti. Ripeti la registrazione.",
                    url_for("loginCompany"),
                    400,
                    "Registrazione non valida",
                    "⚠️",
                    "Vai alla registrazione"
                )
            except InvalidAccessCodeError:
                session.pop("pending_company_data", None)

                return au.renderAuthError(
                    "Il codice di accesso non è valido o è già stato utilizzato. Richiedine uno nuovo alla scuola.",
                    url_for("loginCompany"),
                    403,
                    "Codice non valido",
                    "🔑",
                    "Vai alla registrazione"
                )
            except IntegrityError:
                session.pop("pending_company_data", None)

                return au.renderAuthError(
                    "Esiste già un'azienda registrata con questo account.",
                    url_for("loginCompany"),
                    409,
                    "Registrazione non valida",
                    "⚠️",
                    "Vai al login"
                )

            session.pop("pending_company_data", None)
            return redirect(url_for("dashboardCompany"))
        else:
            return au.renderAuthError(
                "Azienda non registrata. Torna alla pagina di registrazione.",
                url_for("loginCompany"),
                401,
                "Accesso Negato",
                "🔒",
                "Vai alla registrazione"
            )

    if database_helper.existUser(user["googleId"]):
        return redirect(url_for("dashboardStudent"))

    if request.method == "POST":
        data = request.form.to_dict()

        if data.get("privacy_ack") != "on":
            return jsonify({
                "error": "Devi prendere visione dell'informativa privacy prima di continuare."
            }), 400

        if data.get("privacy_version") != PRIVACY_POLICY_VERSION:
            return jsonify({
                "error": "Informativa privacy non aggiornata. Ricarica la pagina e riprova."
            }), 400

        try:
            fields = {
                key: validation.cleanText(data.get(key), label, max_length, required=True)
                for key, label, max_length in (
                    ("nome", "nome", 100),
                    ("cognome", "cognome", 100),
                    ("data_nascita", "data di nascita", 10),
                    ("sesso", "sesso", 20),
                    ("comune_nascita", "comune di nascita", 100),
                    ("codice_fiscale", "codice fiscale", 16),
                    ("telefono", "telefono", 30),
                    ("indirizzo_studio", "indirizzo di studio", 100),
                    ("classe", "classe", 20),
                    ("istituto", "istituto", 100),
                    ("via", "via", 100),
                    ("civico", "civico", 20),
                    ("cap", "CAP", 10),
                    ("citta_residenza", "città di residenza", 100)
                )
            }
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        address_parts = [fields[key].replace("££", " ") for key in ("via", "civico", "cap", "citta_residenza")]

        user_data = {
            "googleId": user["googleId"],
            "name": fields["nome"],
            "surname": fields["cognome"],
            "email": user["email"],
            "data_nascita": fields["data_nascita"],
            "sesso": fields["sesso"],
            "comune_nascita": fields["comune_nascita"],
            "codice_fiscale": fields["codice_fiscale"],
            "telefono": fields["telefono"],
            "indirizzo_studio": fields["indirizzo_studio"],
            "classe": fields["classe"],
            "istituto": fields["istituto"],
            "indirizzo": " ££ ".join(address_parts),
            "picture": user["picture"]
        }
        color_mode = data.get("color_mode") if data.get("color_mode") in validation.COLOR_MODES else "dark"

        try:
            database_helper.addUser(
                user_data,
                privacy_consent={
                    "privacy_version": PRIVACY_POLICY_VERSION
                },
                color_mode=color_mode
            )
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except UserAlreadyExistsError:
            return redirect(url_for("dashboardStudent"))
        except IntegrityError:
            return jsonify({"error": "Esiste già un account con questo codice fiscale o questa email."}), 409

        database_helper.addNotification(
            user["googleId"],
            "Benvenuto su stageMatch!",
            "La tua registrazione è avvenuta con successo. Completa il tuo profilo per iniziare a ricevere match con le aziende.",
            sender="stageMatch"
        )

        matching_worker.enqueue(
            lambda: matching_engine.recomputeMatchesForStudent(user["googleId"]),
            name=f"student:{user['googleId']}"
        )

        return redirect(url_for("dashboardStudent"))

    name, surname = au.getNameSurname(user)
    user_data = {
        "name": name,
        "surname": surname,
        "email": user["email"]
    }

    return render_template(
        "/html/complete-login.html",
        user=user_data,
        privacy_version=PRIVACY_POLICY_VERSION
    )

@app.route("/logged/dashboard/student")
@au.session_middleware.loginRequired(role="user")
def dashboardStudent():
    user = session["user"]
    data = database_helper.getUserById(user["googleId"])

    if not data:
        return redirect(url_for("completeLogin"))

    user_data = database_helper.modelToDict(data)
    user_data["indirizzo"] = _splitAddress(user_data["indirizzo"])

    preferences = user_data.get("preferences") or {}
    color_mode = preferences.get("color_mode") or "dark"
    lingua = preferences.get("lingua") or "it"
    default_transport_mode = preferences.get("default_transport_mode") or "driving-car"

    notifications_data = [
        _notificationToDict(notification)
        for notification in database_helper.getUserNotifications(user["googleId"])
    ]

    stats = database_helper.getRouteStats(user_data["routes"])
    stats["preferredModeLabel"] = TRANSPORT_MODE_LABELS.get(stats["preferredMode"])
    stats["preferredModeIconId"] = TRANSPORT_MODE_ICONS.get(stats["preferredMode"])

    return render_template(
        "/html/dashboard-student.html",
        user=user_data,
        notifications=notifications_data,
        stats=stats,
        app_version=APP_VERSION,
        support_email=SUPPORT_EMAIL,
        color_mode=color_mode,
        lingua=lingua,
        default_transport_mode=default_transport_mode
    )

@app.route("/logged/dashboard/company")
@au.session_middleware.loginRequired(role="company")
def dashboardCompany():
    user = session["user"]
    data = database_helper.getCompanyByGoogleId(user["googleId"])

    if not data:
        return au.renderAuthError(
            "Azienda non trovata.",
            url_for("loginCompany"),
            404,
            "Azienda non trovata",
            "🔍",
            "Vai al login"
        )

    company_data = database_helper.modelToDict(data)
    company_data["address_parts"] = _splitAddress(company_data.get("address"))
    color_mode = company_data.get("color_mode") or "dark"

    offers = database_helper.getJobOffersByCompany(user["googleId"])
    stats = {
        "activeOffers": sum(1 for o in offers if o.attivo),
        "totalApplications": sum(len(o.applications) for o in offers)
    }

    notifications_data = [
        _notificationToDict(notification)
        for notification in database_helper.getCompanyNotifications(user["googleId"])
    ]

    return render_template(
        "/html/home-company.html",
        company=company_data,
        stats=stats,
        notifications=notifications_data,
        support_email=SUPPORT_EMAIL,
        color_mode=color_mode
    )

@app.route('/logged/map')
@au.session_middleware.loginRequired(role="user")
def map():
    preferences = database_helper.getUserPreferences(session["user"]["googleId"])
    lingua = (preferences.lingua if preferences else None) or "it"
    default_transport_mode = (preferences.default_transport_mode if preferences else None) or "driving-car"

    return render_template(
        "/html/map-view.html",
        lingua=lingua,
        default_transport_mode=default_transport_mode
    )

@app.route("/api/users/profile")
@au.session_middleware.loginRequired(role="user")
def getUserProfile():
    id = session["user"]["googleId"]
    data = database_helper.getUserById(id)

    if not data:
        return _jsonError("User not found", 404)

    return database_helper.modelToDict(data)

@app.route("/api/users/profile/save", methods=["POST"])
@au.session_middleware.loginRequired(role="user")
def saveProfile():
    try:
        data = request.get_json(silent=True)

        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid JSON"}), 400

        session_user = session["user"]
        data = validation.normalizeProfile(data)
        data["googleId"] = session_user["googleId"]
        # L'email è l'identità Google: non modificabile dal profilo.
        data.pop("email", None)

        database_helper.updateUser(data)
        updated_user = database_helper.getUserById(session_user["googleId"])

        if not updated_user:
            return jsonify({"error": "User not found"}), 404

        matching_worker.enqueue(
            lambda: matching_engine.recomputeMatchesForStudent(session_user["googleId"]),
            name=f"student:{session_user['googleId']}"
        )

        return jsonify({
            "message": "Profile updated",
            "user": database_helper.modelToDict(updated_user)
        }), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    except IntegrityError:
        return jsonify({"error": "Alcuni dati sono già in uso da un altro account"}), 409

    except Exception:
        app.logger.exception("profile save endpoint failed")

        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/users/preferences/save", methods=["POST"])
@au.session_middleware.loginRequired(role="user")
def savePreferences():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    color_mode = data.get("color_mode")
    lingua = data.get("lingua")
    default_transport_mode = data.get("default_transport_mode")

    if color_mode is not None and color_mode not in ("dark", "light"):
        return jsonify({"error": "color_mode non valido"}), 400

    if lingua is not None and lingua not in ("it", "en"):
        return jsonify({"error": "lingua non valida"}), 400

    if default_transport_mode is not None and default_transport_mode not in VALID_TRANSPORT_MODES:
        return jsonify({"error": "mezzo non valido"}), 400

    preferences = database_helper.updateUserPreferences(
        session["user"]["googleId"],
        color_mode=color_mode,
        lingua=lingua,
        default_transport_mode=default_transport_mode
    )

    if preferences is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "color_mode": preferences.color_mode,
        "lingua": preferences.lingua,
        "default_transport_mode": preferences.default_transport_mode
    }), 200

@app.route("/api/companies/preferences/save", methods=["POST"])
@au.session_middleware.loginRequired(role="company")
def saveCompanyPreferences():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    color_mode = data.get("color_mode")

    if color_mode is not None and color_mode not in ("dark", "light"):
        return jsonify({"error": "color_mode non valido"}), 400

    update_data = {"googleId": session["user"]["googleId"]}
    if color_mode is not None:
        update_data["color_mode"] = color_mode

    company = database_helper.updateCompany(update_data)

    if company is None:
        return jsonify({"error": "Company not found"}), 404

    return jsonify({"color_mode": company.color_mode}), 200

@app.route("/api/users/sessions")
@au.session_middleware.loginRequired(role="user")
def getUserSessions():
    email = session["user"]["email"]
    current_session_id = session.get("session_id")
    sessions = au.rate_limiter.getUserSessions(email)

    return jsonify([
        {
            "created_at": s.created_at.isoformat(),
            "last_seen": s.last_seen.isoformat(),
            "is_current": s.session_id == current_session_id
        }
        for s in sessions
    ])

@app.route("/api/users/sessions/terminate-others", methods=["POST"])
@au.session_middleware.loginRequired(role="user")
def terminateOtherSessions():
    email = session["user"]["email"]
    current_session_id = session.get("session_id")
    au.rate_limiter.removeAllSessionsForUser(email, keep_session_id=current_session_id)

    return jsonify({"message": "Sessioni terminate"}), 200

@app.route("/api/users/routes")
@au.session_middleware.loginRequired(role="user")
def getUserRoutes():
    user = session["user"]
    data = database_helper.getUserById(user["googleId"])

    if not data:
        return jsonify([])

    return jsonify(database_helper.modelToDict(data)["routes"])

def _downloadJson(data: dict, filename: str):
    response = jsonify(data)
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response

def _endSession():
    session_id = session.get("session_id")

    if session_id:
        au.rate_limiter.removeSession(session_id)

    session.clear()

@app.route("/api/users/export")
@au.session_middleware.loginRequired(role="user")
def exportUserData():
    data = database_helper.exportUserData(session["user"]["googleId"])

    if data is None:
        return _jsonError("User not found", 404)

    return _downloadJson(data, "stagematch-i-miei-dati.json")

@app.route("/api/users/delete", methods=["POST"])
@au.session_middleware.loginRequired(role="user")
def deleteUserAccount():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict) or payload.get("confirm") is not True:
        return _jsonError("Conferma richiesta", 400)

    if not database_helper.deleteUser(session["user"]["googleId"]):
        return _jsonError("User not found", 404)

    _endSession()

    return jsonify({"redirect": url_for("loginStudent", notice="account_deleted")}), 200

@app.route("/api/company/export")
@au.session_middleware.loginRequired(role="company")
def exportCompanyData():
    data = database_helper.exportCompanyData(session["user"]["googleId"])

    if data is None:
        return _jsonError("Company not found", 404)

    return _downloadJson(data, "stagematch-dati-azienda.json")

@app.route("/api/company/delete", methods=["POST"])
@au.session_middleware.loginRequired(role="company")
def deleteCompanyAccount():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict) or payload.get("confirm") is not True:
        return _jsonError("Conferma richiesta", 400)

    if not database_helper.deleteCompany(session["user"]["googleId"]):
        return _jsonError("Company not found", 404)

    _endSession()

    return jsonify({"redirect": url_for("loginCompany", notice="account_deleted")}), 200

@app.route("/api/users/notifications/read", methods=["POST"])
@au.session_middleware.loginRequired(role="user")
def markNotificationRead():
    data = request.get_json()

    notification_id = _parseId(data.get("notification_id")) if isinstance(data, dict) else None

    if notification_id is None:
        return jsonify({"error": "Invalid JSON"}), 400

    user = session["user"]
    success = database_helper.markNotificationRead(user["googleId"], notification_id)

    if not success:
        return jsonify({"error": "Notification not found"}), 404

    return jsonify({"message": "Notification marked as read"}), 200

@app.route("/api/company/profile/save", methods=["POST"])
@au.session_middleware.loginRequired(role="company")
def saveCompanyProfile():
    try:
        data = request.get_json(silent=True)

        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid JSON"}), 400

        company_user = session["user"]
        data = validation.normalizeCompanyProfile(data)
        data["googleId"] = company_user["googleId"]

        previous = database_helper.getCompanyByGoogleId(company_user["googleId"])
        company = database_helper.updateCompany(data)

        if not company:
            return jsonify({"error": "Company not found"}), 404

        # Se cambia la sede, distanze e punteggi degli annunci attivi sono da rifare.
        if previous and "address" in data and data["address"] != previous.address:
            for offer in database_helper.getJobOffersByCompany(company_user["googleId"]):
                if offer.attivo:
                    matching_worker.enqueue(
                        lambda offer_id=offer.id: matching_engine.recomputeMatchesForJobOffer(offer_id),
                        name=f"job-offer:{offer.id}"
                    )

        return jsonify({"message": "Profile updated"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        app.logger.exception("company profile save endpoint failed")

        return jsonify({"error": "Internal server error"}), 500

def _jobOfferToDict(job_offer):
    return {
        "id": job_offer.id,
        "title": job_offer.title,
        "description": job_offer.description,
        "attivo": job_offer.attivo,
        "required_skills": [{"name": s.name, "livello_min": s.livello_min} for s in job_offer.required_skills],
        "required_soft_skills": [{"label": s.label, "icon": s.icon} for s in job_offer.required_soft_skills],
        "created_at": job_offer.created_at.isoformat()
    }

@app.route("/api/company/offers")
@au.session_middleware.loginRequired(role="company")
def getCompanyOffers():
    company = session["user"]
    offers = database_helper.getJobOffersByCompany(company["googleId"])

    return jsonify([
        {**_jobOfferToDict(o), "applications_count": len(o.applications)}
        for o in offers
    ])

@app.route("/api/company/offers", methods=["POST"])
@au.session_middleware.loginRequired(role="company")
def createCompanyOffer():
    company = session["user"]
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not str(data.get("title", "")).strip():
        return jsonify({"error": "Titolo obbligatorio"}), 400

    try:
        data = validation.normalizeJobOffer(data, require_title=True)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    offer_id = database_helper.addJobOffer(company["googleId"], data)

    if offer_id is None:
        return jsonify({"error": "Azienda non trovata"}), 404

    matching_worker.enqueue(
        lambda: matching_engine.recomputeMatchesForJobOffer(offer_id),
        name=f"job-offer:{offer_id}"
    )

    return jsonify({"message": "Annuncio creato", "id": offer_id}), 201

@app.route("/api/company/offers/<int:offer_id>/update", methods=["POST"])
@au.session_middleware.loginRequired(role="company")
def updateCompanyOffer(offer_id):
    company = session["user"]
    data = request.get_json(silent=True)

    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        data = validation.normalizeJobOffer(data, require_title=False)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    updated = database_helper.updateJobOffer(offer_id, company["googleId"], data)

    if not updated:
        return jsonify({"error": "Annuncio non trovato"}), 404

    matching_worker.enqueue(
        lambda: matching_engine.recomputeMatchesForJobOffer(offer_id),
        name=f"job-offer:{offer_id}"
    )

    return jsonify({"message": "Annuncio aggiornato"}), 200

@app.route("/api/company/offers/<int:offer_id>/close", methods=["POST"])
@au.session_middleware.loginRequired(role="company")
def closeCompanyOffer(offer_id):
    company = session["user"]
    success = database_helper.closeJobOffer(offer_id, company["googleId"])

    if not success:
        return jsonify({"error": "Annuncio non trovato"}), 404

    database_helper.deleteMatchesForJobOffer(offer_id)

    return jsonify({"message": "Annuncio chiuso"}), 200

@app.route("/api/company/applications")
@au.session_middleware.loginRequired(role="company")
def getCompanyApplications():
    company = session["user"]
    applications = database_helper.getApplicationsForCompany(company["googleId"])

    return jsonify([
        {
            "id": a.id,
            "status": a.status,
            "message": a.message,
            "created_at": a.created_at.isoformat(),
            "job_offer_id": a.job_offer_id,
            "job_offer_title": a.job_offer.title,
            "student": {
                "name": a.user.name,
                "surname": a.user.surname,
                "email": a.user.email,
                "classe": a.user.classe
            }
        }
        for a in applications
    ])

@app.route("/api/company/applications/<int:application_id>/status", methods=["POST"])
@au.session_middleware.loginRequired(role="company")
def updateCompanyApplicationStatus(application_id):
    company = session["user"]
    data = request.get_json()
    status = data.get("status") if data else None

    if status not in ("vista", "accettata", "rifiutata"):
        return jsonify({"error": "Stato non valido"}), 400

    application = database_helper.updateApplicationStatus(application_id, status, company["googleId"])

    if not application:
        return jsonify({"error": "Candidatura non trovata"}), 404

    if status in ("accettata", "rifiutata"):
        job_offer = database_helper.getJobOfferById(application.job_offer_id)
        title = job_offer.title if job_offer else "l'annuncio"
        outcome = "accettata" if status == "accettata" else "rifiutata"

        database_helper.addNotification(
            application.user_id,
            f"Candidatura {outcome}",
            f"La tua candidatura per \"{title}\" è stata {outcome}.",
            sender=job_offer.company.name if job_offer and job_offer.company else "stageMatch"
        )

    return jsonify({"message": "Stato aggiornato"}), 200

@app.route("/api/company/notifications")
@au.session_middleware.loginRequired(role="company")
def getCompanyNotificationsRoute():
    company = session["user"]
    notifications = database_helper.getCompanyNotifications(company["googleId"])

    return jsonify([_notificationToDict(n) for n in notifications])

@app.route("/api/company/notifications/read", methods=["POST"])
@au.session_middleware.loginRequired(role="company")
def markCompanyNotificationReadRoute():
    data = request.get_json()

    notification_id = _parseId(data.get("notification_id")) if isinstance(data, dict) else None

    if notification_id is None:
        return jsonify({"error": "Invalid JSON"}), 400

    company = session["user"]
    success = database_helper.markCompanyNotificationRead(company["googleId"], notification_id)

    if not success:
        return jsonify({"error": "Notification not found"}), 404

    return jsonify({"message": "Notification marked as read"}), 200

@app.route("/api/students/offers")
@au.session_middleware.loginRequired(role="user")
def getStudentOffers():
    user = session["user"]
    student = database_helper.getUserById(user["googleId"])

    if not student:
        return jsonify([])

    flat_student_address = matching_geo.flattenAddress(student.indirizzo)
    route_cache = database_helper.getUserRouteCache(user["googleId"], matching_geo.DEFAULT_MODE)
    matches = database_helper.getMatchesForStudent(user["googleId"])
    applications = database_helper.getApplicationsByStudent(user["googleId"])
    application_status_by_offer = {a.job_offer_id: a.status for a in applications}
    matched_offer_ids = {m.job_offer_id for m in matches}

    def offerCardData(offer, final_score, ai_status, explanation):
        company = offer.company
        flat_company_address = matching_geo.flattenAddress(company.address)
        distance_km, duration_min = route_cache.get(
            (flat_student_address, flat_company_address), (None, None)
        )

        return {
            "id": offer.id,
            "title": offer.title,
            "description": offer.description,
            "company_name": company.name,
            "company_settore": company.settore,
            "company_descrizione": company.descrizione,
            "company_address": flat_company_address,
            "company_email": company.email,
            "company_sito_web": company.sito_web,
            "company_telefono": company.telefono,
            "required_skills": [{"name": s.name, "livello_min": s.livello_min} for s in offer.required_skills],
            "required_soft_skills": [{"label": s.label, "icon": s.icon} for s in offer.required_soft_skills],
            "final_score": final_score,
            "ai_status": ai_status,
            "explanation": explanation,
            "distance_km": distance_km,
            "duration_min": duration_min,
            "application_status": application_status_by_offer.get(offer.id)
        }

    result = [
        offerCardData(m.job_offer, m.final_score, m.ai_status, m.explanation)
        for m in matches
    ]

    for offer in database_helper.getActiveJobOffers():
        if offer.id in matched_offer_ids:
            continue

        result.append(offerCardData(offer, None, "pending", None))

    return jsonify(result)

@app.route("/api/students/offers/<int:job_offer_id>/apply", methods=["POST"])
@au.session_middleware.loginRequired(role="user")
def applyToOffer(job_offer_id):
    user = session["user"]
    data = request.get_json(silent=True) or {}
    message = data.get("message")

    try:
        message = validation.cleanText(message, "messaggio", validation.MAX_LONG_TEXT)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    job_offer = database_helper.getJobOfferById(job_offer_id)

    if not job_offer or not job_offer.attivo:
        return jsonify({"error": "Annuncio non disponibile"}), 404

    student = database_helper.getUserById(user["googleId"])

    if not student:
        return jsonify({"error": "Completa la registrazione prima di candidarti"}), 403

    try:
        database_helper.addApplication(user["googleId"], job_offer_id, message)
    except (ApplicationAlreadyExistsError, IntegrityError):
        return jsonify({"error": "Ti sei già candidato a questo annuncio"}), 409

    database_helper.addCompanyNotification(
        job_offer.company_id,
        "Nuova candidatura ricevuta",
        f"{student.name} {student.surname} si è candidato/a per l'annuncio \"{job_offer.title}\".",
        sender="stageMatch"
    )

    return jsonify({"message": "Candidatura inviata"}), 201

PHOTON_PARAMS = ("q", "lat", "lon", "limit", "lang")

def _geoProxyGet(path: str, params: dict):
    """Chiama il geo-proxy (server.py). Ritorna (json, status) oppure (None, None) se non raggiungibile."""
    api_url = os.getenv("API_URL", "http://127.0.0.1:5001")

    try:
        response = requests.get(f"{api_url}{path}", params=params, timeout=15)

        return response.json(), response.status_code
    except (requests.RequestException, ValueError):
        app.logger.warning(f"geo-proxy non raggiungibile o risposta non valida ({path})")

        return None, None

@app.route("/photon", methods=["POST"])
@au.session_middleware.loginRequired(role="user")
def photon():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return _jsonError("Parametri non validi", 400)

    params = {key: payload[key] for key in PHOTON_PARAMS if isinstance(payload.get(key), (str, int, float))}

    data, status = _geoProxyGet("/photon", params)

    if data is None:
        return _jsonError("Servizio di ricerca indirizzi non disponibile", 502)

    return data, status

@app.route("/routejson", methods=["POST"])
@au.session_middleware.loginRequired(role="user")
def routejson():
    user = session["user"]
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return _jsonError("Parametri non validi", 400)

    start_address = payload.get("startaddress")
    end_address = payload.get("endaddress")
    route_mode = payload.get("routemode") or "driving-car"

    if not all(isinstance(value, str) and value.strip() for value in (start_address, end_address)):
        return _jsonError("Indirizzi di partenza e arrivo obbligatori", 400)

    if route_mode not in VALID_TRANSPORT_MODES:
        return _jsonError("Mezzo di trasporto non valido", 400)

    params = {"startaddress": start_address, "endaddress": end_address, "routemode": route_mode}
    response_data, status = _geoProxyGet("/routejson", params)

    if response_data is None:
        return _jsonError("Servizio di calcolo percorsi non disponibile", 502)

    if 200 <= status < 300 and "error" not in response_data:
        distance_km, duration_min = matching_geo.parseRouteSummary(response_data)

        database_helper.addUserRoute(user["googleId"], {
            **params,
            "distance_km": distance_km,
            "duration_min": duration_min
        })

    return response_data, status

@app.route("/admin/codes")
@adminRequired
def adminCodes():
    return render_template("/html/admin-codes.html", app_version=APP_VERSION)

@app.route("/api/admin/codes")
@adminRequired
def listAccessCodes():
    return jsonify([
        {
            "code": c.code,
            "created_at": c.created_at.isoformat(),
            "used": c.used_at is not None,
            "used_at": c.used_at.isoformat() if c.used_at else None
        }
        for c in database_helper.listAccessCodes()
    ])

@app.route("/api/admin/codes", methods=["POST"])
@adminRequired
def createAccessCode():
    code = database_helper.createAccessCode(session["user"]["email"])

    return jsonify({"code": code}), 201

def _wantsJson() -> bool:
    return request.path.startswith(("/api/", "/photon", "/routejson"))

@app.errorhandler(404)
def notFound(e):
    if _wantsJson():
        return _jsonError("Risorsa non trovata", 404)

    return au.renderAuthError(
        "Page not found",
        url_for("mainPage"),
        404,
        "Page not found",
        "🔍",
        "Torna alla Home"
    )

@app.errorhandler(403)
def forbidden(e):
    if _wantsJson():
        return _jsonError("Accesso non consentito", 403)

    return au.renderAuthError(
        "Forbidden access",
        url_for("mainPage"),
        403,
        "Forbidden access",
        "🚫",
        "Torna alla Home"
    )

@app.errorhandler(405)
def methodNotAllowed(e):
    return _jsonError("Metodo non consentito", 405)

@app.errorhandler(413)
def payloadTooLarge(e):
    return _jsonError("Richiesta troppo grande", 413)

@app.errorhandler(500)
def serverError(e):
    if _wantsJson():
        return _jsonError("Errore interno del server", 500)

    return au.renderAuthError(
        "Si è verificato un errore imprevisto.",
        url_for("mainPage"),
        500,
        "Errore del server",
        "⚠️",
        "Torna alla Home"
    )

if __name__ == '__main__':
    app.logger.info("[INFO] stageMatch started")
    app.logger.info(f"Rate limit: max {au.rate_limiter.maxSessionsPerUser} per user and max {au.rate_limiter.maxSessionsGlobal} per global")

    app.run(
        os.getenv("HOST", "127.0.0.1"),
        int(os.getenv("PORT", 5000)),
        debug=DEBUG
    )
