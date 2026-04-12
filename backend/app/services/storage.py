from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import Config
from app.services.supabase_client import storage_request


def upload_poster(local_path: str, storage_path: str) -> None:
    path = Path(local_path)
    with path.open("rb") as handle:
        storage_request(
            "POST",
            f"object/{Config.SUPABASE_BUCKET}/{storage_path}",
            data=handle.read(),
            headers={
                "Content-Type": "image/png",
                "x-upsert": "true",
            },
        )


def create_signed_url(storage_path: str, ttl_seconds: int | None = None) -> tuple[str, datetime]:
    ttl = ttl_seconds or Config.SIGNED_URL_TTL_SECONDS
    response = storage_request(
        "POST",
        f"object/sign/{Config.SUPABASE_BUCKET}/{storage_path}",
        json={"expiresIn": ttl},
        headers={"Content-Type": "application/json"},
    )
    payload = response.json()
    signed_path = payload.get("signedURL") or payload.get("signedUrl")
    if not signed_path:
        raise RuntimeError("Supabase did not return a signed URL")
    if signed_path.startswith("http://") or signed_path.startswith("https://"):
        signed_url = signed_path
    else:
        signed_url = f"{Config.SUPABASE_URL}/storage/v1{signed_path}"
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
    return signed_url, expires_at
