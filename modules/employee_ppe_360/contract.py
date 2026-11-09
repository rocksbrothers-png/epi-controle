"""Contratos de backend da Ficha 360° de EPI (fatia F0).

Este módulo NÃO registra rotas. Ele fixa, com testes, as regras que toda
consulta futura da Ficha (F1–F6) terá de seguir, para que nenhuma seção
nasça com o próprio jeito de autorizar, paginar ou responder:

1. **Autorização reaproveitada, nunca duplicada.** O acesso ao colaborador
   exige ``employees:view`` (permissão existente) e o escopo de LEITURA já
   oficial, ``ensure_actor_employee_visibility_scope`` — tenant primeiro,
   depois unidade operacional ou vínculo local ativo. Nenhuma permissão nova.
2. **Conhecer o id não basta.** Colaborador inexistente, de outra empresa ou
   fora do escopo resultam no MESMO erro (``EMPLOYEE_NOT_FOUND``, HTTP 404):
   a resposta não revela se o registro existe.
3. **Paginação no servidor.** ``limit`` limitado a ``PAGE_MAX`` e cursor
   opaco validado; nenhuma seção devolve histórico inteiro para o navegador
   filtrar.
4. **Envelope único.** ``{ok, data, page}`` no sucesso; ``{ok: false,
   error: {code, message}}`` no erro, com mensagem genérica — sem detalhe de
   exceção, SQL ou identificador de outro tenant.

Somente leitura: este pacote não escreve no banco (guarda em
``tests/test_employee_ppe_360_f0_contract.py``).
"""

from __future__ import annotations

import base64
import binascii
import json
import re

from core.auth import ensure_permission
from core.permissions import PERM_EMPLOYEES_VIEW

PAGE_DEFAULT = 20
PAGE_MAX = 100
CURSOR_MAX_LENGTH = 200
_CURSOR_RE = re.compile(r'^[A-Za-z0-9_-]+$')
_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}(?:[T ][0-9:.+\-Z]*)?$')

# Código → (status HTTP, mensagem genérica). As mensagens são neutras de
# propósito: o cliente traduz pelo ``code`` (i18n), nunca pelo texto.
ERRORS = {
    'INVALID_EMPLOYEE_ID': (400, 'Identificador de colaborador inválido.'),
    'INVALID_PAGINATION': (400, 'Parâmetros de paginação inválidos.'),
    'FORBIDDEN': (403, 'Perfil sem permissão para esta consulta.'),
    'EMPLOYEE_NOT_FOUND': (404, 'Colaborador indisponível no seu escopo.'),
}


class ContractError(Exception):
    """Erro de contrato com código estável (o texto é só apoio)."""

    def __init__(self, code: str):
        if code not in ERRORS:
            raise ValueError(f'código de erro desconhecido: {code}')
        super().__init__(ERRORS[code][1])
        self.code = code
        self.status = ERRORS[code][0]


def parse_employee_id(raw) -> int:
    """Inteiro positivo, sem coerção de float/bool/notação estranha."""
    if isinstance(raw, bool):
        raise ContractError('INVALID_EMPLOYEE_ID')
    if isinstance(raw, int):
        value = raw
    else:
        text = str(raw if raw is not None else '').strip()
        if not text.isdigit() or len(text) > 12:
            raise ContractError('INVALID_EMPLOYEE_ID')
        value = int(text)
    if value <= 0:
        raise ContractError('INVALID_EMPLOYEE_ID')
    return value


def _first(query, key):
    value = (query or {}).get(key)
    if isinstance(value, (list, tuple)):
        if len(value) > 1:
            raise ContractError('INVALID_PAGINATION')
        value = value[0] if value else None
    return value


def encode_cursor(sort_value: str, row_id: int) -> str:
    """Cursor opaco para paginação estável por (data, id) decrescente."""
    if not isinstance(row_id, int) or isinstance(row_id, bool) or row_id <= 0:
        raise ValueError('row_id inválido para cursor')
    if not _DATE_RE.match(str(sort_value or '')):
        raise ValueError('sort_value inválido para cursor')
    raw = json.dumps({'s': str(sort_value), 'i': row_id}, separators=(',', ':')).encode('utf-8')
    return base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')


