import json
import urllib.parse
import urllib.request

from flask import Blueprint, jsonify, request

bp = Blueprint("geocode", __name__)


@bp.get("/geocode")
def geocode():
    city = request.args.get("city", "").strip()
    country = request.args.get("country", "").strip()
    if not city or not country:
        return jsonify([])

    url = (
        "https://nominatim.openstreetmap.org/search"
        f"?city={urllib.parse.quote(city)}"
        f"&country={urllib.parse.quote(country)}"
        "&format=json&limit=1"
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "MapPosterGenerator/1.0",
            "Accept-Language": "en",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return jsonify(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
