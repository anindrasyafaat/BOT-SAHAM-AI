"""
Login sederhana & gratis: satu password (APP_PASSWORD) -> token bertanda tangan HMAC-SHA256.

- Kunci penandatangan diturunkan dari password + SECRET_KEY, jadi mengganti password otomatis
  membatalkan semua token lama (tidak ada wewenang yang "membeku" di token).
- Semua /api/* dan WebSocket wajib token bila APP_PASSWORD di-set; satu titik penegakan (middleware).
- ENVIRONMENT=production tanpa APP_PASSWORD -> aplikasi menolak start (tidak ada default terbuka).
"""

import base64
import hashlib
import hmac
import json
import time
from collections import deque
from typing import Optional

from config import settings

TOKEN_TTL = 7 * 24 * 3600
PUBLIC_PATHS = {"/api/auth/login", "/api/auth/status"}
_failures: deque = deque()          # waktu login gagal (global): batasi brute force
MAX_FAILURES_PER_MIN = 10


def enabled() -> bool:
    return bool(settings.app_password)


def check_startup():
    if settings.environment == "production" and not enabled():
        raise RuntimeError("APP_PASSWORD wajib di-set untuk ENVIRONMENT=production (lihat .env.example)")


def _key() -> bytes:
    return hashlib.sha256(f"{settings.secret_key}\0{settings.app_password}".encode()).digest()


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def issue(now: Optional[float] = None) -> str:
    payload = _b64(json.dumps({"exp": int((now or time.time()) + TOKEN_TTL)}).encode())
    sig = _b64(hmac.new(_key(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def verify(token: Optional[str], now: Optional[float] = None) -> bool:
    if not enabled():
        return True
    if not token or token.count(".") != 1:
        return False
    payload, sig = token.split(".")
    good = _b64(hmac.new(_key(), payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, good):
        return False
    try:
        exp = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["exp"]
    except (ValueError, KeyError, TypeError):
        return False
    return (now or time.time()) < exp


def throttled(now: Optional[float] = None) -> bool:
    now = now or time.time()
    while _failures and now - _failures[0] > 60:
        _failures.popleft()
    return len(_failures) >= MAX_FAILURES_PER_MIN


def login(password: str, now: Optional[float] = None) -> Optional[str]:
    """Token bila password benar; None bila salah. Perbandingan waktu-konstan."""
    ok = hmac.compare_digest(hashlib.sha256(password.encode()).digest(),
                             hashlib.sha256(settings.app_password.encode()).digest())
    if not ok:
        _failures.append(now or time.time())
        return None
    return issue(now)


def bearer(header: Optional[str]) -> Optional[str]:
    if header and header.lower().startswith("bearer "):
        return header[7:].strip()
    return None
