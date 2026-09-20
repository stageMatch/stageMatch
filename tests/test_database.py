import pytest

from database.database_helper import InvalidAccessCodeError
from sqlalchemy.exc import IntegrityError

from conftest import makeCompany, makeUser


def route(i, mode="driving-car"):
    return {"startaddress": "A", "endaddress": f"B{i}", "routemode": mode, "distance_km": i, "duration_min": i}


def test_add_user_route_keeps_newest_when_cap_exceeded(db):
    db.addUser(makeUser())

    for i in range(db.MAX_USER_ROUTES + 5):
        db.addUserRoute("u1", route(i))

    routes = db.getUserById("u1").routes
    ends = {r.end_address for r in routes}

    assert len(routes) == db.MAX_USER_ROUTES
    assert f"B{db.MAX_USER_ROUTES + 4}" in ends  # l'ultimo inserito non viene scartato
    assert "B0" not in ends  # il più vecchio sì


def test_add_user_route_updates_existing_instead_of_duplicating(db):
    db.addUser(makeUser())
    db.addUserRoute("u1", route(1))
    db.addUserRoute("u1", {**route(1), "distance_km": 99})

    routes = db.getUserById("u1").routes

    assert len(routes) == 1
    assert routes[0].distance_km == 99


def test_route_cache_lookup(db):
    db.addUser(makeUser())
    db.addUserRoute("u1", route(1))

    assert db.getUserRouteCache("u1", "driving-car") == {("A", "B1"): (1, 1)}
    assert db.getUserRouteCache("u1", "foot-walking") == {}


def test_foreign_keys_are_enforced(db):
    with pytest.raises(IntegrityError):
        db.addApplication("ghost", 12345, "ciao")


def test_upsert_match_reports_created_flag(db):
    db.addUser(makeUser())
    db.addCompany(makeCompany())
    offer_id = db.addJobOffer("c1", {"title": "Stage"})

    assert db.upsertMatch("u1", offer_id, 50, None, 50, None, "disabled")[1] is True
    match_id, created = db.upsertMatch("u1", offer_id, 60, None, 60, None, "disabled")

    assert created is False
    assert [m.final_score for m in db.getMatchesForStudent("u1")] == [60]

    db.deleteMatchesForJobOffer(offer_id)
    assert db.getMatchesForStudent("u1") == []


def test_preferences_update_is_whitelisted(db):
    db.addUser(makeUser())
    db.updateUser({"googleId": "u1", "preferences": {"color_mode": "light", "user_id": "hacker"}})

    prefs = db.getUserPreferences("u1")

    assert prefs.color_mode == "light"
    assert prefs.user_id == "u1"


def test_access_code_is_single_use(db):
    code = db.createAccessCode("admin@example.com")

    assert db.isAccessCodeAvailable(code)

    db.addCompany(makeCompany(), access_code=code)

    assert not db.isAccessCodeAvailable(code)
    assert db.listAccessCodes()[0].used_by_company_id == "c1"

    with pytest.raises(InvalidAccessCodeError):
        db.addCompany(makeCompany("c2", "b@azienda.it"), access_code=code)

    assert not db.existCompany("c2")


def test_unknown_access_code_creates_nothing(db):
    with pytest.raises(InvalidAccessCodeError):
        db.addCompany(makeCompany(), access_code="nope")

    assert not db.existCompany("c1")
