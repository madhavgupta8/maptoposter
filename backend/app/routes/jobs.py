import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.config import Config
from app.routes.themes import get_theme_keys
from app.services import storage
from app.services.invite import verify as verify_invite
from app.services.supabase_client import rest_request

bp = Blueprint("jobs", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_RATIOS = {"3:4", "4:5"}


def _clamp_radius(value) -> int:
    try:
        radius = int(value)
    except (TypeError, ValueError):
        radius = 29000
    return max(1000, min(radius, 100000))


def _parse_bool(value, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _select_columns() -> str:
    return ",".join(
        [
            "id",
            "status",
            "created_at",
            "started_at",
            "completed_at",
            "error_message",
            "storage_path",
            "signed_url_expires_at",
            "city",
            "country",
            "theme",
        ]
    )


def _job_response(job: dict, signed_url: str | None = None) -> dict:
    return {
        "job_id": job["id"],
        "status": job["status"],
        "created_at": job.get("created_at"),
        "error_message": job.get("error_message"),
        "signed_url": signed_url,
        "signed_url_expires_at": job.get("signed_url_expires_at"),
    }


@bp.post("/jobs")
def create_job():
    data = request.get_json(silent=True) or {}

    invite_code = (data.get("invite_code") or "").strip()
    if not verify_invite(invite_code):
        return jsonify({"error": "Invalid invite code."}), 401

    city = (data.get("city") or "").strip()
    country = (data.get("country") or "").strip()
    email = (data.get("email") or "").strip()
    theme = (data.get("theme") or "feature_based").strip()
    ratio = (data.get("ratio") or "3:4").strip()
    radius = _clamp_radius(data.get("radius"))
    no_small_roads = _parse_bool(data.get("no_small_roads"), True)

    if not city:
        return jsonify({"error": "City is required."}), 400
    if not country:
        return jsonify({"error": "Country is required."}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "A valid email is required."}), 400
    if theme not in get_theme_keys():
        return jsonify({"error": "Unknown theme."}), 400
    if ratio not in ALLOWED_RATIOS:
        return jsonify({"error": "Invalid ratio."}), 400

    payload = {
        "city": city,
        "country": country,
        "email": email,
        "theme": theme,
        "ratio": ratio,
        "radius": radius,
        "no_small_roads": no_small_roads,
        "status": "queued",
    }
    response = rest_request(
        "POST",
        "jobs",
        json=payload,
        headers={"Prefer": "return=representation"},
    )
    row = response.json()[0]
    return jsonify({"job_id": row["id"], "status": row["status"]}), 202


@bp.get("/jobs/<job_id>")
def get_job(job_id: str):
    response = rest_request(
        "GET",
        "jobs",
        params={"id": f"eq.{job_id}", "select": _select_columns()},
    )
    rows = response.json()
    if not rows:
        return jsonify({"error": "Job not found."}), 404

    job = rows[0]
    signed_url = None
    expires_at_raw = job.get("signed_url_expires_at")
    if job["status"] == "done" and job.get("storage_path"):
        needs_refresh = True
        if expires_at_raw:
            try:
                expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
                needs_refresh = expires_at <= datetime.now(timezone.utc)
            except ValueError:
                needs_refresh = True
        if needs_refresh:
            signed_url, expires_at = storage.create_signed_url(
                job["storage_path"], Config.SIGNED_URL_TTL_SECONDS
            )
            patch_payload = {
                "signed_url_expires_at": expires_at.isoformat(),
            }
            rest_request(
                "PATCH",
                "jobs",
                params={"id": f"eq.{job_id}"},
                json=patch_payload,
            )
            job["signed_url_expires_at"] = expires_at.isoformat()
        else:
            signed_url, _ = storage.create_signed_url(
                job["storage_path"], Config.SIGNED_URL_TTL_SECONDS
            )

    return jsonify(_job_response(job, signed_url=signed_url))
