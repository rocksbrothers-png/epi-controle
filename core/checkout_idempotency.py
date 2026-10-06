"""Idempotência do checkout Corporate (efeito externo no Mercado Pago).

Problema (confirmado na validação 1H-C da PR #1017; espelho do SaaS #392):
duas requisições concorrentes ou um retry após o MP já ter criado o preapproval
podiam gerar DOIS preapprovals — o `mp_client` usava `X-Idempotency-Key` com um
`uuid4()` NOVO a cada chamada, sem identidade estável da INTENÇÃO.

Mecanismo desta correção:
- O cliente envia um `idempotency_key` (nonce da INTENÇÃO) estável entre retries
  da MESMA intenção e novo para uma nova compra. Ele NÃO é autoridade (#1017):
  empresa/ator/preço/plano continuam server-side; o nonce só identifica a
  tentativa.
- `payment_attempts` registra cada intenção com UNIQUE(company_id,
  idempotency_key) — a atomicidade é do BANCO (não de lock em memória): sob
  concorrência, só um INSERT vence; os demais bloqueiam no índice e, ao final,
  reconciliam a tentativa já persistida. Sobrevive a threads/workers/processos/
  restarts.
- A chave enviada ao Mercado Pago é DERIVADA e NAMESPACED por empresa
  (`sha256("corp:{company_id}:{client_key}")`). O `X-Idempotency-Key` do MP é
  global à conta da plataforma; namespacing por empresa impede que a empresa B,
  reenviando a chave da empresa A, receba o preapproval de A (isolamento
  multi-tenant, #1009). É determinística: um retry recomputa a MESMA chave do MP
  (mesmo após rollback local), então o MP responde idempotentemente o mesmo
  preapproval — nunca um segundo.
- `fingerprint(payment_method, plan_key, cycle)` detecta reuso da MESMA chave
  para payload diferente → conflito (nunca reinterpretado como nova intenção).

Esta camada é identidade/recuperação de efeito externo — nunca autoridade.
"""

import hashlib
import json
from datetime import datetime, timezone

UTC = timezone.utc

# Nonce da intenção: opaco, limitado em tamanho, sem semântica de autoridade.
IDEMPOTENCY_KEY_MIN = 8
IDEMPOTENCY_KEY_MAX = 200

# Estados da tentativa. No caminho de uma transação única só existe linha
# COMMITada em 'persisted'; 'processing' vive apenas dentro da transação do
# vencedor (invisível aos concorrentes, que bloqueiam no índice UNIQUE).
STATUS_PROCESSING = 'processing'
STATUS_PERSISTED = 'persisted'


class IdempotencyError(ValueError):
    """`idempotency_key` ausente/ inválido → HTTP 400."""


class IdempotencyTransient(RuntimeError):
    """Corrida rara (vencedor reverteu entre o conflito e a releitura) → 503/retry."""


def _now_iso():
    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')


def validate_key(raw):
    """Normaliza/valida o nonce da intenção. Não é segredo; é identidade."""
    key = str(raw or '').strip()
    if not key:
        raise IdempotencyError('Campo obrigatório: idempotency_key')
    if len(key) < IDEMPOTENCY_KEY_MIN or len(key) > IDEMPOTENCY_KEY_MAX:
        raise IdempotencyError('idempotency_key com tamanho inválido.')
    # Caracteres de controle fora; mantém o nonce opaco e logável com segurança.
    if any(ord(c) < 0x20 for c in key):
        raise IdempotencyError('idempotency_key inválido.')
    return key


def fingerprint(payment_method, plan_key, cycle):
    """Impressão da INTENÇÃO (não inclui card_token: retokenizar a mesma intenção
    não é uma intenção nova). Usada para detectar reuso de chave com payload
    diferente (§18)."""
    base = f'{str(payment_method or "")}|{str(plan_key or "").strip().lower()}|{str(cycle or "").strip().lower()}'
    return hashlib.sha256(base.encode('utf-8')).hexdigest()


def mp_idempotency_key(company_id, client_key):
    """Chave enviada ao Mercado Pago (`X-Idempotency-Key`), DETERMINÍSTICA e
    NAMESPACED por empresa. Mesma intenção/retry → mesma chave (mesmo após
    rollback local) → MP responde o mesmo preapproval. Empresa distinta com o
    mesmo nonce → chave distinta → nunca recupera o preapproval de outra."""
    base = f'corp:{int(company_id) if company_id not in (None, "") else 0}:{str(client_key or "")}'
    return hashlib.sha256(base.encode('utf-8')).hexdigest()


def server_external_reference(company_id, plan_key, cycle, client_key):
    """`external_reference` server-controlled: identifica a intenção local de
    forma determinística e recuperável, sem dado sensível. O cliente nunca a
    informa."""
    tag = mp_idempotency_key(company_id, client_key)[:16]
    return f'checkout|company={company_id}|plan={plan_key}|cycle={cycle}|intent={tag}'


