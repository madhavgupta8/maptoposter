import hashlib
import hmac
import re

from app.config import Config

HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")


def hash_code(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def _normalized_expected_hash() -> str:
    raw = Config.INVITE_CODE_HASH.strip().lower()
    if HEX_64_RE.fullmatch(raw):
        return raw
    return hash_code(Config.INVITE_CODE_HASH)


def verify(plain: str) -> bool:
    if not plain:
        return False
    return hmac.compare_digest(hash_code(plain), _normalized_expected_hash())


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m app.services.invite <invite-code>")
    print(hash_code(sys.argv[1]))
