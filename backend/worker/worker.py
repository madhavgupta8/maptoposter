import logging
import os
import time
import traceback
from datetime import datetime, timezone

from app.config import Config
from app.services.poster import render_poster
from app.services.resend_client import send_completion_email
from app.services.storage import create_signed_url, upload_poster
from app.services.supabase_client import rest_request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 5


def _slugify(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _claim_next_job():
    response = rest_request("POST", "rpc/claim_next_job", json={})
    rows = response.json()
    return rows[0] if rows else None


def _update_job(job_id: str, payload: dict) -> None:
    rest_request("PATCH", "jobs", params={"id": f"eq.{job_id}"}, json=payload)


def _truncate_error(message: str) -> str:
    return message[-2048:]


def run_forever() -> None:
    tmp_dir = os.path.join(Config.MAPTOPOSTER_DIR, "posters", "_worker_tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    while True:
        job = None
        try:
            job = _claim_next_job()
            if not job:
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            job_id = job["id"]
            storage_path = (
                f"{_slugify(job['country'])}/"
                f"{_slugify(job['city'])}/"
                f"{job['theme']}/"
                f"{job_id}.png"
            )
            local_path = os.path.join(tmp_dir, f"{job_id}.png")

            logger.info("Processing job %s for %s, %s", job_id, job["city"], job["country"])
            render_poster(
                city=job["city"],
                country=job["country"],
                theme=job["theme"],
                ratio=job["ratio"],
                radius=job["radius"],
                no_small_roads=job["no_small_roads"],
                output_path=local_path,
            )

            upload_poster(local_path, storage_path)
            signed_url, expires_at = create_signed_url(storage_path, Config.SIGNED_URL_TTL_SECONDS)
            with open(local_path, "rb") as handle:
                png_bytes = handle.read()
            completed_at = datetime.now(timezone.utc)
            send_completion_email(
                to_email=job["email"],
                city=job["city"],
                country=job["country"],
                theme=job["theme"],
                signed_url=signed_url,
                png_bytes=png_bytes,
                generated_at=completed_at,
            )
            _update_job(
                job_id,
                {
                    "status": "done",
                    "storage_path": storage_path,
                    "signed_url_expires_at": expires_at.isoformat(),
                    "completed_at": completed_at.isoformat(),
                    "error_message": None,
                },
            )
            logger.info("Completed job %s", job_id)
            if os.path.exists(local_path):
                os.remove(local_path)
        except Exception as exc:
            logger.exception("Worker failed while processing job")
            if job:
                error_blob = f"{exc.__class__.__name__}: {exc}\n{traceback.format_exc()}"
                _update_job(
                    job["id"],
                    {
                        "status": "error",
                        "error_message": _truncate_error(error_blob),
                    },
                )
            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_forever()
