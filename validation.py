"""Validazione e normalizzazione dell'input JSON delle route in `app.py`
"""

import re

MAX_SHORT_TEXT = 200
MAX_LONG_TEXT = 2000
MAX_LIST_ITEMS = 50

LANGUAGE_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
COLOR_MODES = ("dark", "light")

_URL_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
_HTTP_URL = re.compile(r"^https?://[^\s\"'<>]+$", re.IGNORECASE)

def cleanText(value, field: str, max_length: int = MAX_SHORT_TEXT, required: bool = False) -> str | None:
    """Restituisce il testo ripulito (None se vuoto e non obbligatorio)."""
    if value is None:
        text = ""
    elif isinstance(value, (str, int, float)) and not isinstance(value, bool):
        text = str(value).strip()
    else:
        raise ValueError(f"Il campo '{field}' non è valido")

    if not text:
        if required:
            raise ValueError(f"Il campo '{field}' è obbligatorio")

        return None

    if len(text) > max_length:
        raise ValueError(f"Il campo '{field}' non può superare {max_length} caratteri")

    return text

def normalizeWebsite(value, field: str = "sito web") -> str | None:
    """Accetta solo URL http(s); aggiunge `https://` se manca lo schema."""
    text = cleanText(value, field)

    if text is None:
        return None

    if _URL_SCHEME.match(text) and not text.lower().startswith(("http://", "https://")):
        raise ValueError(f"Il campo '{field}' deve essere un indirizzo http o https")

    if not _URL_SCHEME.match(text):
        text = f"https://{text}"

    if not _HTTP_URL.match(text):
        raise ValueError(f"Il campo '{field}' non è un indirizzo valido")

    return text

def _requireList(value, field: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"Il campo '{field}' deve essere una lista")

    if len(value) > MAX_LIST_ITEMS:
        raise ValueError(f"Il campo '{field}' non può contenere più di {MAX_LIST_ITEMS} elementi")

    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"Il campo '{field}' contiene un elemento non valido")

    return value

def _level(value, field: str) -> int:
    try:
        level = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Il livello di '{field}' non è valido")

    if level not in (1, 2, 3):
        raise ValueError(f"Il livello di '{field}' deve essere compreso tra 1 e 3")

    return level

def normalizeSkills(items, field: str = "skills", level_key: str = "livello") -> list[dict]:
    """Ripulisce le skill; i duplicati (senza distinzione di maiuscole) tengono il livello più alto."""
    by_name: dict[str, dict] = {}

    for item in _requireList(items, field):
        name = cleanText(item.get("name"), "nome skill", required=True)
        level = _level(item.get(level_key), name)
        key = name.casefold()

        if key not in by_name or by_name[key][level_key] < level:
            by_name[key] = {"name": name, level_key: level}

    return list(by_name.values())

def normalizeSoftSkills(items, field: str = "soft_skills") -> list[dict]:
    by_label: dict[str, dict] = {}

    for item in _requireList(items, field):
        label = cleanText(item.get("label"), "soft skill", required=True)
        icon = cleanText(item.get("icon"), "icona soft skill", max_length=50) or "i-star"

        by_label.setdefault(label.casefold(), {"label": label, "icon": icon})

    return list(by_label.values())

def normalizeLanguages(items) -> list[dict]:
    by_name: dict[str, dict] = {}

    for item in _requireList(items, "languages"):
        name = cleanText(item.get("name"), "lingua")

        if name is None:
            continue

        level = cleanText(item.get("level"), "livello lingua", max_length=2) or "A1"

        if level not in LANGUAGE_LEVELS:
            raise ValueError(f"Il livello della lingua '{name}' non è valido")

        by_name.setdefault(name.casefold(), {
            "name": name,
            "level": level,
            "certification": cleanText(item.get("certification"), "certificazione")
        })

    return list(by_name.values())

def normalizeExperiences(items) -> list[dict]:
    result = []

    for item in _requireList(items, "experiences"):
        title = cleanText(item.get("title"), "titolo esperienza")

        if title is None:
            continue

        labels = item.get("labels") or []

        if not isinstance(labels, list) or len(labels) > MAX_LIST_ITEMS:
            raise ValueError("Le etichette dell'esperienza non sono valide")

        link = cleanText(item.get("link"), "link esperienza", max_length=500)

        result.append({
            "title": title,
            "description": cleanText(item.get("description"), "descrizione esperienza", MAX_LONG_TEXT),
            "link": normalizeWebsite(link, "link esperienza") if link else None,
            "labels": [
                label for label in
                (cleanText(label, "etichetta esperienza", 60) for label in labels)
                if label
            ]
        })

    return result

def normalizeProfile(data: dict) -> dict:
    """Valida i campi liste/preferenze del profilo studente. Gli altri campi
    semplici sono ripuliti nei limiti di lunghezza, senza cambiarne il formato."""
    if not isinstance(data, dict):
        raise ValueError("Dati non validi")

    profile = dict(data)

    for field in ("name", "surname", "sesso", "comune_nascita", "telefono",
                  "indirizzo_studio", "classe", "indirizzo"):
        if field in profile:
            profile[field] = cleanText(profile[field], field) or ""

    if "skills" in profile:
        profile["skills"] = normalizeSkills(profile["skills"])

    if "soft_skills" in profile:
        profile["soft_skills"] = normalizeSoftSkills(profile["soft_skills"])

    if "languages" in profile:
        profile["languages"] = normalizeLanguages(profile["languages"])

    if "experiences" in profile:
        profile["experiences"] = normalizeExperiences(profile["experiences"])

    preferences = profile.get("preferences")

    if preferences is not None:
        if not isinstance(preferences, dict):
            raise ValueError("Preferenze non valide")

        if preferences.get("color_mode") not in (None, *COLOR_MODES):
            raise ValueError("color_mode non valido")

    return profile

def normalizeJobOffer(data: dict, require_title: bool) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Dati non validi")

    offer = dict(data)

    if "title" in offer or require_title:
        offer["title"] = cleanText(offer.get("title"), "titolo", required=True)

    if "description" in offer:
        offer["description"] = cleanText(offer["description"], "descrizione", MAX_LONG_TEXT)

    if "required_skills" in offer:
        offer["required_skills"] = normalizeSkills(
            offer["required_skills"], "required_skills", level_key="livello_min"
        )

    if "required_soft_skills" in offer:
        offer["required_soft_skills"] = normalizeSoftSkills(offer["required_soft_skills"], "required_soft_skills")

    return offer

def normalizeCompanyProfile(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Dati non validi")

    profile = dict(data)

    if "name" in profile:
        profile["name"] = cleanText(profile["name"], "nome azienda", required=True)

    for field in ("address", "settore", "telefono"):
        if field in profile:
            profile[field] = cleanText(profile[field], field)

    if "descrizione" in profile:
        profile["descrizione"] = cleanText(profile["descrizione"], "descrizione", MAX_LONG_TEXT)

    if "sito_web" in profile:
        profile["sito_web"] = normalizeWebsite(profile["sito_web"])

    if profile.get("color_mode") not in (None, *COLOR_MODES):
        raise ValueError("color_mode non valido")

    return profile
