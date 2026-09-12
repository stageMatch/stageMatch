"""Orchestrazione del calcolo dei match: unisce database_helper, scorer, geo e ai_refiner.

Le due funzioni pubbliche sono pensate per essere eseguite in background
(vedi matching/worker.py), non nel thread della richiesta HTTP.
"""

import logging
from database import database_helper
from matching import scorer, geo, ai_refiner

logger = logging.getLogger(__name__)


def _requiredSkillsFor(job_offer) -> list[dict]:
    return [{"name": s.name, "livello_min": s.livello_min} for s in job_offer.required_skills]


def _requiredSoftSkillsFor(job_offer) -> list[dict]:
    return [{"label": s.label} for s in job_offer.required_soft_skills]


def _computeAndStoreMatch(user_id: str, student_profile: dict, job_offer):
    if not job_offer.company:
        return

    required_skills = _requiredSkillsFor(job_offer)
    required_soft_skills = _requiredSoftSkillsFor(job_offer)

    distance_km, duration_min = geo.getOrComputeDistance(
        user_id,
        student_profile["indirizzo"],
        job_offer.company.address
    )

    deterministic = scorer.computeDeterministicScore(
        student_profile["skills"],
        student_profile["soft_skills"],
        distance_km,
        duration_min,
        required_skills,
        required_soft_skills
    )

    anonymized_payload = ai_refiner.buildAnonymizedPayload(
        deterministic,
        student_profile["skills"],
        student_profile["soft_skills"],
        job_offer.title,
        job_offer.description,
        required_skills,
        required_soft_skills,
        student_languages=student_profile.get("languages", []),
        student_experiences=student_profile.get("experiences", [])
    )

    refined = ai_refiner.refineScore(deterministic, anonymized_payload)

    database_helper.upsertMatch(
        user_id,
        job_offer.id,
        deterministic["score"],
        refined["ai_score"],
        refined["final_score"],
        refined["explanation"],
        refined["ai_status"]
    )


def recomputeMatchesForStudent(user_id: str):
    """Ricalcola il match dello studente con tutti gli annunci attivi.
    Chiamata quando lo studente aggiorna skill/soft skill/indirizzo."""
    student_profile = database_helper.getStudentMatchingProfile(user_id)

    if not student_profile or not student_profile.get("indirizzo"):
        return

    for job_offer in database_helper.getActiveJobOffers():
        try:
            _computeAndStoreMatch(user_id, student_profile, job_offer)
        except Exception as e:
            logger.exception(f"[matching.engine] match {user_id} <-> offer {job_offer.id} failed: {e}")


def recomputeMatchesForJobOffer(job_offer_id: int):
    """Ricalcola il match di tutti gli studenti (con profilo compilato) con un
    singolo annuncio. Chiamata quando l'azienda crea/modifica un annuncio."""
    job_offer = database_helper.getJobOfferById(job_offer_id)

    if not job_offer or not job_offer.attivo:
        return

    for user_id in database_helper.getStudentIdsWithAddress():
        student_profile = database_helper.getStudentMatchingProfile(user_id)

        if not student_profile:
            continue

        try:
            _computeAndStoreMatch(user_id, student_profile, job_offer)
        except Exception as e:
            logger.exception(f"[matching.engine] match {user_id} <-> offer {job_offer_id} failed: {e}")
