"""Rifinitura del punteggio deterministico tramite un modello AI (Anthropic o DeepSeek,
a seconda di MATCH_AI_PROVIDER), su un payload anonimizzato (nessun dato identificativo
dello studente).

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

SYSTEM_PROMPT = (
    "Sei un assistente che valuta la compatibilità tra il profilo anonimizzato di uno "
    "studente e un annuncio di stage aziendale. Ricevi solo dati anonimi: skill, soft "
    "skill, lingue parlate, esperienze/progetti pregressi, distanza di spostamento e "
    "durata del tragitto, titolo e descrizione dell'annuncio, oltre a un punteggio "
    "deterministico di partenza (0-100) già calcolato su skill/soft skill/distanza. "
    "Lingue ed esperienze non entrano nel punteggio deterministico: usale come contesto "
    "aggiuntivo per affinare la valutazione.\n\n"
    "Nella spiegazione, cita SEMPRE 1-2 fattori concreti e specifici che hanno determinato "
    "la valutazione, scegliendoli tra: skill richieste effettivamente possedute o mancanti "
    "(nominale, es. 'possiedi Python al livello richiesto ma manca SQL'), un'esperienza o "
    "lingua pertinente all'annuncio, oppure la distanza/durata del tragitto se rilevante "
    "(es. 'a soli 8 minuti' o 'un tragitto di oltre un'ora'). Evita frasi generiche e "
    "intercambiabili come 'buona corrispondenza complessiva' o 'profilo adatto al ruolo' "
    "senza riferimenti concreti ai dati ricevuti: due spiegazioni per annunci diversi non "
    "devono mai poter essere scambiate tra loro.\n\n"
    "Rispondi ESCLUSIVAMENTE con un oggetto JSON valido, senza altro testo, in questa forma:\n"
    '{"score": <numero 0-100>, "explanation": "<spiegazione breve e specifica in italiano>"}'
)

def _isEnabled() -> bool:
    enabled = os.getenv("ANTHROPIC_MATCHING_ENABLED", "True").lower() == "true"

    if not enabled:
        return False

    if os.getenv("MATCH_AI_PROVIDER", "anthropic").lower() == "deepseek":
        return bool(os.getenv("DEEPSEEK_API_KEY"))

    return bool(os.getenv("ANTHROPIC_API_KEY"))

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
        client, model = _buildClient()

        message = client.messages.create(
            model=model,
            max_tokens=32000,
            timeout=AI_TIMEOUT_SECONDS,
            thinking={"type": "disabled"},
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Dati:\n{json.dumps(anonymized_payload, ensure_ascii=False)}"
            }]
        )

        text_block = next((b for b in message.content if getattr(b, "type", None) == "text"), None)

        if text_block is None:
            raise ValueError("risposta AI priva di un blocco di testo (solo thinking?)")

        text = text_block.text.strip()
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

def _buildClient():
    """DeepSeek espone un endpoint compatibile con la Messages API di Anthropic
    (https://api-docs.deepseek.com/guides/anthropic_api): stesso SDK, cambiano solo
    base_url/api_key/model."""
    import anthropic

    if os.getenv("MATCH_AI_PROVIDER", "anthropic").lower() == "deepseek":
        client = anthropic.Anthropic(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/anthropic"
        )
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
    else:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

    return client, model