def decode_cursor(cursor: str) -> tuple[str, int]:
    text = str(cursor or '')
    if not text or len(text) > CURSOR_MAX_LENGTH or not _CURSOR_RE.match(text):
        raise ContractError('INVALID_PAGINATION')
    try:
        padded = text + '=' * (-len(text) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode('ascii')).decode('utf-8'))
    except (binascii.Error, ValueError, UnicodeDecodeError):
        raise ContractError('INVALID_PAGINATION') from None
    if not isinstance(payload, dict) or set(payload) != {'s', 'i'}:
        raise ContractError('INVALID_PAGINATION')
    sort_value, row_id = payload['s'], payload['i']
    if (not isinstance(row_id, int) or isinstance(row_id, bool) or row_id <= 0
            or not isinstance(sort_value, str) or not _DATE_RE.match(sort_value)):
        raise ContractError('INVALID_PAGINATION')
    return sort_value, row_id


def parse_page_params(query) -> dict:
    """``limit`` (1..PAGE_MAX, padrão PAGE_DEFAULT) e ``cursor`` opcional.

    Aceita o formato de ``urllib.parse.parse_qs`` (listas) ou dict simples.
    Valor repetido, não numérico ou fora da faixa é recusado — nunca
    "corrigido" silenciosamente para um valor maior.
    """
    raw_limit = _first(query, 'limit')
    if raw_limit is None or str(raw_limit).strip() == '':
        limit = PAGE_DEFAULT
    else:
        text = str(raw_limit).strip()
        if not text.isdigit():
            raise ContractError('INVALID_PAGINATION')
        limit = int(text)
        if limit < 1 or limit > PAGE_MAX:
            raise ContractError('INVALID_PAGINATION')
    raw_cursor = _first(query, 'cursor')
    cursor = None
    if raw_cursor is not None and str(raw_cursor).strip() != '':
        cursor = decode_cursor(str(raw_cursor).strip())
    return {'limit': limit, 'cursor': cursor}


def resolve_authorized_employee(connection, actor, employee_id, *, get_employee_fn=None, visibility_scope_fn=None):
    """Colaborador que o ator pode CONSULTAR, ou ``ContractError``.

    Ordem: permissão funcional → existência → tenant/escopo. Inexistente e
    fora de escopo produzem o mesmo erro 404. As funções de leitura e de
    escopo são as oficiais de ``modules.employees.service`` (injetáveis só
    para teste).
    """
    if not actor or not actor.get('role'):
        raise ContractError('FORBIDDEN')
    try:
        ensure_permission(actor, PERM_EMPLOYEES_VIEW)
    except PermissionError:
        raise ContractError('FORBIDDEN') from None
    employee_id = parse_employee_id(employee_id)
    if get_employee_fn is None or visibility_scope_fn is None:
        from modules.employees.service import (
            ensure_actor_employee_visibility_scope,
            get_employee_by_id,
        )
        get_employee_fn = get_employee_fn or get_employee_by_id
        visibility_scope_fn = visibility_scope_fn or ensure_actor_employee_visibility_scope
    employee = get_employee_fn(connection, employee_id)
    if not employee:
        raise ContractError('EMPLOYEE_NOT_FOUND')
    try:
        visibility_scope_fn(connection, actor, employee)
    except (PermissionError, ValueError):
        raise ContractError('EMPLOYEE_NOT_FOUND') from None
    return employee


def success_envelope(data, *, limit=None, next_cursor=None) -> dict:
    envelope = {'ok': True, 'data': data}
    if limit is not None:
        envelope['page'] = {'limit': int(limit), 'next_cursor': next_cursor}
    return envelope


def error_envelope(error: ContractError) -> tuple[int, dict]:
    """(status, corpo). Só o código e a mensagem genérica saem."""
    return error.status, {'ok': False, 'error': {'code': error.code, 'message': ERRORS[error.code][1]}}


__all__ = [
    'CURSOR_MAX_LENGTH',
    'ERRORS',
    'PAGE_DEFAULT',
    'PAGE_MAX',
    'ContractError',
    'decode_cursor',
    'encode_cursor',
    'error_envelope',
    'parse_employee_id',
    'parse_page_params',
    'resolve_authorized_employee',
    'success_envelope',
]
