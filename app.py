import os
import secrets
import requests
from flask import Flask, render_template, redirect, request, session, url_for, jsonify
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import timedelta
import auth.auth as au
from auth.auth_google.auth import initGoogleAuth, getGoogleUserInfo
from database import database_helper

load_dotenv()

PRIVACY_POLICY_VERSION = os.getenv("PRIVACY_POLICY_VERSION")

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

app = Flask(
    __name__,
    static_folder="./resources",
    template_folder="./resources"
)
google = initGoogleAuth(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
app.secret_key = os.getenv("SERVER_SECRET_KEY")
app.permanent_session_lifetime = timedelta(hours=8)

if os.getenv("DEBUG", "False").lower() != "true":
    app.config.update(
        SESSION_COOKIE_SECURE=True,
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

def _completeLogin(user_data: dict):
    email = user_data.get("email", "")

    session_id = secrets.token_hex(32)
    allowed, reason = au.rate_limiter.registerSession(session_id, email)

    if not allowed:
        app.logger.warning(f"[WARNING] rate limit reached for {email}")

        auth_type = session.get("auth_type", "user")

        return au.renderAuthError(
            reason,
            url_for("loginCompany" if auth_type == "company" else "loginStudent"),
            429,
            "Too many active sessions",
            "⏱️",
            "Vai al login"
        )

    app.logger.info(f"[INFO] User {email} logged in with session ID: {session_id}")

    au.session_middleware.createSession(user_data, session, session_id)

    return redirect(url_for("completeLogin"))

@app.route('/')
def mainPage():
    return render_template("html/landing.html")

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
    return render_template("/html/privacy.html", privacy_version=PRIVACY_POLICY_VERSION)

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
        print(user_data)
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
    except Exception as e:
        app.logger.error(f"[ERROR] Google callback failed: {e}")
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
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dati invalidi"}), 400

        session["pending_company_data"] = data
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
            company_data = {
                "googleId": user["googleId"],
                "name": pending_data["name"],
                "email": user["email"],
                "access_code": pending_data["access_code"],
                "address": f"{pending_data['via']} ££ {pending_data['civico']} ££ {pending_data['cap']} ££ {pending_data['citta']}",
                "picture": user["picture"]
            }
            database_helper.addCompany(company_data)
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

        user_data = {
            "googleId": user["googleId"],
            "name": au.getName(user["email"]),
            "surname": au.getSurname(user["email"]),
            "email": user["email"],
            "data_nascita": data["data_nascita"],
            "sesso": data["sesso"],
            "comune_nascita": data["comune_nascita"],
            "codice_fiscale": data["codice_fiscale"],
            "telefono": data["telefono"],
            "indirizzo_studio": data["indirizzo_studio"],
            "classe": data["classe"],
            "indirizzo": f"{data['via']} ££ {data['civico']} ££ {data['cap']} ££ {data['citta_residenza']}",
            "picture": user["picture"]
        }

        database_helper.addUser(
            user_data,
            privacy_consent={
                "privacy_version": PRIVACY_POLICY_VERSION
            }
        )

        database_helper.addNotification(
            user["googleId"],
            "Benvenuto su stageMatch!",
            "La tua registrazione è avvenuta con successo. Completa il tuo profilo per iniziare a ricevere match con le aziende.",
            sender="stageMatch"
        )

        return redirect(url_for("dashboardStudent"))

    user_data = {
        "name": au.getName(user["email"]),
        "surname": au.getSurname(user["email"]),
        "email": user["email"]
    }

    return render_template("/html/complete-login.html", user=user_data, privacy_version=PRIVACY_POLICY_VERSION)

@app.route("/logged/dashboard/student")
@au.session_middleware.loginRequired(role="user")
def dashboardStudent():
    user = session["user"]
    data = database_helper.getUserById(user["googleId"])
    user_data = database_helper.modelToDict(data)
    user_data["indirizzo"] = [dato.strip() for dato in user_data["indirizzo"].split("££")]

    notifications = database_helper.getUserNotifications(user["googleId"])
    notifications_data = [
        {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "sender": notification.sender,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat()
        }
        for notification in notifications
    ]

    stats = database_helper.getRouteStats(user_data["routes"])
    stats["preferredModeLabel"] = TRANSPORT_MODE_LABELS.get(stats["preferredMode"])
    stats["preferredModeIconId"] = TRANSPORT_MODE_ICONS.get(stats["preferredMode"])

    return render_template(
        "/html/dashboard-student.html",
        user=user_data,
        notifications=notifications_data,
        stats=stats
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

    return render_template("/html/home-company.html", company=company_data)

@app.route('/logged/map')
@au.session_middleware.loginRequired(role="user")
def map():
    return render_template("/html/map-view.html")

@app.route("/api/users/profile")
@au.session_middleware.loginRequired(role="user")
def getUserProfile():
    id = session["user"]["googleId"]
    data = database_helper.getUserById(id)

    return database_helper.modelToDict(data)

@app.route("/api/users/profile/save", methods=["POST"])
@au.session_middleware.loginRequired(role="user")
def saveProfile():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        session_user = session["user"]
        data["googleId"] = session_user["googleId"]

        database_helper.updateUser(data)
        updated_user = database_helper.getUserById(session_user["googleId"])

        if not updated_user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "message": "Profile updated",
            "user": database_helper.modelToDict(updated_user)
        }), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        app.logger.exception("[ERROR] profile save endpoint failed")

        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/users/routes")
def getUserRoutes():
    user = session["user"]
    data = database_helper.getUserById(user["googleId"])
    user_data = database_helper.modelToDict(data)
    routes = user_data["routes"]
    print(routes)

    return jsonify(routes)

@app.route("/api/users/notifications/read", methods=["POST"])
@au.session_middleware.loginRequired(role="user")
def markNotificationRead():
    data = request.get_json()

    if not data or "notification_id" not in data:
        return jsonify({"error": "Invalid JSON"}), 400

    user = session["user"]
    success = database_helper.markNotificationRead(user["googleId"], data["notification_id"])

    if not success:
        return jsonify({"error": "Notification not found"}), 404

    return jsonify({"message": "Notification marked as read"}), 200

@app.route("/api/data", methods=["GET", "POST"])
def getAndSendData():
    pass

@app.route("/photon", methods=["POST"])
@au.session_middleware.loginRequired(role="user")
def photon():
    params = request.get_json()
    api_url = os.getenv("API_URL", "http://127.0.0.1:5001")
    response = requests.get(f"{api_url}/photon", params=params, timeout=5)

    return response.json(), response.status_code

@app.route("/routejson", methods=["POST"])
@au.session_middleware.loginRequired(role="user")
def routejson():
    user = session["user"]
    params = request.get_json()
    data = dict(params)

    api_url = os.getenv("API_URL", "http://127.0.0.1:5001")
    response = requests.get(f"{api_url}/routejson", params=params, timeout=5)
    response_data = response.json()

    if response.ok and "error" not in response_data:
        try:
            distance_m = response_data["features"][0]["properties"]["summary"]["distance"]
            data["distance_km"] = distance_m / 1000
        except (KeyError, IndexError, TypeError):
            data["distance_km"] = None

        database_helper.addUserRoute(user["googleId"], data)

    return response_data, response.status_code

@app.errorhandler(404)
def notFound(e):
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
    return au.renderAuthError(
        "Forbidden access",
        url_for("mainPage"),
        403,
        "Forbidden access",
        "🚫",
        "Torna alla Home"
    )

if __name__ == '__main__':
    app.logger.info("[INFO] stageMatch started")
    app.logger.info(f"Rate limit: max {au.rate_limiter.maxSessionsPerUser} per user and max {au.rate_limiter.maxSessionsGlobal} per global")

    app.run(
        os.getenv("HOST", "127.0.0.1"),
        int(os.getenv("PORT", 5000)),
        debug=os.getenv("DEBUG", "False").lower() == "true"
    )
