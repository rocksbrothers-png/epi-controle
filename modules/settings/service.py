"""Serviços de configurações (regras, framework, ficha)."""

import json
import json as _json
import secrets
from datetime import datetime, timezone

from epi_backend.http_utils import structured_log
from epi_backend.http_utils import structured_log as _structured_log
from epi_backend.rule_engine import SUPPORTED_EXECUTION_MODES, normalize_framework_payload
from epi_backend.rule_engine import (
    build_context as build_rule_context,
    compute_visibility_diff,
    resolve_execution_plan,
    resolve_visibility_filters,
)

from core.meta import get_meta, set_meta

UTC = timezone.utc

DEFAULT_FICHA_TITULO = 'FICHA INDIVIDUAL DE CONTROLE DE EPI (Equipamento de Proteção Individual) E UNIFORMES'
DEFAULT_FICHA_DECLARACAO = (
    'Declaro que recebi os EPIs e uniformes abaixo discriminados, gratuitamente, para uso individual '
    'durante a jornada de trabalho, pelos quais fico responsável pela guarda e conservação, devendo '
    'devolvê-los quando houver alteração que os torne impróprios para uso ou na rescisão do contrato '
    'de trabalho.\nDeclaro ainda que fui treinado no procedimento de Uso Correto e Cuidados com os EPI.\n'
    'Estou ciente de que estarei sujeito a desconto em folha ou na rescisão se eventualmente vier a '
    'provocar danos, modificar ou extraviar os EPIs e de que a recusa injustificada em usar os EPIs '
    'ora fornecidos pela empresa constitui ato faltoso, podendo sofrer as penalidades previstas na Lei.'
)
DEFAULT_FICHA_OBSERVACOES = (
    'OBS.: Cada EPI tem um prazo de validade que se encontra na embalagem, assim como a vida Útil do '
    'mesmo que pode ser encontrado no próprio EPI ou na embalagem.'
)
DEFAULT_FICHA_RASTREABILIDADE = 'Ficha Individual de Controle de EPI - Ver. 01'


def get_ficha_config(connection, company_id):
    normalized_company_id = None if company_id in (None, '', 'null') else int(company_id)
    if normalized_company_id is None:
        return {
            'titulo': DEFAULT_FICHA_TITULO,
            'declaracao': DEFAULT_FICHA_DECLARACAO,
            'observacoes': DEFAULT_FICHA_OBSERVACOES,
            'rastreabilidade': DEFAULT_FICHA_RASTREABILIDADE,
        }
    try:
        row = connection.execute(
            'SELECT titulo, declaracao, observacoes, rastreabilidade FROM ficha_epi_config WHERE company_id = ?',
            (normalized_company_id,),
        ).fetchone()
        if row:
            return {
                'titulo': row['titulo'] or DEFAULT_FICHA_TITULO,
                'declaracao': row['declaracao'] or DEFAULT_FICHA_DECLARACAO,
                'observacoes': row['observacoes'] or DEFAULT_FICHA_OBSERVACOES,
                'rastreabilidade': row['rastreabilidade'] or DEFAULT_FICHA_RASTREABILIDADE,
            }
    except Exception as _e:
        structured_log('warning', 'ficha.config_load_error', error=str(_e))
    return {
        'titulo': DEFAULT_FICHA_TITULO,
        'declaracao': DEFAULT_FICHA_DECLARACAO,
        'observacoes': DEFAULT_FICHA_OBSERVACOES,
        'rastreabilidade': DEFAULT_FICHA_RASTREABILIDADE,
    }


def save_ficha_config(connection, company_id, payload):
    normalized_company_id = None if company_id in (None, '', 'null') else int(company_id)
    if normalized_company_id is None:
        raise ValueError('Configuração da ficha exige empresa vinculada.')
    now = datetime.now(UTC).isoformat()
    titulo = str(payload.get('titulo') or DEFAULT_FICHA_TITULO).strip()
    declaracao = str(payload.get('declaracao') or DEFAULT_FICHA_DECLARACAO).strip()
    observacoes = str(payload.get('observacoes') or DEFAULT_FICHA_OBSERVACOES).strip()
    rastreabilidade = str(payload.get('rastreabilidade') or DEFAULT_FICHA_RASTREABILIDADE).strip()
    existing = connection.execute(
        'SELECT id FROM ficha_epi_config WHERE company_id = ?',
        (normalized_company_id,),
    ).fetchone()
    if existing:
        connection.execute(
            'UPDATE ficha_epi_config SET titulo=?, declaracao=?, observacoes=?, rastreabilidade=?, updated_at=? WHERE company_id=?',
            (titulo, declaracao, observacoes, rastreabilidade, now, normalized_company_id),
        )
    else:
        connection.execute(
            'INSERT INTO ficha_epi_config (company_id, titulo, declaracao, observacoes, rastreabilidade, created_at, updated_at) VALUES (?,?,?,?,?,?,?)',
            (normalized_company_id, titulo, declaracao, observacoes, rastreabilidade, now, now),
        )
    connection.commit()


