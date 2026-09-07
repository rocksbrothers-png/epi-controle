import json
import os
from datetime import datetime
from urllib.parse import unquote

from epi_backend.config import UTC


def _json_safe(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return str(value)


# ── Redação de credencial em query string (#343, F1) ─────────────────────────
#
# UM único mecanismo, chamado EXPLICITAMENTE por cada sink que registra um path
# cru. Deliberadamente NÃO é um filtro mágico dentro do `structured_log`: aquele
# sink registra muita coisa além de path, e interceptar por nome de campo faria
# um sink novo nascer "protegido" por acidente, sem ninguém ter pensado nele.
# Chamada explícita + gate que enumera os sinks é o que mantém a cobertura
# verificável em vez de presumida.

SENSITIVE_QUERY_PARAMS = frozenset({"username", "password", "token", "employee_token"})
"""Nomes cujo VALOR nunca pode ser reproduzido num log.

A lista é de NOMES, não de padrões no valor: procurar "parece uma senha" no
texto erra dos dois lados. É curta de propósito — cada nome está aqui porque a
auditoria PROVOU que ele trafega, ou trafegou, em query string neste código:

  username, password  o achado original da F1. `preloadLoginFromUrl` (removido)
                      aceitava exatamente estes dois, e são os que
                      `sanitizeLoginUrlParams` ainda remove de links antigos.
  token               `modules/portal/routes.py` lê `?token=` hoje, em
                      `handle_get_employee_access` e `..._pdf`.
  employee_token      `modules/portal/service.py` GERA o link do portal como
                      `/?employee_token=…`, e `static/app.js` o LÊ no
                      carregamento da página: toda visita normal ao portal
                      leva uma credencial de capacidade na query.

Nomes que NÃO entram, e por quê: `code` é código de negócio
(`modules/deliveries/routes.py`), `qr_code` identifica item físico e o backend
valida posse antes de agir, e `actor_user_id`/`user_id`/`unit_id` são
identificadores — justamente a observabilidade que precisa sobreviver.
`new_password`, `totp_code`, `recovery_key` e afins viajam no CORPO do POST,
nunca na query: redigi-los aqui seria código morto fingindo proteção.

O gate fixa esta lista. Ampliá-la é um ato deliberado, com evidência — não uma
precaução silenciosa.
"""


def _canonical_param_name(name):
    """Normaliza o NOME do parâmetro do jeito que o servidor de fato o lê.

    `parse_qs` aplica exatamente UMA passada de percent-decoding no nome, e é
    por `parse_qs` que as rotas do portal leem a query. Então `to%6ben=…` chega
    na rota como `token`: comparar o nome cru deixaria a credencial passar por
    um caractere de diferença.

    Uma passada, não um laço. Duas passadas redigiriam `%2570assword`, que o
    servidor NÃO aceita como `password` — o redator cobre exatamente o que é
    aceito, nem mais nem menos.
    """
    return unquote(str(name).strip()).strip().lower()


def redact_sensitive_query(text):
    """Substitui por `***` o VALOR dos parâmetros sensíveis, preservando o resto.

    Aceita as duas formas em que um path aparece nos sinks:

        path cru       `/api/employee-access?token=…&cpf_last3=123`
        linha de log   `"GET /?password=… HTTP/1.1" 200 -`

    Preserva método, rota, status, tamanho e os parâmetros de negócio: a
    observabilidade legítima é metade do contrato, e redigir tudo seria tão ruim
    quanto não redigir nada.
    """
    texto = str(text)
    if "?" not in texto:
        return texto
    antes, _, resto = texto.partition("?")
    # Numa linha de request a query termina no primeiro espaço (o `HTTP/1.1"`);
    # num path cru não há espaço, e `partition` devolve a query inteira.
    query, separador, depois = resto.partition(" ")
    partes = []
    for parte in query.split("&"):
        nome, sep, _valor = parte.partition("=")
        if sep and _canonical_param_name(nome) in SENSITIVE_QUERY_PARAMS:
            # O nome fica COMO VEIO: o log continua fiel ao que o cliente
            # mandou, inclusive na forma codificada, e só o valor desaparece.
            partes.append(f"{nome}=***")
        else:
            partes.append(parte)
    return f'{antes}?{"&".join(partes)}{separador}{depois}'


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
            path=redact_sensitive_query(getattr(handler, "path", "")),
            status=status,
        )


def send_api_response(handler, status, *, data=None, message="", error=None, extra=None):
    """Envelope REST padronizado {success, data, message} / {success, error}.

    Transitório e ADITIVO: inclui também `ok` (espelho de `success`) durante o
    período de compatibilidade, para não quebrar o legado/Flutter que ainda leem
    `ok`. O campo `ok` será removido na Fase 7 (descomissionamento do legado).

    Sucesso: {"success": true, "ok": true, "data": {...}, "message": "..."}
    Erro:    {"success": false, "ok": false, "error": {"code", "message"}}
    """
    if error is not None:
        payload = {"success": False, "ok": False, "error": error}
    else:
        payload = {
            "success": True,
            "ok": True,
            "data": data if data is not None else {},
            "message": str(message or ""),
        }
    if extra:
        payload.update(extra)
    return send_json(handler, status, payload)


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


def request_base_url(handler):
    forwarded_proto = str(handler.headers.get('X-Forwarded-Proto', '')).strip()
    scheme = forwarded_proto or ('https' if 'onrender.com' in str(handler.headers.get('Host', '')).lower() else 'http')
    host = str(handler.headers.get('Host', '')).strip()
    configured = str(os.environ.get('PUBLIC_BASE_URL', '')).strip()
    if configured:
        return configured.rstrip('/')
    return f'{scheme}://{host}'.rstrip('/')
