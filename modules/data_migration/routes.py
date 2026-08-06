"""Rotas REST do Centro de Migração de Dados (ADR-0003).

Toda rota é gateada por ``data_migration:manage`` (só master_admin e
general_admin, ver core/permissions.py) E pelo módulo opt-in ``migracao``
habilitado para o tenant. O backend é a autoridade final — a UI só orienta
a navegação.

O conteúdo do arquivo trafega em base64 dentro do JSON: o servidor HTTP é o
da stdlib e não faz parsing de multipart. Para os volumes desta fase
(limite de 25 MB, ADR-0003 §7) é adequado; a Fase 4 (upload direto +
execução em background) troca isso por streaming.
"""

from __future__ import annotations

import base64
from contextlib import closing
from urllib.parse import parse_qs

from core.database import get_connection
from core.permissions import PERM_DATA_MIGRATION_MANAGE
from core.repository import authorize_action
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.data_migration.catalog import list_entities
from modules.data_migration.service import (
    analyze_source,
    fetch_job_records,
    fetch_jobs,
    get_job,
    load_saved_mapping,
    revert_job,
    run_migration,
)
from modules.data_migration.sources import list_sources
from modules.settings.service import ensure_module_enabled_for_unit


def _authorize(connection, handler, parsed, payload=None):
    """Gate único: permissão técnica + módulo opt-in habilitado.

    ``ensure_module_enabled_for_unit`` com ``unit_id=None`` é o mesmo gate
    real já usado por Terceirizados (ADR-0002 §11.2) — migração é operação
    de tenant inteiro, então nunca é escopada por unidade.
    """
    actor = authorize_action(
        connection, resolve_actor_user_id(handler, parsed, payload), PERM_DATA_MIGRATION_MANAGE,
    )
    ensure_module_enabled_for_unit(connection, actor, 'migracao', None)
    return actor


def _client_ip(handler) -> str:
    try:
        from core.rate_limit import get_client_ip
        return str(get_client_ip(handler) or '')
    except Exception:
        return ''


def _decode_content(payload: dict) -> bytes:
    raw = payload.get('content_base64') or payload.get('content')
    if not raw:
        raise ValueError('Conteúdo do arquivo é obrigatório (content_base64).')
    try:
        return base64.b64decode(str(raw), validate=True)
    except Exception as exc:
        raise ValueError('Conteúdo do arquivo não é base64 válido.') from exc


# ── Catálogo (dashboard com os cartões) ─────────────────────────────────────

def handle_get_migration_catalog(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        _authorize(connection, handler, parsed)
        return send_json(handler, 200, {
            'entities': list_entities(),
            'sources': list_sources(),
        })


# ── Etapas 3 e 4: leitura automática + mapeamento sugerido ──────────────────

def handle_post_migration_analyze(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'entity', 'source_kind'])
    with closing(get_connection()) as connection:
        actor = _authorize(connection, handler, parsed, payload)
        raw = _decode_content(payload)
        analysis = analyze_source(
            str(payload['source_kind']), raw, str(payload['entity']),
            sheet=payload.get('sheet') or None,
        )
        # Mapeamento já confirmado antes para este mesmo layout vence a
        # sugestão automática — é o ganho de produtividade da reimportação.
        saved = load_saved_mapping(
            connection, int(actor['company_id']), analysis['entity'], analysis['signature'],
        )
        if saved:
            analysis['mapping'] = saved
            analysis['mapping_source'] = 'saved'
        else:
            analysis['mapping_source'] = 'suggested'
        return send_json(handler, 200, analysis)


# ── Preview (dry-run) e execução ────────────────────────────────────────────

def handle_post_migration_run(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'entity', 'source_kind', 'mapping'])
    with closing(get_connection()) as connection:
        actor = _authorize(connection, handler, parsed, payload)
        raw = _decode_content(payload)
        result = run_migration(
            connection,
            company_id=int(actor['company_id']),
            entity=str(payload['entity']),
            source_kind=str(payload['source_kind']),
            raw=raw,
            mapping=payload.get('mapping') or {},
            strategy=str(payload.get('strategy') or 'dry_run'),
            actor=actor,
            source_name=str(payload.get('source_name') or ''),
            actor_ip=_client_ip(handler),
            sheet=payload.get('sheet') or None,
        )
        if result.get('applied'):
            from modules.companies.service import register_company_audit
            totals = result['totals']
            register_company_audit(
                connection, int(actor['company_id']), actor, 'data_migration_executed',
                f'Importação de {payload["entity"]}: {totals["inserted"]} inseridos, '
                f'{totals["updated"]} atualizados, {totals["skipped"]} ignorados, '
                f'{totals["failed"]} com erro.',
                {
                    'job_id': result['job_id'],
                    'entity': str(payload['entity']),
                    'source_kind': str(payload['source_kind']),
                    'strategy': result['strategy'],
                    'totals': totals,
                },
            )
            connection.commit()
        return send_json(handler, 200, result)


# ── Histórico e rollback ────────────────────────────────────────────────────

def handle_get_migration_jobs(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = _authorize(connection, handler, parsed)
        query = parse_qs(parsed.query)
        return send_json(handler, 200, {
            'jobs': fetch_jobs(
                connection, int(actor['company_id']),
                entity=str(query.get('entity', [''])[0]).strip(),
                limit=min(int(query.get('limit', ['50'])[0] or 50), 200),
            ),
        })


def handle_get_migration_job(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = _authorize(connection, handler, parsed)
        job_id = int(match.group(1))
        job = get_job(connection, job_id, int(actor['company_id']))
        if not job:
            return send_json(handler, 404, {'error': 'Importação não encontrada.'})
        return send_json(handler, 200, {
            'job': job,
            'records': fetch_job_records(connection, job_id, int(actor['company_id'])),
        })


def handle_post_migration_revert(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = _authorize(connection, handler, parsed, payload)
        job_id = int(match.group(1))
        result = revert_job(connection, job_id, int(actor['company_id']), actor)
        from modules.companies.service import register_company_audit
        register_company_audit(
            connection, int(actor['company_id']), actor, 'data_migration_reverted',
            f'Importação #{job_id} revertida: {result["deleted"]} removidos, '
            f'{result["restored"]} restaurados.',
            {'job_id': job_id, **result},
        )
        connection.commit()
        return send_json(handler, 200, result)


def register_routes(router):
    router.register('GET',  '/api/data-migration/catalog',                 handle_get_migration_catalog)
    router.register('GET',  '/api/data-migration/jobs',                    handle_get_migration_jobs)
    router.register('GET',  r'^/api/data-migration/jobs/(\d+)$',           handle_get_migration_job, regex=True)
    router.register('POST', '/api/data-migration/analyze',                 handle_post_migration_analyze)
    router.register('POST', '/api/data-migration/run',                     handle_post_migration_run)
    router.register('POST', r'^/api/data-migration/jobs/(\d+)/revert$',    handle_post_migration_revert, regex=True)
