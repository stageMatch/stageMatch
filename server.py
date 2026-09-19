import os
from flask import Flask, request, jsonify
import requests
import aiohttp
import urllib.parse
import asyncio
from dotenv import load_dotenv

load_dotenv()

ors_api_key = os.getenv("ORS_API_KEY")
nominatim_user_agent = os.getenv("NOMINATIM_USER_AGENT", "stageMatch/1.0 (geo-proxy interno)")

REQUEST_TIMEOUT_SECONDS = 15
VALID_ROUTE_MODES = ("driving-car", "foot-walking", "cycling-regular")

app = Flask(__name__)

@app.route('/routejson')
def routejson():
    start_address = request.args.get("startaddress")
    end_address = request.args.get("endaddress")
    route_mode = request.args.get("routemode")

    if (start_address == None or end_address == None):
        return jsonify({
            "error": "Mancano gli indirizzi di partenza o di arrivo."
        }), 400

    if route_mode not in VALID_ROUTE_MODES:
        return jsonify({"error": "Mezzo di trasporto non valido."}), 400

    if not ors_api_key:
        return jsonify({"error": "ORS_API_KEY non configurata."}), 503

    try:
        coords = asyncio.run(getCoordinates(start_address, end_address))
    except Exception:
        app.logger.warning("geocoding fallito", exc_info=True)

        return jsonify({
            "error": "Non è stato possibile ricavare le coordinate geografiche dagli indirizzi forniti"
        }), 422

    openrouteservice_url = f"https://api.openrouteservice.org/v2/directions/{route_mode}/geojson"

    request_body = {
        "coordinates": [
            [coords["Start"]["Lon"], coords["Start"]["Lat"]],
            [coords["End"]["Lon"], coords["End"]["Lat"]]
        ]
    }

    headers = {
        "Authorization": ors_api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            openrouteservice_url, json=request_body, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()

        return response.json()
    except (requests.exceptions.RequestException, ValueError) as error:
        app.logger.warning(f"richiesta a OpenRouteService fallita: {error}")

        return jsonify({
            "error": "Errore nella richiesta al servizio di routing",
        }), 502

@app.route("/photon")
def photon():
    q = request.args.get("q", "")

    if not q.strip():
        return jsonify({"error": "Parametro q obbligatorio"}), 400

    try:
        params = {
            "q": q,
            "limit": max(1, min(int(request.args.get("limit", "5")), 10)),
            "lang": request.args.get("lang", "en")[:5]
        }

        if request.args.get("lat") and request.args.get("lon"):
            params["lat"] = float(request.args["lat"])
            params["lon"] = float(request.args["lon"])
    except ValueError:
        return jsonify({"error": "Parametri non validi"}), 400

    try:
        response = requests.get(
            "https://photon.komoot.io/api/",
            params=params,
            headers={"User-Agent": nominatim_user_agent},
            timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()

        return jsonify(response.json())
    except (requests.exceptions.RequestException, ValueError) as e:
        app.logger.warning(f"richiesta a Photon fallita: {e}")

        return jsonify({"error": "Servizio di ricerca indirizzi non disponibile"}), 502

async def getCoordinates(address_start, address_end):
    if not address_start or not address_end:
        raise ValueError("Inserire gli indirizzi di partenza e arrivo")

    url_start = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(address_start)}&format=json&limit=1"
    url_end = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(address_end)}&format=json&limit=1"

    coords_start = []
    coords_end = []

    async with aiohttp.ClientSession(
        headers={"User-Agent": nominatim_user_agent},
        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    ) as session:
        # --- Richiesta indirizzo di partenza ---
        try:
            async with session.get(url_start) as response:
                if not response.ok:
                    raise Exception(f"HTTP Error: {response.status}")

                data = await response.json()

                if len(data) > 0:
                    coords_start.append(data[0]["lat"])
                    coords_start.append(data[0]["lon"])
                else:
                    raise ValueError("Indirizzo di partenza non trovato")
        except Exception as error:
            raise RuntimeError(
                "Errore nella richiesta conversione indirizzo partenza"
            ) from error

        await asyncio.sleep(1)

        # --- Richiesta indirizzo di arrivo ---
        try:
            async with session.get(url_end) as response:
                if not response.ok:
                    raise Exception(f"HTTP Error: {response.status}")

                data = await response.json()

                if len(data) > 0:
                    coords_end.append(data[0]["lat"])
                    coords_end.append(data[0]["lon"])
                else:
                    raise ValueError("Indirizzo di arrivo non trovato")
        except Exception as error:
            raise RuntimeError(
                "Errore nella richiesta conversione indirizzo arrivo"
            ) from error

    coords = {
        "Start": {
            "Lat": coords_start[0],
            "Lon": coords_start[1]
        },
        "End": {
            "Lat": coords_end[0],
            "Lon": coords_end[1]
        }
    }

    return coords

if __name__ == '__main__':
    app.run(
        os.getenv("HOST", "127.0.0.1"),
        int(os.getenv("PORT_API", 5001)),
        debug=os.getenv("DEBUG", "False").lower() == "true"
    )