def _configuration_scope_key(company_id):
    if company_id in (None, '', 'null'):
        return 'global'
    return str(int(company_id))


def _configuration_scope_unit_ids(connection, company_id):
    if company_id in (None, '', 'null'):
        return set()
    normalized_company_id = int(company_id)
    return {
        int(row['id'])
        for row in connection.execute(
            'SELECT id FROM units WHERE company_id = ?',
            (normalized_company_id,),
        ).fetchall()
    }


def get_configuration_rules(connection, company_id):
    default_rules = []
    scope_key = _configuration_scope_key(company_id)
    raw = get_meta(connection, f'configuration_rules:{scope_key}')
    if not raw:
        return default_rules
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except Exception as _e:
        structured_log('warning', 'configuration.rules_load_error', error=str(_e), scope_key=scope_key)
    return default_rules


def get_configuration_framework(connection, company_id):
    scope_key = _configuration_scope_key(company_id)
    raw = get_meta(connection, f'configuration_framework:{scope_key}')
    payload = {}
    if raw:
        try:
            payload = json.loads(raw)
        except Exception as _e:
            structured_log('warning', 'configuration.framework_load_error', error=str(_e), scope_key=scope_key)
    normalized = normalize_framework_payload(payload)
    if not normalized.get('visibility_rules'):
        normalized['visibility_rules'] = get_configuration_rules(connection, company_id)
    return normalized


def promote_rule_engine(connection, company_id, *, mode, rollout_percentage, enable=True):
    """Patch only execution_mode/rollout_percentage/enable_new_rules_engine in the framework.

    Simpler than save_configuration_framework — callers don't need the full JSON.
    Returns the updated framework.
    """
    mode = str(mode or 'off').lower()
    if mode not in SUPPORTED_EXECUTION_MODES:
        raise ValueError(f'execution_mode inválido: {mode!r}. Use: {SUPPORTED_EXECUTION_MODES}')
    rollout = int(rollout_percentage or 0)
    if not (0 <= rollout <= 100):
        raise ValueError('rollout_percentage deve ser entre 0 e 100.')
    framework = get_configuration_framework(connection, company_id)
    framework['feature_flags']['enable_new_rules_engine'] = bool(enable)
    framework['feature_flags']['execution_mode'] = mode
    framework['feature_flags']['rollout_percentage'] = rollout
    scope_key = _configuration_scope_key(company_id)
    set_meta(connection, f'configuration_framework:{scope_key}', json.dumps(framework, ensure_ascii=False))
    return framework


def get_rule_engine_status(connection, company_id):
    """Return current engine mode + recent shadow diff summary."""
    framework = get_configuration_framework(connection, company_id)
    flags = framework.get('feature_flags', {})
    summary = {'total': 0, 'diff_count': 0, 'no_diff_count': 0}
    try:
        rows = connection.execute(
            'SELECT has_diff, COUNT(*) AS cnt FROM rule_engine_shadow_log '
            'WHERE company_id = ? GROUP BY has_diff',
            (int(company_id),),
        ).fetchall()
        for row in rows:
            cnt = int(row['cnt'])
            summary['total'] += cnt
            if int(row['has_diff']):
                summary['diff_count'] += cnt
            else:
                summary['no_diff_count'] += cnt
    except Exception:
        pass
    return {
        'enabled': bool(flags.get('enable_new_rules_engine', False)),
        'mode': str(flags.get('execution_mode', 'off')),
        'rollout_percentage': int(flags.get('rollout_percentage', 0)),
        'shadow_log': summary,
    }


