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
from .models.language import Language
from .models.experience import Experience
from .models.route import UserRoute
from .models.notification import Notification
from .models.privacy_consent import PrivacyConsent
from .models.active_session import ActiveSession
from .models.job_offer import JobOffer
from .models.job_offer_skill import JobOfferSkill
from .models.job_offer_soft_skill import JobOfferSoftSkill
from .models.application import Application
from .models.match import Match

# global
Session = None

# Delimitatore usato per campi "lista" salvati come singola stringa (stessa
# convenzione di `indirizzo`, vedi app.py e CLAUDE.md).
LABEL_DELIMITER = " ££ "

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
                selectinload(User.languages),
                selectinload(User.experiences),
                selectinload(User.routes),
                selectinload(User.notifications),
                selectinload(User.applications),
                selectinload(User.matches)
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
        return (
            session.query(Company)
            .options(
                selectinload(Company.job_offers),
                selectinload(Company.notifications)
            )
            .filter_by(googleId=google_id)
            .first()
        )

def addCompany(company_data: dict):
    with Session() as session:
        company = Company(**company_data)
        session.add(company)
        session.commit()

def updateCompany(company_data: dict):
    with Session() as session:
        company = session.query(Company).filter_by(googleId=company_data["googleId"]).first()

        if not company:
            return None

        for field in ["name", "address", "picture", "settore", "descrizione", "sito_web", "telefono"]:
            if field in company_data:
                setattr(company, field, company_data[field])

        session.commit()
        session.refresh(company)

        return company

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
            selectinload(User.soft_skills),
            selectinload(User.languages),
            selectinload(User.experiences)
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

        # Languages
        languages = user_data.get("languages")
        if languages is not None:
            user.languages.clear()

            for lang_item in languages:
                name = str(lang_item.get("name", "")).strip()
                if not name:
                    continue

                user.languages.append(Language(
                    name=name,
                    level=lang_item.get("level", "A1"),
                    certification=(str(lang_item["certification"]).strip() or None)
                        if lang_item.get("certification") else None
                ))

        # Experiences
        experiences = user_data.get("experiences")
        if experiences is not None:
            user.experiences.clear()

            for exp_item in experiences:
                title = str(exp_item.get("title", "")).strip()
                if not title:
                    continue

                labels = exp_item.get("labels") or []
                sanitized_labels = [
                    str(label).strip().replace(LABEL_DELIMITER.strip(), "")
                    for label in labels if str(label).strip()
                ]

                user.experiences.append(Experience(
                    title=title,
                    description=(str(exp_item["description"]).strip() or None)
                        if exp_item.get("description") else None,
                    link=(str(exp_item["link"]).strip() or None)
                        if exp_item.get("link") else None,
                    labels=LABEL_DELIMITER.join(sanitized_labels)
                ))

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
        duration_min = route_data.get("duration_min")

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
            existing.duration_min = duration_min
            existing.updated_at = datetime.now(timezone.utc)
            route = existing
        else:
            route = UserRoute(
                start_address=route_data["startaddress"],
                end_address=route_data["endaddress"],
                mode=route_data["routemode"],
                distance_km=distance_km,
                duration_min=duration_min
            )
            user.routes.append(route)

        if len(user.routes) > 25:
            user.routes = user.routes[:25]

        session.commit()

        return route

def getStudentIdsWithAddress():
    """Studenti con un indirizzo compilato, candidati al calcolo del matching."""
    with Session() as session:
        rows = (
            session.query(User.googleId)
            .filter(User.indirizzo.isnot(None), User.indirizzo != "")
            .all()
        )

        return [row[0] for row in rows]

def getUserRouteByAddresses(user_id: str, start_address: str, end_address: str, mode: str):
    with Session() as session:
        return (
            session.query(UserRoute)
            .filter_by(
                user_id=user_id,
                start_address=start_address,
                end_address=end_address,
                mode=mode
            )
            .first()
        )

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

