"""Calcolo del punteggio di compatibilità deterministico studente <-> annuncio di stage.

Nessun accesso a DB o rete: funzioni pure, facilmente testabili in isolamento.
"""

SKILL_WEIGHT = 0.5
SOFT_SKILL_WEIGHT = 0.2
DISTANCE_WEIGHT = 0.3

NEUTRAL_SCORE_NO_REQUIREMENTS = 0.7
MAX_ACCEPTABLE_DURATION_MIN = 60


def _skillScore(student_skills: list[dict], required_skills: list[dict]) -> float:
    if not required_skills:
        return NEUTRAL_SCORE_NO_REQUIREMENTS

    student_by_name = {s["name"].strip().lower(): s["livello"] for s in student_skills}

    scores = []
    for req in required_skills:
        livello_studente = student_by_name.get(req["name"].strip().lower())

        if livello_studente is None:
            scores.append(0.0)
        else:
            scores.append(min(1.0, livello_studente / req["livello_min"]))

    return sum(scores) / len(scores)


def _softSkillScore(student_soft_skills: list[dict], required_soft_skills: list[dict]) -> float:
    if not required_soft_skills:
        return NEUTRAL_SCORE_NO_REQUIREMENTS

    student_labels = {s["label"].strip().lower() for s in student_soft_skills}
    required_labels = {s["label"].strip().lower() for s in required_soft_skills}

    matched = student_labels & required_labels

    return len(matched) / len(required_labels)


def _distanceScore(duration_min: float | None) -> float:
    if duration_min is None:
        return NEUTRAL_SCORE_NO_REQUIREMENTS

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
        "duration_min": duration_min
    }
