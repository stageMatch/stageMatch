"""Rifinitura del punteggio deterministico tramite un modello AI (Anthropic),
su un payload anonimizzato (nessun dato identificativo dello studente).

Se l'AI è disabilitata, mancante di API key, sotto la soglia minima di rilevanza,
o la chiamata fallisce per qualunque motivo, si ritorna sempre il punteggio
deterministico come fallback: il matching resta funzionante anche senza AI.
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

MATCH_AI_MIN_SCORE = 40
AI_TIMEOUT_SECONDS = 10


def _isEnabled() -> bool:
    enabled = os.getenv("ANTHROPIC_MATCHING_ENABLED", "True").lower() == "true"

    return enabled and bool(os.getenv("ANTHROPIC_API_KEY"))


def buildAnonymizedPayload(deterministic_result: dict, student_skills: list[dict],
                            student_soft_skills: list[dict], offer_title: str,
                            offer_description: str | None, required_skills: list[dict],
                            required_soft_skills: list[dict],
                            student_languages: list[dict] | None = None,
                            student_experiences: list[dict] | None = None) -> dict:
    """Costruisce il payload da inviare all'AI. Nessun nome/email/googleId/indirizzo/foto:
    solo skill, soft skill, distanza/durata già calcolata e testo dell'annuncio.

    Lingue ed esperienze/progetti dello studente vengono passate solo qui, come
    contesto extra per la rifinitura AI: non esiste ancora, lato JobOffer/azienda,
    un campo "lingue richieste"/"esperienza richiesta" con cui confrontarle
    oggettivamente, quindi non entrano nello scoring deterministico (scorer.py).
    Il link delle esperienze non viene mai incluso (già escluso a monte da
    database_helper.getStudentMatchingProfile)."""
    return {
        "punteggio_deterministico": deterministic_result["score"],
        "distanza_km": deterministic_result["distance_km"],
        "durata_min": deterministic_result["duration_min"],
        "skill_studente": student_skills,
        "soft_skill_studente": student_soft_skills,
        "lingue_studente": student_languages or [],
        "esperienze_studente": student_experiences or [],
        "annuncio": {
            "titolo": offer_title,
            "descrizione": offer_description,
            "skill_richieste": required_skills,
            "soft_skill_richieste": required_soft_skills
        }
    }


def _fallbackResult(deterministic_score: float, ai_status: str) -> dict:
    return {
        "final_score": deterministic_score,
        "ai_score": None,
        "explanation": None,
        "ai_status": ai_status
    }


def refineScore(deterministic_result: dict, anonymized_payload: dict) -> dict:
    if not _isEnabled():
        return _fallbackResult(deterministic_result["score"], "disabled")

    if deterministic_result["score"] < MATCH_AI_MIN_SCORE:
        return _fallbackResult(deterministic_result["score"], "disabled")

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

        prompt = (
            "Sei un assistente che valuta la compatibilità tra il profilo anonimizzato di uno "
            "studente e un annuncio di stage aziendale. Ricevi solo dati anonimi (skill, soft "
            "skill, distanza di spostamento, titolo e descrizione dell'annuncio) e un punteggio "
            "deterministico di partenza (0-100) già calcolato sugli stessi criteri.\n\n"
            "Rispondi ESCLUSIVAMENTE con un oggetto JSON valido, senza altro testo, in questa forma:\n"
            '{"score": <numero 0-100>, "explanation": "<spiegazione breve in italiano, massimo due frasi>"}\n\n'
            f"Dati:\n{json.dumps(anonymized_payload, ensure_ascii=False)}"
        )

        message = client.messages.create(
            model=model,
            max_tokens=300,
            timeout=AI_TIMEOUT_SECONDS,
            messages=[{"role": "user", "content": prompt}]
        )

        text = message.content[0].text.strip()
        parsed = json.loads(text[text.index("{"):text.rindex("}") + 1])

        ai_score = max(0.0, min(100.0, float(parsed["score"])))

        return {
            "final_score": ai_score,
            "ai_score": ai_score,
            "explanation": parsed.get("explanation"),
            "ai_status": "ok"
        }
    except Exception as e:
        logger.warning(f"[matching.ai_refiner] rifinitura AI fallita, uso il punteggio deterministico: {e}")

        return _fallbackResult(deterministic_result["score"], "fallback")
