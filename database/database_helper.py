from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy.inspection import inspect
from .models.base import Base
from .models.user import User
from .models.company import Company
from .models.user_preferences import UserPreferences
from .models.skill import Skill
from .models.soft_skill import SoftSkill
from .models.route import UserRoute
from .models.notification import Notification
from .models.privacy_consent import PrivacyConsent
from .models.active_session import ActiveSession

# global
Session = None

def initDB(connstr: str):
    """Initialize the database engine and session."""
    global Session

    engine = create_engine(f"sqlite:///{connstr}", echo=True)
    Session = sessionmaker(bind=engine)

    Base.metadata.create_all(engine)

def getUserById(user_id: str):
    with Session() as session:
        return (
            session.query(User)
            .options(
                selectinload(User.preferences),
                selectinload(User.skills),
                selectinload(User.soft_skills),
                selectinload(User.routes),
                selectinload(User.notifications)
            )
            .filter_by(googleId=user_id)
            .first()
        )

def existUser(google_id: str) -> bool:
    """
        Check if the user exists
    """
    with Session() as session:
        return session.get(User, google_id) is not None

def existCompany(google_id: str) -> bool:
    """
        Check if the company exists by googleId
    """
    with Session() as session:
        return session.query(Company).filter_by(googleId=google_id).first() is not None

def getCompanyByGoogleId(google_id: str):
    with Session() as session:
        return session.query(Company).filter_by(googleId=google_id).first()

def addCompany(company_data: dict):
    with Session() as session:
        company = Company(**company_data)
        session.add(company)
        session.commit()

def getUserColumn(user_id: str, column: str):
    """Return a single column value of a user by id."""
    with Session() as session:
        user = session.query(User).filter_by(googleId=user_id).first()

        if not user:
            return None

        if not hasattr(user, column):
            raise ValueError(f"Column '{column}' does not exist in User model")

        return getattr(user, column)

def addUser(user_data: dict, privacy_consent: dict | None = None):
    with Session() as session:
        existing = session.query(User).filter_by(googleId=user_data["googleId"]).options(
            selectinload(User.preferences)
        ).first()

        if existing:
            raise UserAlreadyExistsError(
                f"User with id {user_data['googleId']} already exists!"
            )

        user = User(**user_data)
        user.preferences = UserPreferences(color_mode="light")

        session.add(user)
        session.flush()

        if privacy_consent:
            session.add(PrivacyConsent(
                user_id=user.googleId,
                privacy_version=privacy_consent["privacy_version"]
            ))

        session.commit()

def updateUser(user_data: dict):
    with Session() as session:
        user = session.query(User).filter_by(googleId=user_data["googleId"]).options(
            selectinload(User.preferences),
            selectinload(User.skills),
            selectinload(User.soft_skills)
        ).first()

        if not user:
            return None

        # Update simple fields
        for field in ["name", "surname", "email", "sesso", "comune_nascita", "codice_fiscale", "telefono", "indirizzo_studio", "classe", "indirizzo", "picture"]:
            if field in user_data:
                setattr(user, field, user_data[field])

        # Update date separately
        if "data_nascita" in user_data:
            try:
                user.data_nascita = datetime.strptime(user_data["data_nascita"], "%Y-%m-%d").date()
            except ValueError:
                pass

        # Ensure preferences exists
        if user.preferences is None:
            user.preferences = UserPreferences(color_mode="light")

        # Preferences
        pref_data = user_data.get("preferences")
        if pref_data:
            for key, value in pref_data.items():
                if hasattr(user.preferences, key):
                    setattr(user.preferences, key, value)

        # Skills
        skills = user_data.get("skills")
        if skills is not None:
            user.skills.clear()

            for skill_item in skills:
                nuova_skill = Skill(
                    name=skill_item["name"],
                    livello=skill_item["livello"]
                )
                user.skills.append(nuova_skill)

        # SoftSkills
        sskills = user_data.get("soft_skills")
        if sskills is not None:
            user.soft_skills.clear()

            for skill_item in sskills:
                nuova_skill = SoftSkill(
                    label=skill_item["label"],
                    icon=skill_item["icon"]
                )
                user.soft_skills.append(nuova_skill)

        # Commit changes
        session.add(user)
        session.commit()

def getUserPreferences(user_id: str):
    with Session() as session:
        user = (
            session.query(User)
            .options(selectinload(User.preferences))
            .filter_by(googleId=user_id)
            .first()
        )

        if not user:
            return None

        return user.preferences

def updateUserPreferences(user_id: str, color_mode: str):
    with Session() as session:
        user = session.query(User).filter_by(googleId=user_id).first()

        if not user:
            return None

        if user.preferences is None:
            user.preferences = UserPreferences(color_mode=color_mode)
        else:
            user.preferences.color_mode = color_mode

        session.commit()

        return user.preferences