def save_configuration_framework(connection, company_id, payload):
    scope_key = _configuration_scope_key(company_id)
    normalized = normalize_framework_payload(payload if isinstance(payload, dict) else {})
    valid_unit_ids = _configuration_scope_unit_ids(connection, company_id)
    valid_roles = {'user', 'employee'}
    cleaned_rules = []
    for rule in normalized.get('visibility_rules', []):
        role = str(rule.get('role') or '').strip()
        unit_id = int(rule.get('unit_id') or 0)
        if role not in valid_roles:
            continue
        if unit_id and unit_id not in valid_unit_ids:
            continue
        cleaned_rules.append(rule)
    normalized['visibility_rules'] = cleaned_rules
    set_meta(connection, f'configuration_framework:{scope_key}', json.dumps(normalized, ensure_ascii=False))
    set_meta(connection, f'configuration_rules:{scope_key}', json.dumps(cleaned_rules, ensure_ascii=False))
    connection.commit()
    return normalized


def save_configuration_rules(connection, company_id, rules):
    sanitized = []
    scope_key = _configuration_scope_key(company_id)
    valid_roles = {'user', 'employee'}
    valid_unit_ids = _configuration_scope_unit_ids(connection, company_id)
    for item in rules or []:
        if not isinstance(item, dict):
            continue
        unit_id = int(item.get('unit_id') or 0)
        if unit_id and unit_id not in valid_unit_ids:
            structured_log(
                'warning',
                'configuration.rules_invalid_unit_fallback',
                scope_key=scope_key,
                unit_id=unit_id,
                rule_id=str(item.get('id') or ''),
            )
            continue
        role = str(item.get('role') or '').strip()
        if role not in valid_roles:
            structured_log(
                'warning',
                'configuration.rules_invalid_role_fallback',
                scope_key=scope_key,
                role=role,
                rule_id=str(item.get('id') or ''),
            )
            continue
        sanitized.append({
            'id': str(item.get('id') or secrets.token_hex(6)),
            'role': role,
            'unit_id': unit_id,
            'unit_context': 'inside_jv' if str(item.get('unit_context') or '') == 'inside_jv' else 'outside_jv',
            'can_view_unit': bool(item.get('can_view_unit')),
            'can_view_epis': bool(item.get('can_view_epis')),
            'can_view_employees': bool(item.get('can_view_employees')),
        })
    set_meta(connection, f'configuration_rules:{scope_key}', json.dumps(sanitized, ensure_ascii=False))
    framework = get_configuration_framework(connection, company_id)
    framework['visibility_rules'] = sanitized
    set_meta(connection, f'configuration_framework:{scope_key}', json.dumps(framework, ensure_ascii=False))
    connection.commit()
    return sanitized


def default_ficha_retention_policy():
    return {
        'retention_years': 5,
        'purge_enabled': False,
        'timeline': [
            {'stage': 'snapshot_generated', 'label': 'Fechamento / snapshot gerado'},
            {'stage': 'years_1_2', 'label': 'Ano 1-2: retenção ativa'},
            {'stage': 'years_3_4', 'label': 'Ano 3-4: auditoria legal'},
            {'stage': 'year_5', 'label': '5 anos: expiração NR-6'},
            {'stage': 'purge', 'label': 'Purge automático (se habilitado)'},
        ],
    }


def get_ficha_retention_policy(connection, company_id):
    policy = default_ficha_retention_policy()
    scope_key = _configuration_scope_key(company_id)
    raw = get_meta(connection, f'ficha_retention_policy:{scope_key}')
    if not raw:
        return policy
    try:
        parsed = json.loads(raw)
    except Exception as exc:
        structured_log('warning', 'ficha.retention_policy_parse_error', error=str(exc), scope_key=scope_key)
        return policy
    retention_years = int(parsed.get('retention_years') or policy['retention_years'])
    purge_enabled = bool(parsed.get('purge_enabled'))
    policy['retention_years'] = max(1, min(retention_years, 15))
    policy['purge_enabled'] = purge_enabled
    return policy


def save_ficha_retention_policy(connection, company_id, payload):
    scope_key = _configuration_scope_key(company_id)
    current = get_ficha_retention_policy(connection, company_id)
    retention_years = int(payload.get('retention_years') or current['retention_years'])
    purge_enabled = bool(payload.get('purge_enabled'))
    normalized = default_ficha_retention_policy()
    normalized['retention_years'] = max(1, min(retention_years, 15))
    normalized['purge_enabled'] = purge_enabled
    set_meta(connection, f'ficha_retention_policy:{scope_key}', json.dumps(normalized, ensure_ascii=False))
    connection.commit()
    return normalized


