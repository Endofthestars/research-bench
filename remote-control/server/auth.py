import hmac
import secrets
import time
from collections import defaultdict

from fastapi import Header, HTTPException, Request

from . import config

_buckets: dict[str, list[float]] = defaultdict(list)

# SSE 流的一次性 ticket:EventSource 不能带 Authorization 头,又不能把长期 token
# 放进 URL(会进浏览器历史/反代 access log)。所以用 Bearer token 先换一张
# 短时(60s)、单次使用、绑定 run_id 的 ticket,只有它出现在 query string 里。
# 泄露的 ticket 要么已被消费要么已过期,拿不到长期凭证。
STREAM_TICKET_TTL_SECONDS = 60
_stream_tickets: dict[str, tuple[str, float]] = {}  # ticket -> (run_id, expires_at)


def issue_stream_ticket(run_id: str) -> str:
    now = time.time()
    for t, (_rid, exp) in list(_stream_tickets.items()):
        if exp < now:
            _stream_tickets.pop(t, None)
    ticket = secrets.token_urlsafe(32)
    _stream_tickets[ticket] = (run_id, now + STREAM_TICKET_TTL_SECONDS)
    return ticket


def _consume_stream_ticket(ticket: str, run_id: str) -> bool:
    entry = _stream_tickets.pop(ticket, None)  # 单次使用:查到即作废
    if entry is None:
        return False
    rid, expires_at = entry
    return hmac.compare_digest(rid, run_id) and time.time() <= expires_at


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


async def verify_stream_access(
    run_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
    ticket: str | None = None,
) -> None:
    """SSE 流端点的认证:标准 Bearer 头(curl 等能带头的客户端)或一次性 ticket
    (浏览器 EventSource)。两条路都不通就 401——和其他端点一样,不存在无鉴权访问。"""
    if authorization:
        await verify_token(request, authorization)
        return
    if ticket and _consume_stream_ticket(ticket, run_id):
        return
    raise HTTPException(status_code=401, detail="missing bearer token or valid stream ticket")
