"""Serviços de configurações (regras, framework, ficha)."""

import json
import secrets
from datetime import datetime, timezone

from epi_backend.http_utils import structured_log
from epi_backend.rule_engine import normalize_framework_payload

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
