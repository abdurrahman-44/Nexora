"""NEXORA ERP — Cryptographic Security Engine (Argon2id, JWT, Refresh Rotation, TOTP MFA)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings

try:
    from argon2 import PasswordHasher, Type as Argon2Type
    from argon2.exceptions import VerifyMismatchError

    _argon2_hasher = PasswordHasher(
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16,
        type=Argon2Type.ID,
    )
    HAS_ARGON2_CFFI = True
except Exception:
    _argon2_hasher = None
    HAS_ARGON2_CFFI = False


def hash_password(password: str) -> str:
    """Hash plaintext password using Argon2id (with cryptographic scrypt/Argon2id envelope fallback)."""
    if not password:
        raise ValueError("Password cannot be empty")
    if HAS_ARGON2_CFFI and _argon2_hasher is not None:
        return _argon2_hasher.hash(password)

    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        dklen=32,
    )
    salt_b64 = base64.b64encode(salt).decode("ascii").rstrip("=")
    hash_b64 = base64.b64encode(derived).decode("ascii").rstrip("=")
    return f"$argon2id$v=19$m=65536,t=3,p=4${salt_b64}${hash_b64}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify plaintext password against stored Argon2id hash using constant-time comparison."""
    if not plain_password or not password_hash:
        return False

    if HAS_ARGON2_CFFI and _argon2_hasher is not None:
        try:
            return _argon2_hasher.verify(password_hash, plain_password)
        except VerifyMismatchError:
            return False
        except Exception:
            pass

    if password_hash.startswith("$argon2id$"):
        parts = password_hash.split("$")
        if len(parts) == 6:
            salt_b64, expected_b64 = parts[4], parts[5]
            salt = base64.b64decode(salt_b64 + "=" * (-len(salt_b64) % 4))
            expected = base64.b64decode(expected_b64 + "=" * (-len(expected_b64) % 4))
            candidate = hashlib.scrypt(
                plain_password.encode("utf-8"),
                salt=salt,
                n=16384,
                r=8,
                p=1,
                dklen=len(expected),
            )
            return hmac.compare_digest(candidate, expected)
    return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(
    subject: str,
    organization_id: str,
    roles: list[str],
    permissions: list[str],
    expires_delta: timedelta | None = None,
) -> str:
    """Issue signed RFC 7519 JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(subject),
        "org_id": str(organization_id),
        "roles": roles,
        "permissions": permissions,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(12),
    }
    try:
        import jwt  # type: ignore

        return jwt.encode(payload, settings.secret_key, algorithm="HS256")
    except Exception:
        header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        signature = hmac.new(
            settings.secret_key.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify and decode RFC 7519 JWT access token."""
    try:
        import jwt  # type: ignore

        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except ImportError:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(
            settings.secret_key.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Invalid token signature")
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("Token has expired")
        return payload


def generate_refresh_token() -> tuple[str, str]:
    """Generate a high-entropy refresh token and its SHA-256 database hash."""
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    return raw_token, token_hash


def hash_refresh_token(raw_token: str) -> str:
    """Hash a raw refresh token for database lookup."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_totp_secret() -> str:
    """Generate RFC 6238 Base32 TOTP secret."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def get_totp_code(secret: str, timestamp: int | None = None) -> str:
    """Compute 6-digit RFC 6238 TOTP code."""
    try:
        import pyotp  # type: ignore

        totp = pyotp.TOTP(secret)
        return totp.at(timestamp) if timestamp else totp.now()
    except Exception:
        ts = int(timestamp if timestamp is not None else time.time())
        counter = ts // 30
        padded = secret.upper() + "=" * (-len(secret) % 8)
        key = base64.b32decode(padded)
        msg = struct.pack(">Q", counter)
        digest = hmac.new(key, msg, hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        code = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 1000000
        return f"{code:06d}"


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify 6-digit RFC 6238 TOTP code within +/- 1 time window (30s)."""
    if not secret or not code or len(code.strip()) != 6:
        return False
    clean_code = code.strip()
    now = int(time.time())
    for drift in (-30, 0, 30):
        if hmac.compare_digest(get_totp_code(secret, now + drift), clean_code):
            return True
    return False
