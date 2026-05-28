from starlette.datastructures import Headers
from starlette.websockets import WebSocket


def _first_forwarded_ip(value: str | None) -> str | None:
    if not value:
        return None
    first = value.split(",", 1)[0].strip()
    return first or None


def client_key_from_headers(headers: Headers, fallback_host: str | None) -> str:
    forwarded = _first_forwarded_ip(headers.get("x-forwarded-for"))
    if forwarded:
        return forwarded
    real_ip = headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return fallback_host or "unknown"


def client_key_from_websocket(websocket: WebSocket) -> str:
    host = websocket.client.host if websocket.client else None
    return client_key_from_headers(websocket.headers, host)
