"""Serviços de "Minha Empresa" — configuração da própria tenant pelo Administrador Geral.

O Administrador Geral (Owner da tenant) edita apenas os campos cadastrais,
de identidade visual, tema, domínio e preferências da própria empresa.
Campos estruturais da assinatura (plano, limites, licença, status financeiro)
permanecem exclusivos do Administrador Master e nunca entram no whitelist.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from epi_backend.db import row_to_dict

UTC = timezone.utc

# Campos que o Administrador Geral pode alterar na própria empresa.
# Tudo que estiver fora desta lista é ignorado no update (defesa por whitelist):
# tenant/company id, plano, limites, licença, status financeiro e módulos
# jamais são graváveis por este módulo.
PROFILE_EDITABLE_FIELDS: tuple[str, ...] = (
    # Dados cadastrais
    'name', 'legal_name', 'cnpj',
    'state_registration', 'municipal_registration', 'address',
    'contact_phone', 'whatsapp', 'contact_email', 'website',
    # Identidade visual
    'logo_type', 'favicon_type', 'login_logo_type',
    'display_name', 'institutional_message',
    # Tema
    'theme_json', 'primary_color', 'secondary_color', 'accent_color',
    # Domínio
    'slug', 'subdomain', 'custom_domain',
    # Preferências
    'default_language', 'timezone',
    # Estrutura empresarial (Multi-CNPJ / Joint Venture)
    'org_structure_type', 'stock_control_scope',
)

# Campos somente-leitura expostos no perfil (controlados pelo Administrador Master).
PROFILE_READONLY_FIELDS: tuple[str, ...] = (
    'id', 'plan_name', 'user_limit', 'license_status', 'active',
    'contract_start', 'contract_end', 'monthly_value', 'addendum_enabled',
    'onboarding_completed', 'onboarding_completed_at',
)

_FIELD_LABELS: dict[str, str] = {
    'name': 'Nome fantasia',
    'legal_name': 'Razão social',
    'cnpj': 'CNPJ',
    'state_registration': 'Inscrição estadual',
    'municipal_registration': 'Inscrição municipal',
    'address': 'Endereço',
    'contact_phone': 'Telefone',
    'whatsapp': 'WhatsApp',
    'contact_email': 'E-mail institucional',
    'website': 'Website',
    'logo_type': 'Logotipo',
    'favicon_type': 'Favicon',
    'login_logo_type': 'Imagem da tela de login',
    'display_name': 'Nome exibido no sistema',
    'institutional_message': 'Mensagem institucional',
    'theme_json': 'Tema',
    'primary_color': 'Cor principal',
    'secondary_color': 'Cor secundária',
    'accent_color': 'Cor de destaque',
    'slug': 'Slug',
    'subdomain': 'Subdomínio',
    'custom_domain': 'Domínio personalizado',
    'default_language': 'Idioma',
    'timezone': 'Fuso horário',
    'org_structure_type': 'Estrutura organizacional',
    'stock_control_scope': 'Consolidação de saldos de estoque por',
}

# Campos com payload de imagem (auditados como "[imagem]" para não inflar o log).
_IMAGE_FIELDS = ('logo_type', 'favicon_type', 'login_logo_type')

_TIMEZONE_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_+\-]*(/[A-Za-z0-9_+\-]+){0,3}$')
_DOMAIN_RE = re.compile(r'^(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$')
_SUBDOMAIN_RE = re.compile(r'^(?!-)[a-z0-9-]{1,63}(?<!-)$')


def get_my_company_profile(connection, company_id: int) -> dict:
    """Perfil completo da própria empresa (campos editáveis + somente-leitura)."""
    row = connection.execute(
        'SELECT * FROM companies WHERE id = ?', (int(company_id),)
    ).fetchone()
    if not row:
        raise ValueError('Empresa não encontrada.')
    data = row_to_dict(row)
    profile = {field: data.get(field) for field in PROFILE_READONLY_FIELDS}
    for field in PROFILE_EDITABLE_FIELDS:
        profile[field] = data.get(field)
    return profile


def _validate_timezone(value: str) -> str:
    tz = str(value or '').strip()
    if not tz:
        return 'America/Sao_Paulo'
    if not _TIMEZONE_RE.match(tz):
        raise ValueError(f"Fuso horário inválido: '{tz}'. Use o formato IANA (ex.: America/Sao_Paulo).")
    return tz


def _validate_subdomain(value: str) -> str | None:
    sub = str(value or '').strip().lower()
    if not sub:
        return None
    if not _SUBDOMAIN_RE.match(sub):
        raise ValueError(
            f"Subdomínio inválido: '{sub}'. Use apenas letras minúsculas, números e hífens."
        )
    return sub


def _validate_custom_domain(value: str) -> str | None:
    domain = str(value or '').strip().lower()
    if not domain:
        return None
    if not _DOMAIN_RE.match(domain):
        raise ValueError(f"Domínio personalizado inválido: '{domain}'.")
    return domain


def ensure_tenant_routing_unique(connection, field: str, value: str | None, company_id: int) -> None:
    """Garante associação única de slug/subdomínio/domínio com uma única tenant."""
    if not value:
        return
    row = connection.execute(
        f'SELECT id FROM companies WHERE {field} = ? AND id != ?',  # noqa: S608 — field é constante interna
        (value, int(company_id)),
    ).fetchone()
    if row:
        label = _FIELD_LABELS.get(field, field)
        raise ValueError(f"{label} '{value}' já está em uso por outra empresa.")


def validate_my_company_payload(connection, payload: dict, company_id: int, previous: dict) -> dict:
    """Valida e normaliza um update parcial da própria empresa.

    Retorna somente os campos do whitelist presentes no payload, já validados.
    Campos ausentes não são alterados (update parcial, usado pelo assistente
    de implantação etapa a etapa).
    """
    from modules.commercial.service import (
        validate_cnpj,
        validate_login_logo_payload,
        validate_logo_payload,
    )
    from modules.companies.service import (
        _validate_color,
        _validate_language,
        ensure_unique_company_cnpj,
    )
    from modules.tenant.service import ensure_slug_unique, validate_slug

    fields: dict = {}
    for field in PROFILE_EDITABLE_FIELDS:
        if field not in payload:
            continue
        fields[field] = payload.get(field)

    if 'name' in fields:
        fields['name'] = str(fields['name'] or '').strip()
        if not fields['name']:
            raise ValueError('O nome da empresa é obrigatório.')
    if 'legal_name' in fields:
        fields['legal_name'] = str(fields['legal_name'] or '').strip()
        if not fields['legal_name']:
            raise ValueError('A razão social é obrigatória.')
    if 'cnpj' in fields:
        fields['cnpj'] = validate_cnpj(fields['cnpj'])
        ensure_unique_company_cnpj(connection, fields['cnpj'], company_id)

    # Estrutura empresarial: valores fora do enum caem no padrão em vez de
    # quebrar a tela de configuração.
    if 'org_structure_type' in fields:
        from modules.legal_entities.service import normalize_org_structure_type
        fields['org_structure_type'] = normalize_org_structure_type(fields['org_structure_type'])
    if 'stock_control_scope' in fields:
        from modules.legal_entities.service import normalize_stock_control_scope
        fields['stock_control_scope'] = normalize_stock_control_scope(fields['stock_control_scope'])

    for field in ('state_registration', 'municipal_registration', 'address',
                  'contact_phone', 'whatsapp', 'contact_email', 'website',
                  'display_name', 'institutional_message'):
        if field in fields:
            fields[field] = str(fields[field] or '').strip()

    if 'logo_type' in fields:
        fields['logo_type'] = validate_logo_payload(fields['logo_type'])
    if 'favicon_type' in fields:
        fields['favicon_type'] = validate_logo_payload(fields['favicon_type'])
    if 'login_logo_type' in fields:
        fields['login_logo_type'] = validate_login_logo_payload(fields['login_logo_type'])

    if 'primary_color' in fields:
        fields['primary_color'] = _validate_color(fields['primary_color'], '#1565C0')
    if 'secondary_color' in fields:
        fields['secondary_color'] = _validate_color(fields['secondary_color'], '#42A5F5')
    if 'accent_color' in fields:
        fields['accent_color'] = _validate_color(fields['accent_color'], '#FF6F00')
    if 'default_language' in fields:
        fields['default_language'] = _validate_language(fields['default_language'])
    if 'timezone' in fields:
        fields['timezone'] = _validate_timezone(fields['timezone'])

    if 'theme_json' in fields:
        import json as _json
        raw = fields['theme_json'] or '{}'
        if isinstance(raw, dict):
            fields['theme_json'] = _json.dumps(raw, ensure_ascii=False)
        else:
            try:
                _json.loads(str(raw))
                fields['theme_json'] = str(raw)
            except Exception:
                raise ValueError('Tema inválido: JSON malformado.')

    if 'slug' in fields:
        slug_raw = str(fields['slug'] or '').strip()
        if slug_raw:
            fields['slug'] = validate_slug(slug_raw)
            ensure_slug_unique(connection, fields['slug'], company_id)
        else:
            fields['slug'] = None
    if 'subdomain' in fields:
        fields['subdomain'] = _validate_subdomain(fields['subdomain'])
        ensure_tenant_routing_unique(connection, 'subdomain', fields['subdomain'], company_id)
    if 'custom_domain' in fields:
        fields['custom_domain'] = _validate_custom_domain(fields['custom_domain'])
        ensure_tenant_routing_unique(connection, 'custom_domain', fields['custom_domain'], company_id)

    return fields


def update_my_company(connection, company_id: int, fields: dict) -> None:
    """Aplica um update parcial usando somente colunas do whitelist."""
    columns = [field for field in PROFILE_EDITABLE_FIELDS if field in fields]
    if not columns:
        return
    assignments = ', '.join(f'{column} = ?' for column in columns)
    params = [fields[column] for column in columns]
    params.append(int(company_id))
    connection.execute(f'UPDATE companies SET {assignments} WHERE id = ?', params)  # noqa: S608


def summarize_profile_changes(previous: dict, fields: dict) -> tuple[str, list[dict]]:
    """Resumo auditável das mudanças (imagens registradas como marcador)."""
    changed = []
    details = []
    for field, value in fields.items():
        before = previous.get(field)
        if str(before or '') == str(value or ''):
            continue
        label = _FIELD_LABELS.get(field, field)
        changed.append(label.lower())
        if field in _IMAGE_FIELDS:
            details.append({
                'field': label,
                'before': '[imagem]' if before else '',
                'after': '[imagem]' if value else '',
            })
        else:
            details.append({'field': label, 'before': str(before or ''), 'after': str(value or '')})
    summary = (
        'Configuração da empresa alterada: ' + ', '.join(changed) + '.'
        if changed
        else 'Configuração da empresa revisada sem mudanças.'
    )
    return summary, details


def complete_onboarding(connection, company_id: int) -> str:
    """Marca o assistente de primeiro acesso como concluído."""
    completed_at = datetime.now(UTC).isoformat(timespec='seconds')
    connection.execute(
        'UPDATE companies SET onboarding_completed = 1, onboarding_completed_at = ? WHERE id = ?',
        (completed_at, int(company_id)),
    )
    return completed_at
