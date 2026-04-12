import requests

from app.config import Config

_session = None


def get_session() -> requests.Session:
    global _session
    if _session is None:
        session = requests.Session()
        session.headers.update(
            {
                "apikey": Config.SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {Config.SUPABASE_SERVICE_KEY}",
            }
        )
        _session = session
    return _session


def rest_request(method: str, path: str, **kwargs) -> requests.Response:
    session = get_session()
    headers = kwargs.pop("headers", {})
    response = session.request(
        method,
        f"{Config.SUPABASE_URL}/rest/v1/{path.lstrip('/')}",
        headers=headers,
        timeout=30,
        **kwargs,
    )
    response.raise_for_status()
    return response


def storage_request(method: str, path: str, **kwargs) -> requests.Response:
    session = get_session()
    headers = kwargs.pop("headers", {})
    response = session.request(
        method,
        f"{Config.SUPABASE_URL}/storage/v1/{path.lstrip('/')}",
        headers=headers,
        timeout=60,
        **kwargs,
    )
    response.raise_for_status()
    return response