def ensure_payment_attempt_tables(connection):
    """Cria `payment_attempts` + o índice UNIQUE (idempotente; SQLite e Postgres).

    A garantia de unicidade é do índice no BANCO (§9). A RLS desta tabela
    multi-tenant é VERSIONADA na migration 029 (par .sql), seguindo o padrão das
    demais tabelas de billing (#309) — nada de DDL de RLS aqui."""
    connection.executescript(
        '''
        CREATE TABLE IF NOT EXISTS payment_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            idempotency_key TEXT NOT NULL DEFAULT '',
            actor_user_id INTEGER,
            payment_method TEXT NOT NULL DEFAULT '',
            plan_key TEXT NOT NULL DEFAULT '',
            cycle TEXT NOT NULL DEFAULT '',
            fingerprint TEXT NOT NULL DEFAULT '',
            external_reference TEXT NOT NULL DEFAULT '',
            mp_resource_type TEXT NOT NULL DEFAULT '',
            mp_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'processing',
            result_json TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_attempts_company_key
            ON payment_attempts(company_id, idempotency_key);
        CREATE INDEX IF NOT EXISTS idx_payment_attempts_mp ON payment_attempts(mp_id);
        '''
    )


def _is_unique_violation(exc):
    text = str(exc).upper()
    if 'UNIQUE CONSTRAINT FAILED' in text or 'DUPLICATE KEY' in text:
        return True
    if getattr(exc, 'pgcode', '') == '23505':
        return True
    return type(exc).__name__ == 'UniqueViolation'


def _row_to_attempt(row):
    if not row:
        return None
    # Acesso posicional compatível com sqlite3.Row e psycopg2 DictRow.
    keys = ('id', 'company_id', 'idempotency_key', 'actor_user_id', 'payment_method',
            'plan_key', 'cycle', 'fingerprint', 'external_reference', 'mp_resource_type',
            'mp_id', 'status', 'result_json', 'created_at', 'updated_at')
    return {k: row[i] for i, k in enumerate(keys)}


def find_attempt(connection, company_id, client_key):
    row = connection.execute(
        'SELECT id, company_id, idempotency_key, actor_user_id, payment_method, plan_key, '
        'cycle, fingerprint, external_reference, mp_resource_type, mp_id, status, result_json, '
        'created_at, updated_at FROM payment_attempts '
        'WHERE company_id = ? AND idempotency_key = ?',
        (int(company_id) if company_id not in (None, '') else None, str(client_key)),
    ).fetchone()
    return _row_to_attempt(row)


def claim(connection, *, company_id, client_key, fingerprint, actor_user_id,
          payment_method, plan_key, cycle, external_reference):
    """Reivindica a intenção atomicamente ou devolve a tentativa já existente.

    Retorna ('claimed', None) quando ESTE request venceu o INSERT (segue para o
    MP na MESMA transação), ou ('exists', attempt) quando a intenção já tem uma
    tentativa persistida (reconciliar/replay). A unicidade é imposta pelo índice
    UNIQUE: concorrentes bloqueiam nele e, ao final, caem em ('exists', …).
    """
    prior = find_attempt(connection, company_id, client_key)
    if prior:
        return ('exists', prior)
    now = _now_iso()
    try:
        connection.execute(
            '''
            INSERT INTO payment_attempts
                (company_id, idempotency_key, actor_user_id, payment_method, plan_key,
                 cycle, fingerprint, external_reference, mp_resource_type, mp_id,
                 status, result_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', '', ?, '', ?, ?)
            ''',
            (
                int(company_id) if company_id not in (None, '') else None,
                str(client_key), int(actor_user_id) if actor_user_id not in (None, '') else None,
                str(payment_method or ''), str(plan_key or ''), str(cycle or ''),
                str(fingerprint or ''), str(external_reference or ''),
                STATUS_PROCESSING, now, now,
            ),
        )
        return ('claimed', None)
    except Exception as exc:
        # Só tratamos a violação de unicidade (corrida perdida); o resto sobe.
        if not _is_unique_violation(exc):
            raise
        # Sai da transação abortada e relê a tentativa já COMMITada (os
        # concorrentes bloqueiam no índice até o vencedor commitar, então aqui
        # ela existe e está 'persisted'). Se o rollback falhasse, propagaria.
        connection.rollback()
        prior = find_attempt(connection, company_id, client_key)
        if prior:
            return ('exists', prior)
        # Raríssimo: o vencedor reverteu entre o conflito e a releitura.
        raise IdempotencyTransient('checkout em processamento; tente novamente.') from exc


def finalize(connection, *, company_id, client_key, status, mp_resource_type, mp_id, result):
    """Marca a tentativa como concluída e guarda o resultado para replay idempotente."""
    connection.execute(
        'UPDATE payment_attempts SET status = ?, mp_resource_type = ?, mp_id = ?, '
        'result_json = ?, updated_at = ? WHERE company_id = ? AND idempotency_key = ?',
        (
            str(status or STATUS_PERSISTED), str(mp_resource_type or ''), str(mp_id or ''),
            json.dumps(result or {}, ensure_ascii=False), _now_iso(),
            int(company_id) if company_id not in (None, '') else None, str(client_key),
        ),
    )


def stored_result(attempt):
    """Resultado persistido de uma tentativa concluída, para replay idempotente."""
    raw = (attempt or {}).get('result_json') or ''
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None
