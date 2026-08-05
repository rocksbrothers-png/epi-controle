"""Serviços de configurações (regras, framework, ficha)."""

import json
import json as _json
import secrets
from datetime import datetime, timezone

from epi_backend.http_utils import structured_log
from epi_backend.http_utils import structured_log as _structured_log
from epi_backend.rule_engine import SUPPORTED_EXECUTION_MODES, normalize_framework_payload
from epi_backend.rule_engine import (
    MODULE_KEYS,
    _DEFAULT_UNIT_BUCKET,
    _UNIT_SCOPED_ROLES,
    build_context as build_rule_context,
    compute_visibility_diff,
    resolve_execution_plan,
    resolve_module_visibility,
    resolve_visibility_filters,
)

from core.meta import get_meta, set_meta
from core.permissions import PERMISSIONS
from epi_backend.db import row_to_dict

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


# ── Visibilidade estrutural por módulo (menu/rotas/deep links) ────────────
# Reaproveita o mesmo armazenamento do framework (`configuration_framework:
# {scope_key}`, aba "Configuração → Regras → Visualização") — não é uma
# tabela nova. A regra padrão do sistema vem de
# rule_engine.default_framework_payload()["module_visibility"]; o que é
# salvo aqui é só o override por tenant (e, para admin/user, por Unidade),
# mesclado por normalize_framework_payload(). resolve_module_visibility()
# ainda reclampa pela permissão técnica do ator — esta camada nunca amplia
# o que o backend autoriza. module_visibility é a ÚNICA fonte de verdade
# para tenant+perfil+unidade+módulo — não existe mais um module_unit_scope
# separado (aposentado; normalize_framework_payload converte automaticamente
# qualquer configuração antiga que ainda o contenha).

def get_module_visibility_config(connection, company_id):
    """Configuração de visibilidade por módulo — {role: {"*"|unit_id:
    {module: bool}}}, já mesclada com o padrão do sistema. Usada pela tela
    de administração (para exibir o estado atual) e por
    get_effective_module_visibility."""
    framework = get_configuration_framework(connection, company_id)
    return framework.get('module_visibility', {})


def get_effective_module_visibility(connection, actor, unit_id=None):
    """Visibilidade efetiva de cada módulo para o ator autenticado: config
    (padrão + override do tenant, por perfil e — para admin/user — por
    Unidade) AND permissão técnica. É isto que entra no /api/bootstrap (e
    no login/`auth/me`) para orientar menu/rotas no Flutter e no web
    legado — a autorização real de dados continua nas rotas, inalterada.

    `unit_id`: unidade operacional do ator, só relevante para
    Administrador Local/Gestor de EPI (resolve_module_visibility só a usa
    para papéis em _UNIT_SCOPED_ROLES — todo módulo suporta override por
    Unidade, não só um subconjunto fixo). O chamador
    (modules.auth.service/routes) já resolve isso via
    modules.employees.service.actor_operational_unit_id — não é recalculado
    aqui para não importar modules.employees.service a partir deste módulo
    (modules.employees.service importa modules.outsourced_companies.service,
    que já importa modules.settings.service: fechar esse ciclo aqui criaria
    um import circular entre os três).

    Camada só-UI: se a leitura da configuração falhar (ex.: schema ainda
    não migrado), cai para a regra padrão do sistema (sem override de
    tenant) em vez de derrubar o login/bootstrap por causa de um recurso
    não-crítico.
    """
    company_id = actor.get('company_id')
    try:
        framework = get_configuration_framework(connection, company_id)
    except Exception as exc:
        structured_log('warning', 'configuration.module_visibility_load_error', error=str(exc))
        framework = normalize_framework_payload({})
    context = build_rule_context(actor, unit_id=unit_id)
    granted = PERMISSIONS.get(str(actor.get('role') or ''), frozenset())
    return resolve_module_visibility(context, framework, granted)


def ensure_module_enabled_for_unit(connection, actor, module, unit_id):
    """Autoridade no BACKEND para módulos escopáveis por Unidade: mesmo com
    o menu oculto no Flutter/web legado, nenhuma rota de escrita pode
    confiar só na UI. Levanta PermissionError se o módulo não está
    habilitado (config do Administrador Geral, por perfil e por Unidade) —
    reusa integralmente get_effective_module_visibility/
    resolve_module_visibility, sem mecanismo novo.
    """
    effective = get_effective_module_visibility(connection, actor, unit_id=unit_id)
    if not effective.get(module, False):
        raise PermissionError(
            f'Módulo "{module}" não autorizado para o seu perfil/unidade. '
            'Peça ao Administrador Geral para habilitar o acesso.'
        )