def addUserRoute(user_id: str, route_data: dict):
    with Session() as session:
        user = session.query(User).filter_by(googleId=user_id).first()

        if not user:
            return None

        distance_km = route_data.get("distance_km")

        existing = next(
            (
                r for r in user.routes
                if r.start_address == route_data["startaddress"] and
                r.end_address == route_data["endaddress"] and
                r.mode == route_data["routemode"]
            ),
            None
        )

        if existing:
            existing.distance_km = distance_km
            existing.updated_at = datetime.now(timezone.utc)
            route = existing
        else:
            route = UserRoute(
                start_address=route_data["startaddress"],
                end_address=route_data["endaddress"],
                mode=route_data["routemode"],
                distance_km=distance_km
            )
            user.routes.append(route)

        if len(user.routes) > 25:
            user.routes = user.routes[:25]

        session.commit()

        return route

def getRouteStats(routes: list):
    """Aggrega la lista di percorsi (dict, es. user_data["routes"]) in statistiche
    per la dashboard: km totali, numero percorsi, mezzo preferito e ultimo percorso."""
    if not routes:
        return {
            "totalRoutes": 0,
            "totalKm": 0.0,
            "preferredMode": None,
            "lastRoute": None
        }

    total_km = sum(r.get("distance_km") or 0 for r in routes)

    occurrences = {}
    km_by_mode = {}
    for r in routes:
        mode = r.get("mode")
        occurrences[mode] = occurrences.get(mode, 0) + 1
        km_by_mode[mode] = km_by_mode.get(mode, 0) + (r.get("distance_km") or 0)

    max_occurrences = max(occurrences.values())
    tied_modes = [mode for mode, count in occurrences.items() if count == max_occurrences]

    if len(tied_modes) == 1:
        preferred_mode = tied_modes[0]
    else:
        preferred_mode = max(tied_modes, key=lambda mode: km_by_mode[mode])

    return {
        "totalRoutes": len(routes),
        "totalKm": total_km,
        "preferredMode": preferred_mode,
        "lastRoute": routes[0]
    }

def getUserNotifications(user_id: str):
    with Session() as session:
        return (
            session.query(Notification)
            .filter_by(user_id=user_id)
            .order_by(Notification.id.desc())
            .all()
        )

def markNotificationRead(user_id: str, notification_id: int) -> bool:
    with Session() as session:
        notification = session.get(Notification, notification_id)

        if not notification or notification.user_id != user_id:
            return False

        notification.is_read = True
        session.commit()

        return True

def addNotification(user_id: str, title: str, message: str, sender: str | None = None):
    """Create a notification for a user. Ready for future automatic/system or admin use."""
    with Session() as session:
        user = session.query(User).filter_by(googleId=user_id).first()

        if not user:
            return None

        notification = Notification(title=title, message=message, sender=sender)
        user.notifications.append(notification)

        session.commit()

        return {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "sender": notification.sender,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat()
        }

def addActiveSession(session_id: str, email: str):
    with Session() as session:
        now = datetime.now(timezone.utc)
        active_session = ActiveSession(
            session_id=session_id,
            email=email.lower(),
            created_at=now,
            last_seen=now
        )
        session.add(active_session)
        session.commit()

def touchActiveSession(session_id: str):
    with Session() as session:
        active_session = session.get(ActiveSession, session_id)

        if not active_session:
            return

        active_session.last_seen = datetime.now(timezone.utc)
        session.commit()

def removeActiveSession(session_id: str):
    with Session() as session:
        active_session = session.get(ActiveSession, session_id)

        if active_session:
            session.delete(active_session)
            session.commit()

def isActiveSessionValid(session_id: str, ttl_seconds: int) -> bool:
    with Session() as session:
        active_session = session.get(ActiveSession, session_id)

        if not active_session:
            return False

        last_seen = active_session.last_seen

        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)

        expires_at = last_seen + timedelta(seconds=ttl_seconds)

        return datetime.now(timezone.utc) <= expires_at

def getActiveSessionsByEmail(email: str):
    with Session() as session:
        return (
            session.query(ActiveSession)
            .filter_by(email=email.lower())
            .order_by(ActiveSession.created_at.asc())
            .all()
        )

def countActiveSessions() -> int:
    with Session() as session:
        return session.query(ActiveSession).count()

def deleteExpiredActiveSessions(ttl_seconds: int):
    with Session() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds)

        session.query(ActiveSession).filter(
            ActiveSession.last_seen < cutoff
        ).delete()
        session.commit()

def modelToDict(obj, include_relationships=True):
    result = {}

    mapper = inspect(obj)

    # Columns
    for column in mapper.mapper.column_attrs:
        result[column.key] = getattr(obj, column.key)

    # Relationships
    if include_relationships:
        for rel in mapper.mapper.relationships:
            value = getattr(obj, rel.key)

            if value is None:
                result[rel.key] = None
            elif rel.uselist:
                result[rel.key] = [modelToDict(item, False) for item in value]
            else:
                result[rel.key] = modelToDict(value, False)

    return result

class UserAlreadyExistsError(Exception):
    """Raised when trying to add a user that already exists."""

    pass
