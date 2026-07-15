"""Resolução de empresa da Ficha (POST/GET /api/ficha-config).

O master_admin não tem empresa própria (company_id NULL): antes o
save_ficha_config(actor['company_id']) estourava e a Ficha não podia ser
configurada por ele. Agora o master escolhe a empresa (isolada por tenant);
general_admin/registry_admin ficam presos à própria empresa.
"""

import pytest

import modules.settings.routes as settings_routes


def test_master_requires_company_selection_on_save():
    actor = {'role': 'master_admin', 'company_id': None}
    with pytest.raises(ValueError, match='Selecione uma empresa'):
        settings_routes._resolve_settings_company_id(None, actor, '')


def test_master_with_selection_resolves(monkeypatch):
    import modules.companies.service as comp_svc
    monkeypatch.setattr(comp_svc, 'get_company_by_id', lambda c, cid: {'id': cid})
    actor = {'role': 'master_admin', 'company_id': None}
    assert settings_routes._resolve_settings_company_id(None, actor, '3') == 3


def test_master_read_mode_returns_none():
    # GET (require=False): master sem seleção vê os padrões, não quebra o load.
    actor = {'role': 'master_admin', 'company_id': None}
    assert settings_routes._resolve_settings_company_id(None, actor, '', require=False) is None


def test_general_admin_forced_to_own_company():
    actor = {'role': 'general_admin', 'company_id': 8}
    assert settings_routes._resolve_settings_company_id(None, actor, '') == 8


def test_general_admin_cross_tenant_blocked():
    actor = {'role': 'general_admin', 'company_id': 8}
    with pytest.raises(PermissionError):
        settings_routes._resolve_settings_company_id(None, actor, '99')
