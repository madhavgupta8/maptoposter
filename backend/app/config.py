import os
from pathlib import Path

# Default: maptoposter/ sits next to this file's parent (i.e. backend/maptoposter)
_DEFAULT_MAPTOPOSTER_DIR = str(Path(__file__).resolve().parent.parent / "maptoposter")


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer") from exc


def _csv(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    items = []
    for part in raw.split(","):
        origin = part.strip().rstrip("/")
        if origin:
            items.append(origin)
    return items


class Config:
    SUPABASE_URL = _required("SUPABASE_URL").rstrip("/")
    SUPABASE_SERVICE_KEY = _required("SUPABASE_SERVICE_KEY")
    SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "map-posters").strip() or "map-posters"
    RESEND_API_KEY = _required("RESEND_API_KEY")
    RESEND_FROM_EMAIL = _required("RESEND_FROM_EMAIL")
    INVITE_CODE_HASH = _required("INVITE_CODE_HASH")
    SIGNED_URL_TTL_SECONDS = _int("SIGNED_URL_TTL_SECONDS", 604800)
    CORS_ORIGINS = _csv("CORS_ORIGINS", "https://guptamadhav.vercel.app,http://localhost:5173")
    MAPTOPOSTER_DIR = os.environ.get("MAPTOPOSTER_DIR", "").strip() or _DEFAULT_MAPTOPOSTER_DIR
