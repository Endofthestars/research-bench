import hmac
import time
from collections import defaultdict

from fastapi import Header, HTTPException, Request

from . import config

_buckets: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(key: str) -> None:
    now = time.time()
    window = _buckets[key]
    window[:] = [t for t in window if now - t < 60]
    if len(window) >= config.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="rate limit exceeded, try again later")
    window.append(now)


async def verify_token(request: Request, authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token, config.BEARER_TOKEN):
        raise HTTPException(status_code=401, detail="invalid token")
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)