def addCompanyNotification(company_id: str, title: str, message: str, sender: str | None = None):
    """Create a notification for a company (e.g. a new application received)."""
    with Session() as session:
        company = session.query(Company).filter_by(googleId=company_id).first()

        if not company:
            return None

        notification = Notification(title=title, message=message, sender=sender)
        company.notifications.append(notification)

        session.commit()

        return {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "sender": notification.sender,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat()
        }

def getCompanyNotifications(company_id: str):
    with Session() as session:
        return (
            session.query(Notification)
            .filter_by(company_id=company_id)
            .order_by(Notification.id.desc())
            .all()
        )

def markCompanyNotificationRead(company_id: str, notification_id: int) -> bool:
    with Session() as session:
        notification = session.get(Notification, notification_id)

        if not notification or notification.company_id != company_id:
            return False

        notification.is_read = True
        session.commit()

        return True

# ============================================================
# JOB OFFERS
# ============================================================

def _applyJobOfferSkills(job_offer: JobOffer, data: dict):
    skills = data.get("required_skills")
    if skills is not None:
        job_offer.required_skills.clear()

        for skill_item in skills:
            job_offer.required_skills.append(JobOfferSkill(
                name=skill_item["name"],
                livello_min=skill_item["livello_min"]
            ))

    soft_skills = data.get("required_soft_skills")
    if soft_skills is not None:
        job_offer.required_soft_skills.clear()

        for skill_item in soft_skills:
            job_offer.required_soft_skills.append(JobOfferSoftSkill(
                label=skill_item["label"],
                icon=skill_item["icon"]
            ))

def addJobOffer(company_id: str, data: dict):
    with Session() as session:
        company = session.query(Company).filter_by(googleId=company_id).first()

        if not company:
            return None

        job_offer = JobOffer(
            title=data["title"],
            description=data.get("description")
        )
        _applyJobOfferSkills(job_offer, data)

        company.job_offers.append(job_offer)
        session.commit()
        session.refresh(job_offer)

        return job_offer.id

def getJobOfferById(job_offer_id: int):
    with Session() as session:
        return (
            session.query(JobOffer)
            .options(
                selectinload(JobOffer.company),
                selectinload(JobOffer.required_skills),
                selectinload(JobOffer.required_soft_skills)
            )
            .filter_by(id=job_offer_id)
            .first()
        )

def getJobOffersByCompany(company_id: str):
    with Session() as session:
        return (
            session.query(JobOffer)
            .options(
                selectinload(JobOffer.required_skills),
                selectinload(JobOffer.required_soft_skills),
                selectinload(JobOffer.applications)
            )
            .filter_by(company_id=company_id)
            .order_by(JobOffer.created_at.desc())
            .all()
        )

def getActiveJobOffers():
    with Session() as session:
        return (
            session.query(JobOffer)
            .options(
                selectinload(JobOffer.company),
                selectinload(JobOffer.required_skills),
                selectinload(JobOffer.required_soft_skills)
            )
            .filter_by(attivo=True)
            .all()
        )

def updateJobOffer(job_offer_id: int, company_id: str, data: dict):
    with Session() as session:
        job_offer = session.query(JobOffer).filter_by(id=job_offer_id).first()

        if not job_offer or job_offer.company_id != company_id:
            return None

        for field in ["title", "description"]:
            if field in data:
                setattr(job_offer, field, data[field])

        _applyJobOfferSkills(job_offer, data)

        session.commit()
        session.refresh(job_offer)

        return job_offer

def closeJobOffer(job_offer_id: int, company_id: str) -> bool:
    with Session() as session:
        job_offer = session.query(JobOffer).filter_by(id=job_offer_id).first()

        if not job_offer or job_offer.company_id != company_id:
            return False

        job_offer.attivo = False
        session.commit()

        return True

# ============================================================
# APPLICATIONS (CANDIDATURE)
# ============================================================

