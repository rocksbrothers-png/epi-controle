import json
import os
import re
from datetime import datetime
from urllib.parse import unquote

from epi_backend.config import UTC

# ── Segredos em texto livre de erro (segurança 503/500) ──────────────────────
#
# Mensagens de driver/libpq podem trazer a URL de conexão (inclusive a senha,
# quando a DATABASE_URL está malformada), host, usuário e SQL. Nos LOGS a
# senha some e o resto fica para diagnóstico; no CLIENTE nada disso aparece.
# Limite de texto analisado por campo: a redação roda em todo campo de log, e
# o caminho da requisição (controlado pelo cliente, sem autenticação) é logado
# várias vezes por request. O texto acima do limite é truncado ANTES das regex.
_REDACT_MAX_CHARS = 8192
_REDACT_MARGIN = 1024
_SENSITIVE_NAME = (
    r'(?:password|passwd|pwd|pgpassword|secret|client[_-]?secret|token|access[_-]?token|'
    r'refresh[_-]?token|api[_-]?key|x-api-key|apikey|authorization)'
)
# Todas as regex são ancoradas por lookbehind (nenhuma tentativa no meio de uma
# palavra) e sem quantificadores aninhados: custo linear no tamanho do texto.
_SECRET_PATTERNS = (
    # esquema://usuario:senha@host — a senha vai até o ÚLTIMO '@' do token (aceita '@' e '/').
    (re.compile(r'(?<![A-Za-z0-9+.-])([A-Za-z][A-Za-z0-9+.-]{0,31}://[^\s:/@]{0,256}:)\S{1,512}@(?=[^\s@]*(?:\s|$))'),
     r'\1***@'),
    # Bearer|Basic <credencial>; `Token` só logo após `Authorization:`. O valor precisa ter
    # cara de credencial (≥ 8 caracteres com dígito ou símbolo), para não mascarar texto como
    # "Invalid token signature" ou "basic validation failed".
    (re.compile(r'(?i)(?<![A-Za-z0-9])(bearer|basic|(?<=:)\s*token)\s+'
                r'(?=[A-Za-z0-9._~+/=-]{8,4096})(?=[A-Za-z0-9._~+/=-]{0,4095}?(?:[0-9._~+/=-]|(?-i:[a-z][A-Z])))[A-Za-z0-9._~+/=-]{8,4096}'),
     r'\1 ***'),
    # JWT solto (três segmentos base64url)
    (re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{5,4096}\.[A-Za-z0-9_-]{5,4096}\.[A-Za-z0-9_-]{5,4096}'), '***'),
    # Cabeçalhos HTTP com credencial, mesmo sem aspas: `X-Api-Key: abc`, `Cookie: s=1`.
    (re.compile(r'(?im)(?<![A-Za-z0-9-])(x-api-key|authorization|proxy-authorization|cookie|set-cookie)'
                r'([ \t]*+:[ \t]*+)((?:bearer|basic|token)[ \t]+)?+(?!\*\*\*)([^\r\n]{1,4096})'), r'\1\2\3***'),
    # nome=valor (DSN chave=valor, query string, env): qualquer valor até o separador
    (re.compile(r'(?i)(?<![A-Za-z0-9])(' + _SENSITIVE_NAME + r')(\s*=\s*)("[^"]{0,4096}"|\'[^\']{0,4096}\'|[^\s&;,]{1,4096})'),
     r'\1\2***'),
    # "nome": "valor" / 'nome': 'valor' (JSON e repr) — só valor entre aspas, para não
    # apagar texto legível como "password: authentication failed".
    (re.compile(r'(?i)(?<![A-Za-z0-9])(' + _SENSITIVE_NAME + r')(["\']?\s*:\s*)("[^"]{0,4096}"|\'[^\']{0,4096}\')'),
     r'\1\2***'),
)
_SENSITIVE_KEY = re.compile(r'(?i)(?:^|[^A-Za-z0-9])' + _SENSITIVE_NAME + r'$')


def redact_secrets(text):
    """Remove senhas/tokens de um texto livre, preservando o resto para diagnóstico."""
    texto = str(text)
    excedente = len(texto) - _REDACT_MAX_CHARS
    # Redige uma fatia com folga ANTES de cortar: um segredo que cruza o limite é
    # mascarado inteiro, e o corte nunca deixa metade de uma senha no log.
    if excedente > 0:
        texto = texto[:_REDACT_MAX_CHARS + _REDACT_MARGIN]
    for pattern, replacement in _SECRET_PATTERNS:
        texto = pattern.sub(replacement, texto)
    if excedente > 0:
        texto = texto[:_REDACT_MAX_CHARS] + f'…[truncado: {excedente} caracteres]'
    return texto


def _is_sensitive_key(key, value=None):
    # Booleanos, números e None não carregam credencial (`has_token: True`).
    if isinstance(value, (bool, int, float)) or value is None:
        return False
    return bool(_SENSITIVE_KEY.search(str(key)))


PUBLIC_INTERNAL_ERROR = 'Erro interno do servidor. Os detalhes técnicos ficam registrados nos logs.'


class PublicServerError(RuntimeError):
    """Falha de servidor cuja mensagem é, por CONTRATO, segura para o cliente.

    Só use com texto fixo de negócio escrito no código (nunca `str(exc)` de
    terceiros, SQL, caminhos, URLs ou dados do usuário). Qualquer outra exceção
    que chegue a um handler genérico de 500 vira PUBLIC_INTERNAL_ERROR.
    """


def public_error_message(exc):
    """Texto do erro 500 que pode ir ao cliente: lista de PERMISSÃO, não de bloqueio.

    Exceção não classificada → mensagem genérica. A mensagem original só passa
    quando a exceção é `PublicServerError` (contrato explícito no ponto do raise).
    """
    if isinstance(exc, PublicServerError):
        texto = str(exc).strip()
        if texto:
            return texto
    return PUBLIC_INTERNAL_ERROR


def _json_safe(value):
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {redact_secrets(key): ('***' if _is_sensitive_key(key, item) else _json_safe(item))
                for key, item in value.items()}
    return redact_secrets(value)


# ── Redação de credencial em query string (#343, F1) ─────────────────────────
#
# UM único mecanismo, chamado EXPLICITAMENTE por cada sink que registra um path
# cru. Deliberadamente NÃO é um filtro mágico dentro do `structured_log`: aquele
# sink registra muita coisa além de path, e interceptar por nome de campo faria
# um sink novo nascer "protegido" por acidente, sem ninguém ter pensado nele.
# Chamada explícita + gate que enumera os sinks é o que mantém a cobertura
# verificável em vez de presumida.

SENSITIVE_QUERY_PARAMS = frozenset({"username", "password", "token", "employee_token", "cpf_last3"})
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
  cpf_last3           acrescentado pela F4 da #343, com evidência: é o SEGUNDO
                      FATOR do portal (posse do link + conhecimento dos 3
                      dígitos), e `handle_get_employee_access` e `..._pdf` o
                      leem de `?cpf_last3=` — toda validação bem-sucedida põe o
                      fator na query. Antes disso ele sobrevivia no path cru
                      registrado, ao lado de um `employee_token` já redigido.

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
        **{key: ('***' if _is_sensitive_key(key, value) else _json_safe(value)) for key, value in fields.items()},
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def send_json(handler, status, payload, headers=None):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    for name, value in (headers or {}).items():
        handler.send_header(name, value)
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


DB_POOL_SATURATED_CODE = "DB_POOL_SATURATED"
DB_POOL_SATURATED_MESSAGE = "Servidor ocupado no momento. Tente novamente em instantes."


def send_db_pool_saturated(handler, method, path):
    """503 controlado quando o pool de conexões não liberou vaga no prazo (P0).

    Mesmo envelope do 503 de bootstrap (``ok``/``error.code``/``error.message``),
    que o cliente web já trata como indisponibilidade temporária e não fatal.
    ``Retry-After`` orienta o novo envio. Nada da requisição vai para o log além
    de método e caminho sem query string.
    """
    structured_log("warning", "http.db_pool_saturated", method=method, path=str(path).split("?", 1)[0])
    try:
        return send_json(
            handler,
            503,
            {"ok": False, "error": {"code": DB_POOL_SATURATED_CODE, "message": DB_POOL_SATURATED_MESSAGE}},
            headers={"Retry-After": "1"},
        )
    except (BrokenPipeError, ConnectionResetError):
        return None


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
