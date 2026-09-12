"""Risoluzione della distanza studente <-> sede azienda per il matching.

Riusa la stessa cache (`UserRoute`) e lo stesso geo-proxy già usati dalla
sezione "Percorsi" della dashboard studente (vedi app.py::routejson()).
"""

import os
import logging
import requests
from database import database_helper

logger = logging.getLogger(__name__)

DEFAULT_MODE = "driving-car"


def flattenAddress(raw_address: str | None) -> str | None:
    """Converte un indirizzo composito '££'-delimited in una stringa geocodificabile."""
    if not raw_address:
        return None

    parts = [p.strip() for p in raw_address.split("££") if p.strip()]

    return ", ".join(parts) if parts else None


def getOrComputeDistance(user_id: str, student_address: str | None, job_offer_address: str | None,
                          mode: str = DEFAULT_MODE) -> tuple[float | None, float | None]:
    """Ritorna (distance_km, duration_min), usando la cache UserRoute se disponibile
    o interrogando il geo-proxy (server.py) altrimenti. In caso di errore ritorna (None, None)."""
    start = flattenAddress(student_address)
    end = flattenAddress(job_offer_address)

    if not start or not end:
        return None, None

    cached = database_helper.getUserRouteByAddresses(user_id, start, end, mode)
    if cached and cached.distance_km is not None:
        return cached.distance_km, cached.duration_min

    api_url = os.getenv("API_URL", "http://127.0.0.1:5001")

    try:
        response = requests.get(
            f"{api_url}/routejson",
            params={"startaddress": start, "endaddress": end, "routemode": mode},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            logger.warning(f"[matching.geo] geo-proxy error for {start} -> {end}: {data['error']}")
            return None, None

        summary = data["features"][0]["properties"]["summary"]
        distance_km = summary["distance"] / 1000
        duration_min = summary["duration"] / 60
    except Exception as e:
        logger.warning(f"[matching.geo] failed to resolve distance {start} -> {end}: {e}")
        return None, None

    database_helper.addUserRoute(user_id, {
        "startaddress": start,
        "endaddress": end,
        "routemode": mode,
        "distance_km": distance_km,
        "duration_min": duration_min
    })

    return distance_km, duration_min