def canary_evaluate_visibility_dataset(connection, actor, *, endpoint_name, dataset_name, legacy_items):
    """Run legacy/new engine in parallel. Returns candidate_items when mode=enforced, else legacy_items."""
    try:
        framework = get_configuration_framework(connection, actor['company_id'])
        context = build_rule_context(actor, endpoint=endpoint_name)
        plan = resolve_execution_plan(context, framework)
        if not plan.get('evaluate_in_background'):
            return legacy_items

        def item_unit_id(item):
            return int(
                item.get('unit_id')
                or item.get('current_unit_id')
                or 0
            )

        def item_context(item):
            return 'inside_jv' if str(item.get('active_joinventure') or '').strip() else 'outside_jv'

        candidate_items = []
        for item in legacy_items:
            item_ctx = build_rule_context(
                actor,
                endpoint=endpoint_name,
                unit_id=item_unit_id(item) or None,
                jv_context=item_context(item),
            )
            visibility = resolve_visibility_filters(item_ctx, framework)
            if dataset_name == 'units' and visibility.get('allow_unit', True):
                candidate_items.append(item)
            elif dataset_name == 'employees' and visibility.get('allow_employees', True):
                candidate_items.append(item)
            elif dataset_name == 'epis' and visibility.get('allow_epis', True):
                candidate_items.append(item)
            elif dataset_name not in ('units', 'employees', 'epis'):
                candidate_items.append(item)

        legacy_ids = [str(item.get('id') or item.get('employee_id_code') or '') for item in legacy_items]
        candidate_ids = [str(item.get('id') or item.get('employee_id_code') or '') for item in candidate_items]
        diff = compute_visibility_diff(legacy_ids, candidate_ids)

        log_payload = {
            'company_id': int(actor.get('company_id') or 0),
            'user_id': int(actor.get('id') or 0),
            'role': str(actor.get('role') or ''),
            'endpoint': endpoint_name,
            'dataset': dataset_name,
            'mode': plan.get('mode'),
            'legacy_count': len(legacy_items),
            'new_count': len(candidate_items),
            'diff': diff,
        }
        if diff.get('has_diff'):
            _structured_log('warning', 'rules_engine.shadow_diff_detected', **log_payload)
        else:
            _structured_log('info', 'rules_engine.shadow_diff_none', **log_payload)

        try:
            from datetime import datetime, timezone as _tz
            connection.execute(
                'INSERT INTO rule_engine_shadow_log '
                '(company_id, user_id, role, endpoint, dataset, mode, legacy_count, new_count, has_diff, legacy_only, new_only, created_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    int(actor.get('company_id') or 0),
                    int(actor.get('id') or 0),
                    str(actor.get('role') or ''),
                    endpoint_name,
                    dataset_name,
                    str(plan.get('mode') or 'shadow'),
                    len(legacy_items),
                    len(candidate_items),
                    1 if diff.get('has_diff') else 0,
                    _json.dumps(diff.get('legacy_only', [])),
                    _json.dumps(diff.get('new_only', [])),
                    datetime.now(_tz.utc).isoformat(),
                ),
            )
            connection.commit()
        except Exception:
            pass

        if not plan.get('legacy_is_source_of_truth'):
            return candidate_items
    except Exception as exc:
        _structured_log(
            'warning',
            'rules_engine.shadow_failed_fallback_legacy',
            company_id=int(actor.get('company_id') or 0),
            user_id=int(actor.get('id') or 0),
            role=str(actor.get('role') or ''),
            endpoint=endpoint_name,
            dataset=dataset_name,
            error=str(exc),
        )
    return legacy_items


# ── Route-level SQL extractions ───────────────────────────────────────────────

def delete_shadow_log(connection, company_id):
    connection.execute('DELETE FROM rule_engine_shadow_log WHERE company_id = ?', (int(company_id),))


def fetch_shadow_log(connection, company_id, limit):
    import json as _json
    rows = connection.execute(
        'SELECT id, company_id, user_id, role, endpoint, dataset, mode, '
        'legacy_count, new_count, has_diff, legacy_only, new_only, created_at '
        'FROM rule_engine_shadow_log '
        'WHERE company_id = ? '
        'ORDER BY id DESC LIMIT ?',
        (int(company_id), int(limit)),
    ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d['legacy_only'] = _json.loads(d.get('legacy_only') or '[]')
        d['new_only'] = _json.loads(d.get('new_only') or '[]')
        d['has_diff'] = bool(d['has_diff'])
        items.append(d)
    return items