def save_module_visibility(connection, company_id, role, updates, unit_id=None):
    """Grava o override de visibilidade de módulos para um perfil — no
    bucket "*" (padrão do perfil, toda unidade) quando `unit_id` é
    omitido, ou no bucket daquela Unidade especificamente quando
    informado (só válido para papéis em _UNIT_SCOPED_ROLES — admin/user;
    os demais não são escopados por unidade em nenhum outro fluxo do
    sistema). Retorna (before, after) só dos módulos alterados — usado
    para auditoria (core.audit.register_company_audit).
    """
    role = str(role or '').strip()
    if role not in PERMISSIONS:
        raise ValueError(f'Perfil inválido: {role!r}.')
    if not isinstance(updates, dict) or not updates:
        raise ValueError('Informe ao menos um módulo para atualizar.')
    unit_bucket = _DEFAULT_UNIT_BUCKET
    if unit_id not in (None, '', 0, '0'):
        if role not in _UNIT_SCOPED_ROLES:
            raise ValueError(f'Perfil {role!r} não é escopado por Unidade — grave sem unit_id.')
        unit_id = int(unit_id)
        if unit_id not in _configuration_scope_unit_ids(connection, company_id):
            raise ValueError('Unidade informada não pertence a este tenant.')
        unit_bucket = str(unit_id)
    scope_key = _configuration_scope_key(company_id)
    framework = get_configuration_framework(connection, company_id)
    role_config = framework.setdefault('module_visibility', {}).setdefault(role, {})
    bucket_visibility = dict(role_config.get(unit_bucket, {}))
    base_visibility = role_config.get(_DEFAULT_UNIT_BUCKET, {})
    before = {}
    after = {}
    for module, value in updates.items():
        module = str(module or '').strip()
        if module not in MODULE_KEYS:
            continue
        # "before" é o valor EFETIVO (com fallback para "*" quando o bucket
        # da Unidade ainda não tem override daquele módulo) — mais útil para
        # auditoria do que mostrar sempre False para um módulo nunca
        # sobrescrito naquela Unidade.
        if module in bucket_visibility:
            before[module] = bool(bucket_visibility[module])
        else:
            before[module] = bool(base_visibility.get(module, False))
        bucket_visibility[module] = bool(value)
        after[module] = bool(value)
    if not before:
        raise ValueError('Nenhum módulo reconhecido em: ' + ', '.join(sorted(updates.keys())))
    role_config[unit_bucket] = bucket_visibility
    normalized = normalize_framework_payload(framework)
    set_meta(connection, f'configuration_framework:{scope_key}', json.dumps(normalized, ensure_ascii=False))
    connection.commit()
    return before, after


def _module_visibility_needs_migration(payload):
    """True quando `payload` (config_framework bruto, como armazenado em
    app_meta) ainda tem algum vestígio do modelo legado: module_unit_scope
    separado, ou module_visibility no formato plano {role: {module: bool}}
    (sem bucket de Unidade)."""
    if isinstance(payload.get('module_unit_scope'), dict) and payload['module_unit_scope']:
        return True
    for role_config in (payload.get('module_visibility') or {}).values():
        if isinstance(role_config, dict) and any(isinstance(v, bool) for v in role_config.values()):
            return True
    return False


def migrate_module_visibility_unit_model(connection):
    """Migration idempotente: converte todo `configuration_framework:*`
    guardado em `app_meta` (um por tenant + o escopo global do Admin
    Master) do modelo legado (module_visibility plano por perfil +
    module_unit_scope separado, {module: [unit_id, ...]}) para o modelo
    único (module_visibility com override por Unidade — "*" = padrão do
    perfil, "<unit_id>" = override, um bucket por módulo). Mesma conversão
    que epi_backend.rule_engine.normalize_framework_payload já faz em
    memória a cada leitura; esta função persiste o resultado de volta, para
    o armazenamento em si parar de carregar os dois formatos.

    Preserva integralmente o comportamento observável: um módulo com
    restrição ativa (allowlist não vazia) vira `"*": {module: False}` +
    `"<unit_id>": {module: True}` para cada unidade antes autorizada — as
    demais unidades continuam vendo False, exatamente como antes.

    Idempotente: linhas já no formato novo (sem module_unit_scope e sem
    nenhum module_visibility plano) não são regravadas.
    """
    rows = connection.execute(
        "SELECT key, value FROM app_meta WHERE key LIKE 'configuration_framework:%'"
    ).fetchall()
    for row in rows:
        item = row_to_dict(row)
        key = str(item.get('key') or '')
        if not key:
            continue
        try:
            payload = json.loads(item.get('value') or '{}')
        except (TypeError, ValueError):
            continue
        if not isinstance(payload, dict) or not _module_visibility_needs_migration(payload):
            continue
        normalized = normalize_framework_payload(payload)
        set_meta(connection, key, json.dumps(normalized, ensure_ascii=False))
    connection.commit()


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

def fetch_shadow_log_health(connection, company_id, window_hours=48):
    """Return health summary for the last window_hours hours of shadow log activity."""
    from datetime import datetime, timezone as _tz, timedelta
    cutoff = (datetime.now(_tz.utc) - timedelta(hours=int(window_hours))).isoformat()
    rows = connection.execute(
        'SELECT has_diff, COUNT(*) AS cnt FROM rule_engine_shadow_log '
        'WHERE company_id = ? AND created_at >= ? GROUP BY has_diff',
        (int(company_id), cutoff),
    ).fetchall()
    total = 0
    diff_count = 0
    for row in rows:
        cnt = int(row['cnt'])
        total += cnt
        if int(row['has_diff']):
            diff_count += cnt
    is_clean = diff_count == 0
    return {
        'window_hours': int(window_hours),
        'total': total,
        'diff_count': diff_count,
        'no_diff_count': total - diff_count,
        'is_clean': is_clean,
        'go_live_ready': is_clean and total > 0,
    }


def cleanup_shadow_log_older_than(connection, company_id, days_old):
    """Delete rule_engine_shadow_log entries older than days_old days. Returns deleted row count."""
    from datetime import datetime, timezone as _tz, timedelta
    cutoff = (datetime.now(_tz.utc) - timedelta(days=int(days_old))).isoformat()
    cursor = connection.execute(
        'DELETE FROM rule_engine_shadow_log WHERE company_id = ? AND created_at < ?',
        (int(company_id), cutoff),
    )
    return int(cursor.rowcount or 0)


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
