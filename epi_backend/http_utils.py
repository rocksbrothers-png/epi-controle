import json
from datetime import datetime

from epi_backend.config import UTC


def _json_safe(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return str(value)


def structured_log(level, event, **fields):
    payload = {
        "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "level": str(level).lower(),
        "event": event,
        **{key: _json_safe(value) for key, value in fields.items()},
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def send_json(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
    if str(handler.path).startswith("/api/") or str(handler.path).startswith("/health"):
        structured_log(
            "info" if status < 400 else "error",
            "http.response",
            method=getattr(handler, "command", ""),
            path=getattr(handler, "path", ""),
            status=status,
        )


def send_bytes(handler, status, content_type, body, filename=None):
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    if filename:
        handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.end_headers()
    handler.wfile.write(body)


def parse_json(handler):
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Content-Length inválido.") from exc
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("JSON inválido no corpo da requisição.") from exc


def require_fields(payload, fields):
    for field in fields:
        if payload.get(field) in (None, ""):
            raise ValueError(f"Campo obrigatório: {field}")
