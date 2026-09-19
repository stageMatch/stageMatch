"""Calcolo del punteggio di compatibilità deterministico studente <-> annuncio di stage.

Nessun accesso a DB o rete: funzioni pure, facilmente testabili in isolamento.
"""

import unicodedata

SKILL_WEIGHT = 0.5
SOFT_SKILL_WEIGHT = 0.2
DISTANCE_WEIGHT = 0.3

# Senza requisiti nell'annuncio non c'è nulla da confrontare: valore neutro (metà
# del massimo), invece di un punteggio alto regalato senza dati.
NEUTRAL_SCORE_NO_REQUIREMENTS = 0.5
# Distanza sconosciuta (geo-proxy non disponibile): penalizzata più di un tragitto medio noto.
UNKNOWN_DISTANCE_SCORE = 0.3
MAX_ACCEPTABLE_DURATION_MIN = 60

def _normalize(text) -> str:
    """Minuscolo, senza accenti né spazi ai bordi, per confrontare i nomi delle skill."""
    decomposed = unicodedata.normalize("NFKD", str(text or "").strip().casefold())

    return "".join(c for c in decomposed if not unicodedata.combining(c))

def _skillScore(student_skills: list[dict], required_skills: list[dict]) -> float:
    if not required_skills:
        return NEUTRAL_SCORE_NO_REQUIREMENTS

    student_by_name: dict[str, int] = {}
    for s in student_skills:
        key = _normalize(s.get("name"))
        student_by_name[key] = max(student_by_name.get(key, 0), s.get("livello") or 0)

    scores = []
    for req in required_skills:
        livello_studente = student_by_name.get(_normalize(req.get("name")))
        livello_min = req.get("livello_min") or 1

        if not livello_studente:
            scores.append(0.0)
        else:
            scores.append(min(1.0, livello_studente / livello_min))

    return sum(scores) / len(scores)

def _softSkillScore(student_soft_skills: list[dict], required_soft_skills: list[dict]) -> float:
    if not required_soft_skills:
        return NEUTRAL_SCORE_NO_REQUIREMENTS

    student_labels = {_normalize(s.get("label")) for s in student_soft_skills}
    required_labels = {_normalize(s.get("label")) for s in required_soft_skills}

    matched = student_labels & required_labels

    return len(matched) / len(required_labels)

def _distanceScore(duration_min: float | None) -> float:
    if duration_min is None:
        return UNKNOWN_DISTANCE_SCORE

    return max(0.0, 1 - (duration_min / MAX_ACCEPTABLE_DURATION_MIN))

def computeDeterministicScore(
    student_skills: list[dict],
    student_soft_skills: list[dict],
    distance_km: float | None,
    duration_min: float | None,
    required_skills: list[dict],
    required_soft_skills: list[dict]
) -> dict:
    """Ritorna un punteggio 0-100 e i sotto-punteggi che lo compongono."""
    skill_score = _skillScore(student_skills, required_skills)
    soft_score = _softSkillScore(student_soft_skills, required_soft_skills)
    distance_score = _distanceScore(duration_min)

    weighted = (
        skill_score * SKILL_WEIGHT +
        soft_score * SOFT_SKILL_WEIGHT +
        distance_score * DISTANCE_WEIGHT
    )

    return {
        "score": round(weighted * 100, 1),
        "skill_score": round(skill_score * 100, 1),
        "soft_score": round(soft_score * 100, 1),
        "distance_score": round(distance_score * 100, 1),
        "distance_km": distance_km,
        "duration_min": duration_min,
        "has_skill_requirements": bool(required_skills),
        "has_soft_requirements": bool(required_soft_skills)
    }