def addApplication(user_id: str, job_offer_id: int, message: str | None = None):
    with Session() as session:
        existing = (
            session.query(Application)
            .filter_by(user_id=user_id, job_offer_id=job_offer_id)
            .first()
        )

        if existing:
            raise ApplicationAlreadyExistsError(
                f"Application for job offer {job_offer_id} by user {user_id} already exists!"
            )

        application = Application(user_id=user_id, job_offer_id=job_offer_id, message=message)
        session.add(application)
        session.commit()
        session.refresh(application)

        return application.id

def getApplicationsByStudent(user_id: str):
    with Session() as session:
        return (
            session.query(Application)
            .options(
                selectinload(Application.job_offer).selectinload(JobOffer.company)
            )
            .filter_by(user_id=user_id)
            .all()
        )

def getApplicationsForCompany(company_id: str):
    with Session() as session:
        return (
            session.query(Application)
            .join(JobOffer, Application.job_offer_id == JobOffer.id)
            .options(
                selectinload(Application.user),
                selectinload(Application.job_offer)
            )
            .filter(JobOffer.company_id == company_id)
            .order_by(Application.created_at.desc())
            .all()
        )

def updateApplicationStatus(application_id: int, status: str, company_google_id: str):
    with Session() as session:
        application = (
            session.query(Application)
            .options(selectinload(Application.job_offer))
            .filter_by(id=application_id)
            .first()
        )

        if not application or application.job_offer.company_id != company_google_id:
            return None

        application.status = status
        session.commit()
        session.refresh(application)

        return application

# ============================================================
# MATCHES
# ============================================================

def getStudentMatchingProfile(user_id: str):
    """Solo i dati necessari al motore di matching (skill, soft skill, indirizzo)."""
    with Session() as session:
        user = (
            session.query(User)
            .options(
                selectinload(User.skills),
                selectinload(User.soft_skills),
                selectinload(User.languages),
                selectinload(User.experiences)
            )
            .filter_by(googleId=user_id)
            .first()
        )

        if not user:
            return None

        return {
            "googleId": user.googleId,
            "indirizzo": user.indirizzo,
            "skills": [{"name": s.name, "livello": s.livello} for s in user.skills],
            "soft_skills": [{"label": s.label} for s in user.soft_skills],
            # Dato oggettivo, utilizzabile come criterio di matching: niente certification.
            "languages": [{"name": l.name, "level": l.level} for l in user.languages],
            # Dato qualitativo: valutato dall'AI refiner, non dallo scoring deterministico.
            # Il link non viene mai esposto al motore di matching.
            "experiences": [
                {
                    "title": e.title,
                    "description": e.description,
                    "labels": [
                        label.strip()
                        for label in (e.labels or "").split(LABEL_DELIMITER.strip())
                        if label.strip()
                    ]
                }
                for e in user.experiences
            ]
        }

def upsertMatch(user_id: str, job_offer_id: int, deterministic_score: float,
                 ai_score: float | None, final_score: float,
                 explanation: str | None, ai_status: str):
    with Session() as session:
        match = (
            session.query(Match)
            .filter_by(user_id=user_id, job_offer_id=job_offer_id)
            .first()
        )

        if not match:
            match = Match(user_id=user_id, job_offer_id=job_offer_id)
            session.add(match)

        match.deterministic_score = deterministic_score
        match.ai_score = ai_score
        match.final_score = final_score
        match.explanation = explanation
        match.ai_status = ai_status
        match.computed_at = datetime.now(timezone.utc)

        session.commit()

        return match.id

def getMatchesForStudent(user_id: str):
    with Session() as session:
        return (
            session.query(Match)
            .options(
                selectinload(Match.job_offer).selectinload(JobOffer.company),
                selectinload(Match.job_offer).selectinload(JobOffer.required_skills),
                selectinload(Match.job_offer).selectinload(JobOffer.required_soft_skills)
            )
            .join(JobOffer, Match.job_offer_id == JobOffer.id)
            .filter(Match.user_id == user_id, JobOffer.attivo.is_(True))
            .order_by(Match.final_score.desc())
            .all()
        )

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

class ApplicationAlreadyExistsError(Exception):
    """Raised when a student tries to apply twice to the same job offer."""

    pass
