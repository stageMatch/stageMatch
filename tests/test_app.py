import pytest

from conftest import makeCompany, makeUser


@pytest.fixture
def app_module(db):
    import app as app_module

    app_module.app.config["TESTING"] = True

    return app_module


@pytest.fixture
def client(app_module):
    return app_module.app.test_client()


def login(client, app_module, google_id, email, auth_type):
    """Simula un login completato: sessione Flask + sessione attiva del rate limiter."""
    session_id = f"sid-{google_id}"
    app_module.au.rate_limiter.registerSession(session_id, email)

    with client.session_transaction() as sess:
        sess["user"] = {"email": email, "name": "Nome Cognome", "googleId": google_id, "picture": ""}
        sess["session_id"] = session_id
        sess["auth_type"] = auth_type


def test_security_headers_present(client):
    response = client.get("/login")

    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_removed_stub_endpoint_is_gone(client):
    assert client.get("/api/data").status_code == 404


def test_api_errors_are_json(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.is_json


def test_student_cannot_use_company_routes(client, app_module, db):
    db.addUser(makeUser())
    login(client, app_module, "u1", "rossi.mario@example.com", "user")

    assert client.get("/api/company/offers").status_code == 403


def test_company_cannot_use_student_routes(client, app_module, db):
    db.addCompany(makeCompany())
    login(client, app_module, "c1", "hr@azienda.it", "company")

    assert client.get("/api/students/offers").status_code == 403
    assert client.get("/api/users/routes").status_code == 403


def test_routes_require_login(client):
    response = client.get("/api/users/routes")

    assert response.status_code == 302


def test_session_without_session_id_is_rejected(client, db):
    with client.session_transaction() as sess:
        sess["user"] = {"email": "a@b.it", "googleId": "u1"}
        sess["auth_type"] = "user"

    assert client.get("/api/users/profile").status_code == 302


def test_save_profile_rejects_bad_input_with_400(client, app_module, db):
    db.addUser(makeUser())
    login(client, app_module, "u1", "rossi.mario@example.com", "user")

    for payload in (
        {"skills": [{"name": "Python", "livello": 9}]},
        {"skills": [{"livello": 1}]},
        {"languages": [{"name": "Inglese", "level": "ZZ"}]},
        {"experiences": [{"title": "x", "link": "javascript:alert(1)"}]},
        {"codice_fiscale": "non-valido"},
    ):
        assert client.post("/api/users/profile/save", json=payload).status_code == 400, payload


def test_save_profile_ignores_email_change_and_dedups_skills(client, app_module, db):
    db.addUser(makeUser())
    login(client, app_module, "u1", "rossi.mario@example.com", "user")

    response = client.post("/api/users/profile/save", json={
        "email": "evil@example.com",
        "skills": [{"name": "Python", "livello": 1}, {"name": "python", "livello": 2}],
        "preferences": {"user_id": "hacker", "color_mode": "light"},
    })

    assert response.status_code == 200
    user = db.getUserById("u1")
    assert user.email == "rossi.mario@example.com"
    assert [(s.name, s.livello) for s in user.skills] == [("python", 2)]
    assert user.preferences.user_id == "u1"


def test_company_profile_rejects_xss_in_website(client, app_module, db):
    db.addCompany(makeCompany())
    login(client, app_module, "c1", "hr@azienda.it", "company")

    bad = client.post("/api/company/profile/save", json={"sito_web": 'x" onmouseover="alert(1)'})
    good = client.post("/api/company/profile/save", json={"sito_web": "acme.it"})

    assert bad.status_code == 400
    assert good.status_code == 200
    assert db.getCompanyByGoogleId("c1").sito_web == "https://acme.it"


def test_company_address_change_enqueues_recompute(client, app_module, db, monkeypatch):
    db.addCompany(makeCompany())
    offer_id = db.addJobOffer("c1", {"title": "Stage"})
    login(client, app_module, "c1", "hr@azienda.it", "company")

    names = []
    monkeypatch.setattr(app_module.matching_worker, "enqueue", lambda fn, name=None: names.append(name))

    client.post("/api/company/profile/save", json={"address": "Via Nuova ££ 9 ££ 24100 ££ Bergamo"})
    client.post("/api/company/profile/save", json={"address": "Via Nuova ££ 9 ££ 24100 ££ Bergamo"})

    assert names == [f"job-offer:{offer_id}"]  # secondo salvataggio identico: nessun ricalcolo


def test_apply_checks_offer_exists_and_is_active(client, app_module, db):
    db.addUser(makeUser())
    db.addCompany(makeCompany())
    offer_id = db.addJobOffer("c1", {"title": "Stage"})
    login(client, app_module, "u1", "rossi.mario@example.com", "user")

    assert client.post("/api/students/offers/9999/apply", json={}).status_code == 404
    assert client.post(f"/api/students/offers/{offer_id}/apply", json={}).status_code == 201
    assert client.post(f"/api/students/offers/{offer_id}/apply", json={}).status_code == 409

    db.closeJobOffer(offer_id, "c1")
    other = db.addJobOffer("c1", {"title": "Altro"})
    db.closeJobOffer(other, "c1")
    assert client.post(f"/api/students/offers/{other}/apply", json={}).status_code == 404
    assert len(db.getCompanyNotifications("c1")) == 1


def test_accepting_application_notifies_student(client, app_module, db):
    db.addUser(makeUser())
    db.addCompany(makeCompany())
    offer_id = db.addJobOffer("c1", {"title": "Stage"})
    application_id = db.addApplication("u1", offer_id, None)
    login(client, app_module, "c1", "hr@azienda.it", "company")

    assert client.post(f"/api/company/applications/{application_id}/status", json={"status": "accettata"}).status_code == 200

    notifications = db.getUserNotifications("u1")
    assert notifications[0].title == "Candidatura accettata"


def test_company_registration_requires_valid_single_use_code(client, db):
    payload = {"name": "Acme", "via": "Via A", "civico": "1", "cap": "24100", "citta": "Bergamo", "terms_ack": True}

    assert client.post("/auth/company/login", json={**payload, "access_code": "sbagliato"}).status_code == 403
    assert client.post("/auth/company/login", json={**payload, "access_code": ""}).status_code == 400

    code = db.createAccessCode("admin@example.com")
    assert client.post("/auth/company/login", json={**payload, "access_code": code}).status_code == 200

    with client.session_transaction() as sess:
        assert sess["pending_company_data"]["access_code"] == code


def test_admin_codes_only_for_admin_emails(client, app_module, db):
    login(client, app_module, "u9", "someone@example.com", "user")
    assert client.get("/api/admin/codes").status_code == 403
    assert client.post("/api/admin/codes").status_code == 403

    login(client, app_module, "admin", "admin@example.com", "user")
    created = client.post("/api/admin/codes")

    assert created.status_code == 201
    listed = client.get("/api/admin/codes").get_json()
    assert listed[0]["code"] == created.get_json()["code"] and listed[0]["used"] is False


def test_routejson_validates_input(client, app_module, db):
    db.addUser(makeUser())
    login(client, app_module, "u1", "rossi.mario@example.com", "user")

    assert client.post("/routejson", json={"startaddress": "A"}).status_code == 400
    assert client.post("/routejson", json={"startaddress": "A", "endaddress": "B", "routemode": "../x"}).status_code == 400
    # proxy non raggiungibile (API_URL punta a una porta chiusa)
    assert client.post("/routejson", json={"startaddress": "A", "endaddress": "B"}).status_code == 502
    assert client.post("/photon", json={"q": "Ber"}).status_code == 502


def test_dashboard_without_profile_redirects_to_onboarding(client, app_module, db):
    login(client, app_module, "newbie", "new.user@example.com", "user")
    response = client.get("/logged/dashboard/student")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/logged/complete")


def test_cross_site_writes_are_rejected(client, app_module, db):
    db.addUser(makeUser())
    login(client, app_module, "u1", "rossi.mario@example.com", "user")

    evil = client.post("/api/users/sessions/terminate-others", headers={"Origin": "https://evil.example"})
    fetch_meta = client.post("/api/users/sessions/terminate-others", headers={"Sec-Fetch-Site": "cross-site"})
    same_site = client.post("/api/users/sessions/terminate-others", headers={"Origin": "http://localhost"})

    assert evil.status_code == 403
    assert fetch_meta.status_code == 403
    assert same_site.status_code == 200


def test_user_export_contains_personal_data(client, app_module, db):
    db.addUser(makeUser(), privacy_consent={"privacy_version": "1.0"})
    db.addCompany(makeCompany())
    offer_id = db.addJobOffer("c1", {"title": "Stage"})
    db.addApplication("u1", offer_id, "ciao")
    db.updateUser({"googleId": "u1", "skills": [{"name": "Python", "livello": 2}]})
    login(client, app_module, "u1", "rossi.mario@example.com", "user")

    response = client.get("/api/users/export")
    data = response.get_json()

    assert response.status_code == 200
    assert "attachment" in response.headers["Content-Disposition"]
    assert data["profile"]["codice_fiscale"] == "RSSMRA07A01A794X"
    assert data["skills"] == [{"name": "Python", "livello": 2}]
    assert data["applications"][0]["job_offer_title"] == "Stage"
    assert data["privacy_consents"][0]["privacy_version"] == "1.0"


def test_user_delete_requires_confirmation_and_removes_everything(client, app_module, db):
    db.addUser(makeUser(), privacy_consent={"privacy_version": "1.0"})
    db.addCompany(makeCompany())
    offer_id = db.addJobOffer("c1", {"title": "Stage"})
    db.addApplication("u1", offer_id, None)
    db.upsertMatch("u1", offer_id, 50, None, 50, None, "disabled")
    login(client, app_module, "u1", "rossi.mario@example.com", "user")

    assert client.post("/api/users/delete", json={}).status_code == 400
    assert db.existUser("u1")

    response = client.post("/api/users/delete", json={"confirm": True})

    assert response.status_code == 200
    assert "account_deleted" in response.get_json()["redirect"]
    assert not db.existUser("u1")
    assert db.getMatchesForStudent("u1") == []
    assert db.getApplicationsByStudent("u1") == []
    assert db.countActiveSessions() == 0
    assert client.get("/api/users/profile").status_code == 302  # sessione terminata


def test_company_delete_removes_offers_and_applications(client, app_module, db):
    db.addUser(makeUser())
    db.addCompany(makeCompany(), privacy_version="1.0")
    offer_id = db.addJobOffer("c1", {"title": "Stage", "required_skills": [{"name": "Python", "livello_min": 1}]})
    db.addApplication("u1", offer_id, None)
    login(client, app_module, "c1", "hr@azienda.it", "company")

    export = client.get("/api/company/export").get_json()
    assert export["job_offers"][0]["applications_count"] == 1
    assert export["privacy_consents"][0]["privacy_version"] == "1.0"

    assert client.post("/api/company/delete", json={"confirm": True}).status_code == 200
    assert not db.existCompany("c1")
    assert db.getJobOfferById(offer_id) is None
    assert db.getApplicationsByStudent("u1") == []


def test_company_registration_requires_terms_ack(client, db):
    code = db.createAccessCode("admin@example.com")
    payload = {"name": "Acme", "via": "Via A", "civico": "1", "cap": "24100", "citta": "Bergamo", "access_code": code}

    assert client.post("/auth/company/login", json=payload).status_code == 400
    assert client.post("/auth/company/login", json={**payload, "terms_ack": True}).status_code == 200


def test_pages_render(client, app_module, db):
    db.addUser(makeUser(), privacy_consent={"privacy_version": "1.0"})
    db.addCompany(makeCompany(address="Via Milano ££ 2 ££ 24100 ££ Bergamo"))

    for path in ("/", "/login", "/login/student", "/login/company", "/privacy", "/terms"):
        assert client.get(path).status_code == 200, path

    login(client, app_module, "u1", "rossi.mario@example.com", "user")
    student = client.get("/logged/dashboard/student")
    assert student.status_code == 200
    assert b"data-account-delete" in student.data
    assert client.get("/logged/map").status_code == 200

    login(client, app_module, "c1", "hr@azienda.it", "company")
    company = client.get("/logged/dashboard/company")
    assert company.status_code == 200
    assert b"Via Milano, 2, 24100, Bergamo" in company.data
    assert b"Codice di Accesso" not in company.data

    login(client, app_module, "admin", "admin@example.com", "user")
    assert client.get("/admin/codes").status_code == 200


def _studentForm(app_module, **overrides):
    form = {
        "privacy_ack": "on", "privacy_version": app_module.PRIVACY_POLICY_VERSION,
        "nome": "Maria Grazia", "cognome": "De Luca", "data_nascita": "2008-05-01", "sesso": "F",
        "comune_nascita": "Bergamo", "codice_fiscale": "DLCMGR08E41A794X", "telefono": "3331234567",
        "indirizzo_studio": "Informatica", "classe": "4A", "istituto": "ITIS",
        "via": "Via A", "civico": "1", "cap": "24100", "citta_residenza": "Bergamo",
    }
    form.update(overrides)

    return form


def test_complete_student_uses_editable_name(client, app_module, monkeypatch, db):
    monkeypatch.setattr(app_module.matching_worker, "enqueue", lambda fn, name=None: None)
    login(client, app_module, "s1", "rossi.mario.studente@scuola.it", "user")

    response = client.post("/logged/complete", data=_studentForm(app_module))

    assert response.status_code == 302
    user = db.getUserById("s1")
    assert (user.name, user.surname) == ("Maria Grazia", "De Luca")


def test_complete_student_requires_name(client, app_module, db):
    login(client, app_module, "s1", "rossi.mario.studente@scuola.it", "user")

    response = client.post("/logged/complete", data=_studentForm(app_module, nome=" "))

    assert response.status_code == 400
    assert not db.existUser("s1")
