"""
Encryption helpers for sensitive billing fields (payment provider tokens).

Uses Fernet (symmetric AES) when the ``cryptography`` package is installed
and falls back to Django's signed serialization otherwise. Keys are derived
from ``settings.SECRET_KEY`` so no extra configuration is required.
"""
import base64
import hashlib

from django.conf import settings
from django.core import signing

try:  # pragma: no cover - environment dependent
    from cryptography.fernet import Fernet, InvalidToken

    _fernet = Fernet(
        base64.urlsafe_b64encode(
            hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        )
    )
    HAS_FERNET = True
except ImportError:  # pragma: no cover - environment dependent
    HAS_FERNET = False


def encrypt_value(value) -> str:
    """Encrypt a JSON-serializable value into a stored string."""
    if value is None:
        return None
    payload = signing.dumps(value, compress=True)
    if HAS_FERNET:
        return _fernet.encrypt(payload.encode("utf-8")).decode("ascii")
    return f"sig:{payload}"


def decrypt_value(token) -> object:
    """Decrypt a value produced by :func:`encrypt_value`."""
    if token is None:
        return None
    if HAS_FERNET:
        try:
            payload = _fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise ValueError(
                "Unable to decrypt value: bad token or key mismatch"
            ) from exc
        return signing.loads(payload)
    if isinstance(token, str) and token.startswith("sig:"):
        return signing.loads(token[4:])
    raise ValueError("Unable to decrypt value: unsupported token format")
