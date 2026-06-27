"""Cliente HTTP fino para a API do Mercado Pago.

Usa apenas a biblioteca padrão (urllib) para não acrescentar dependências ao
projeto. TODO acesso à API do Mercado Pago acontece exclusivamente no backend,
autenticado com o Access Token secreto (MERCADO_PAGO_ACCESS_TOKEN). O Access
Token NUNCA é enviado ao frontend.
"""

import json
import urllib.error
import urllib.request
import uuid

from epi_backend.config import MERCADO_PAGO_ACCESS_TOKEN
from epi_backend.http_utils import structured_log

MP_API_BASE = "https://api.mercadopago.com"
_TIMEOUT_SECONDS = 30


class MercadoPagoError(RuntimeError):
    """Erro ao comunicar com a API do Mercado Pago."""

    def __init__(self, message, *, status=None, response=None):
        super().__init__(message)
        self.status = status
        self.response = response or {}


def _require_access_token():
    if not MERCADO_PAGO_ACCESS_TOKEN:
        raise MercadoPagoError(
            "MERCADO_PAGO_ACCESS_TOKEN não configurado no backend.",
            status=503,
        )
    return MERCADO_PAGO_ACCESS_TOKEN


def _request(method, path, body=None, *, idempotency_key=None):
    token = _require_access_token()
    url = path if path.startswith("http") else f"{MP_API_BASE}{path}"
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if method.upper() == "POST":
        headers["X-Idempotency-Key"] = idempotency_key or str(uuid.uuid4())

    request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8") or "{}"
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = ""
        try:
            raw = exc.read().decode("utf-8")
        except Exception:  # pragma: no cover - defensivo
            raw = ""
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        message = parsed.get("message") or parsed.get("error") or f"HTTP {exc.code}"
        structured_log(
            "error",
            "mercadopago.http_error",
            method=method.upper(),
            path=path,
            status=exc.code,
            error=message,
        )
        raise MercadoPagoError(
            f"Mercado Pago: {message}", status=exc.code, response=parsed
        ) from exc
    except urllib.error.URLError as exc:
        structured_log("error", "mercadopago.connection_error", method=method.upper(), path=path, error=str(exc))
        raise MercadoPagoError(f"Falha de conexão com o Mercado Pago: {exc}") from exc


def post(path, body, *, idempotency_key=None):
    return _request("POST", path, body, idempotency_key=idempotency_key)


def get(path):
    return _request("GET", path)


def put(path, body):
    return _request("PUT", path, body)
