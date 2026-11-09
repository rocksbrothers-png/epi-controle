"""CO-1 — limite de alçada de aprovação de PO por empresa (D-1, D-2).

Fonte única de verdade: a chave já existente ``po_approval_threshold`` dentro de
``app_meta['purchase_config_{company_id}']``, lida pela aprovação de PO
(``_po_company_approval_threshold``). Nenhuma tabela nova, nenhuma segunda fonte.

Regras:

* **Quem configura:** só quem tem ``purchase_limits:manage`` — exclusiva do
  Administrador Geral (``core/permissions.py``), sempre na PRÓPRIA empresa.
  ``finance:view`` não concede edição; o Aprovador não define a própria alçada.
* **Sem valor padrão.** Ausência de configuração = sem limite = um nível de
  aprovação (comportamento atual). Ausência NUNCA é lida como zero.
* **Zero é recusado.** "Todo PO exige dois níveis" não é expresso por 0: o valor
  precisa ser > 0. Para voltar a um nível, remove-se o limite (``value: null``),
  e a remoção é auditada como tal.
* **Dinheiro sem ponto flutuante.** ``Decimal`` com 2 casas, em BRL (Compras não
  tem outra moeda). Valor com mais de 2 casas é recusado, não arredondado.
* **Concorrência.** Leitura-modificação-escrita sob trava da linha de
  configuração (``BEGIN IMMEDIATE`` no SQLite, ``SELECT … FOR UPDATE`` no
  Postgres) e controle de versão otimista (``expected_version``): duas edições
  concorrentes não se sobrescrevem em silêncio.
* **Auditoria.** Criação, alteração e remoção geram ``purchase_events`` com
  valor anterior e posterior.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from core.auth import ensure_permission
from core.permissions import PERM_PURCHASE_LIMITS_MANAGE
from modules.purchases.audit import record_purchase_event
from modules.purchases.governance import PurchaseConflictError

CURRENCY = 'BRL'
THRESHOLD_KEY = 'po_approval_threshold'
VERSION_KEY = 'po_approval_threshold_version'
UPDATED_AT_KEY = 'po_approval_threshold_updated_at'
UPDATED_BY_KEY = 'po_approval_threshold_updated_by_user_id'
UPDATED_BY_NAME_KEY = 'po_approval_threshold_updated_by_name'
MAX_THRESHOLD = Decimal('999999999999.99')
CENT = Decimal('0.01')

MSG_INVALID_VALUE = 'Limite de alçada inválido: informe um valor maior que zero, com até duas casas decimais.'
MSG_TOO_LARGE = 'Limite de alçada acima do máximo permitido.'
MSG_INVALID_CURRENCY = 'Moeda não suportada para o limite de alçada.'
MSG_VERSION_REQUIRED = 'Versão da configuração obrigatória para salvar o limite de alçada.'
MSG_VERSION_CONFLICT = 'O limite de alçada foi alterado por outro usuário. Recarregue e tente novamente.'
MSG_NO_COMPANY = 'Empresa obrigatória para configurar o limite de alçada.'


def config_key(company_id) -> str:
    return f'purchase_config_{int(company_id)}'


def _is_sqlite(connection) -> bool:
    from epi_backend.db import _is_sqlite_connection
    return _is_sqlite_connection(connection)


def parse_threshold_input(raw):
    """Valor enviado pelo cliente → ``Decimal`` (2 casas) ou ``None`` (remover).

    Aceita texto decimal com ponto ("1500", "1500.5", "1500.50") ou inteiro.
    Recusa bool, float (perde precisão), notação científica, NaN/Infinito, sinal,
    separador de milhar, zero, negativos e mais de 2 casas.
    """
    if raw is None:
        return None
    if isinstance(raw, bool) or isinstance(raw, float):
        raise ValueError(MSG_INVALID_VALUE)
    if isinstance(raw, int):
        text = str(raw)
    elif isinstance(raw, str):
        text = raw.strip()
    else:
        raise ValueError(MSG_INVALID_VALUE)
    if not text or len(text) > 20 or not all(c.isdigit() or c == '.' for c in text) or text.count('.') > 1:
        raise ValueError(MSG_INVALID_VALUE)
    if text.startswith('.') or text.endswith('.'):
        raise ValueError(MSG_INVALID_VALUE)
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError(MSG_INVALID_VALUE) from None
    if not value.is_finite() or value <= 0:
        raise ValueError(MSG_INVALID_VALUE)
    if value.as_tuple().exponent < -2:
        raise ValueError(MSG_INVALID_VALUE)
    if value > MAX_THRESHOLD:
        raise ValueError(MSG_TOO_LARGE)
    return value.quantize(CENT)


def read_threshold(config) -> Decimal | None:
    """Limite vigente da configuração armazenada, ou ``None`` (sem limite).

    Compatível com o formato legado (número JSON, ex.: ``20000.0``): é lido pela
    representação decimal do texto, nunca por aritmética de float. Valores
    ausentes, inválidos ou <= 0 significam "sem limite" — a mesma semântica que
    a aprovação já aplicava antes desta fatia.
    """
    if not isinstance(config, dict):
        return None
    raw = config.get(THRESHOLD_KEY)
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError):
        return None
    if not value.is_finite() or value <= 0:
        return None
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def format_threshold(value: Decimal | None) -> str | None:
    return None if value is None else f'{value.quantize(CENT):f}'


def money(value) -> Decimal:
    """Valor monetário armazenado (REAL/NUMERIC) → ``Decimal`` com 2 casas.

    Converte pela representação textual (``str``), nunca operando em float.
    """
    if value is None or value == '':
        return Decimal('0.00')
    try:
        return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return Decimal('0.00')


def _load_config(connection, company_id, *, lock: bool) -> dict:
    key = config_key(company_id)
    if lock:
        if _is_sqlite(connection):
            if not connection.in_transaction:
                connection.execute('BEGIN IMMEDIATE')
            row = connection.execute('SELECT value FROM app_meta WHERE key = ?', (key,)).fetchone()
        else:
            # Garante a linha antes de travá-la: sem ela, duas primeiras gravações
            # concorrentes não teriam o que travar.
            connection.execute(
                "INSERT INTO app_meta (key, value) VALUES (?, '{}') ON CONFLICT (key) DO NOTHING", (key,)
            )
            row = connection.execute('SELECT value FROM app_meta WHERE key = ? FOR UPDATE', (key,)).fetchone()
    else:
        row = connection.execute('SELECT value FROM app_meta WHERE key = ?', (key,)).fetchone()
    if not row:
        return {}
    try:
        stored = json.loads(row['value'] or '{}')
    except (TypeError, ValueError):
        return {}
    return dict(stored) if isinstance(stored, dict) else {}


def _store_config(connection, company_id, config: dict) -> None:
    from core.meta import set_meta
    set_meta(connection, config_key(company_id), json.dumps(config, sort_keys=True))


def locked_purchase_config(connection, company_id) -> dict:
    """Configuração de Compras lida SOB TRAVA, para leitura-modificação-escrita.

    Usada por toda escrita na chave ``purchase_config_{company}``
    (alçada e revisão do Admin), para que uma não apague a outra.
    """
    return _load_config(connection, company_id, lock=True)


def store_purchase_config(connection, company_id, config: dict) -> None:
    _store_config(connection, company_id, config)


def describe(config: dict) -> dict:
    threshold = read_threshold(config)
    return {
        'po_approval_threshold': format_threshold(threshold),
        'currency': CURRENCY,
        'configured': threshold is not None,
        'version': int(config.get(VERSION_KEY) or 0),
        'updated_at': config.get(UPDATED_AT_KEY) or None,
        'updated_by_name': config.get(UPDATED_BY_NAME_KEY) or None,
    }


def get_purchase_limits(connection, company_id) -> dict:
    return describe(_load_config(connection, company_id, lock=False))


def _version_from_payload(raw) -> int:
    if isinstance(raw, bool) or raw is None:
        raise ValueError(MSG_VERSION_REQUIRED)
    text = str(raw).strip()
    if not text.isdigit():
        raise ValueError(MSG_VERSION_REQUIRED)
    return int(text)


def set_purchase_limit(connection, actor, *, value, expected_version, currency=None, ip_address='') -> dict:
    """Cria, altera ou remove (``value=None``) o limite da empresa do ator.

    A empresa vem do ATOR, nunca do payload: não há como apontar outra empresa.
    Não faz commit — o chamador confirma a transação.
    """
    ensure_permission(actor, PERM_PURCHASE_LIMITS_MANAGE)
    company_id = actor.get('company_id')
    if not company_id:
        raise ValueError(MSG_NO_COMPANY)
    if currency not in (None, '', CURRENCY):
        raise ValueError(MSG_INVALID_CURRENCY)
    new_value = parse_threshold_input(value)
    expected = _version_from_payload(expected_version)

    config = locked_purchase_config(connection, company_id)
    current_version = int(config.get(VERSION_KEY) or 0)
    if expected != current_version:
        raise PurchaseConflictError(
            'PURCHASE_LIMIT_VERSION_CONFLICT', MSG_VERSION_CONFLICT, details=describe(config),
        )
    old_value = read_threshold(config)
    if old_value == new_value:
        # Idempotente: reenvio do mesmo valor não gera versão nem evento novos.
        return {**describe(config), 'changed': False}

    now = datetime.now(UTC).isoformat()
    if new_value is None:
        config.pop(THRESHOLD_KEY, None)
        action = 'purchase_limit_removed'
    else:
        config[THRESHOLD_KEY] = format_threshold(new_value)
        action = 'purchase_limit_created' if old_value is None else 'purchase_limit_changed'
    config[VERSION_KEY] = current_version + 1
    config[UPDATED_AT_KEY] = now
    config[UPDATED_BY_KEY] = int(actor['id'])
    config[UPDATED_BY_NAME_KEY] = actor.get('full_name') or ''
    _store_config(connection, company_id, config)

    before = format_threshold(old_value) or ''
    after = format_threshold(new_value) or ''
    record_purchase_event(
        connection, int(company_id), 'company', int(company_id), action, before, after,
        f'Limite de alçada de PO ({CURRENCY}): {before or "não configurado"} → {after or "não configurado"}.',
        int(actor['id']), actor.get('full_name') or '', ip_address, actor.get('role') or '',
    )
    return {**describe(config), 'changed': True}
