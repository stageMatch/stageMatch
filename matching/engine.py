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

def _skillFitPhrase(score: float) -> str:
    if score >= 85:
        return "corrispondono pienamente ai requisiti richiesti"
    if score >= 60:
        return "coprono buona parte dei requisiti richiesti"
    if score >= 30:
        return "coprono solo in parte i requisiti richiesti"
    return "coprono solo una minima parte dei requisiti richiesti"

def _softSkillFitPhrase(score: float) -> str:
    if score >= 85:
        return "sono pienamente in linea con quanto cercato"
    if score >= 60:
        return "sono in buona parte in linea con quanto cercato"
    if score >= 30:
        return "sono solo in parte in linea con quanto cercato"
    return "si discostano da quanto cercato"

def _commutePhrase(duration_min: float) -> str:
    if duration_min <= 15:
        return "un tragitto molto breve"
    if duration_min <= 30:
        return "un tragitto comodo"
    if duration_min <= 60:
        return "un tragitto di media durata"
    return "un tragitto piuttosto lungo"

def _buildDeterministicExplanation(deterministic: dict) -> str:
    """Spiegazione testuale generata dai sotto-punteggi deterministici, usata quando
    l'AI non è disponibile/fallisce: varia da annuncio ad annuncio (a differenza di
    una frase fissa) perché riflette i dati reali del singolo match."""
    skill_score = deterministic["skill_score"]
    soft_score = deterministic["soft_score"]
    distance_km = deterministic["distance_km"]
    duration_min = deterministic["duration_min"]

    frase = (
        f"Le tue competenze tecniche {_skillFitPhrase(skill_score)} ({skill_score:.0f}%), "
        f"mentre le tue soft skill {_softSkillFitPhrase(soft_score)} ({soft_score:.0f}%)."
    )

    if distance_km is not None and duration_min is not None:
        frase += (
            f" Lo stage dista {distance_km:.1f} km, {_commutePhrase(duration_min)} "
            f"di circa {round(duration_min)} minuti."
        )
    else:
        frase += " La distanza dallo stage non è al momento disponibile."

    return frase

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
    explanation = refined["explanation"] or _buildDeterministicExplanation(deterministic)

    database_helper.upsertMatch(
        user_id,
        job_offer.id,
        deterministic["score"],
        refined["ai_score"],
        refined["final_score"],
        explanation,
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
