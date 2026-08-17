"""Escopo por empresa da Ficha de EPI, atravessando Python↔Dart.

O `master_admin` não tem empresa própria: para configurar a Ficha de um tenant
ele precisa **escolher** a empresa. Sem o seletor no cliente, ele não consegue
configurar a Ficha de nenhum tenant — era o estado deste repositório até o
Lote 5.

O ponto sensível aqui não é a UI: é que `company_id` vindo do cliente é uma
entrada de **autorização**. A regra tem de valer no servidor, não na tela.
`_resolve_settings_company_id` faz isso:

- `master_admin` sem seleção → erro na gravação (não grava em tenant nenhum);
- qualquer outro perfil com `company_id` divergente do próprio → **rejeitado**,
  não silenciosamente trocado pelo próprio. Esconder no cliente não bastaria:
  a requisição pode ser forjada.

Estes testes travam as duas pontas: que o backend impõe o escopo e que o
cliente Dart de fato envia o `company_id` que torna a seleção possível.
"""

import pathlib
import re

import pytest

from modules.settings.routes import _resolve_settings_company_id

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SETTINGS_API = RAIZ / 'flutter/packages/epi_api/lib/endpoints/settings_api.dart'
SETTINGS_CUBIT = RAIZ / 'flutter/apps/epi_admin/lib/core/bloc/settings_cubit.dart'
SETTINGS_SCREEN = RAIZ / 'flutter/apps/epi_admin/lib/features/settings/settings_screen.dart'


class _ConexaoFake:
    """Só o suficiente para o resolver: ele consulta a empresa pelo id."""

    def __init__(self, empresas=(7,)):
        self._empresas = set(empresas)

    def execute(self, *_a, **_k):  # pragma: no cover - não usado nestes casos
        raise AssertionError('o resolver não deveria consultar assim')


@pytest.fixture(autouse=True)
def _empresa_existente(monkeypatch):
    import modules.companies.service as companies
    monkeypatch.setattr(
        companies, 'get_company_by_id',
        lambda _conn, cid: {'id': cid} if cid in (7, 9) else None,
    )


# ── o servidor impõe o escopo ────────────────────────────────────────────────

def test_master_escolhe_a_empresa_explicitamente():
    conn = _ConexaoFake()
    actor = {'role': 'master_admin', 'company_id': None}
    assert _resolve_settings_company_id(conn, actor, '7') == 7


def test_master_sem_selecao_nao_grava_em_tenant_nenhum():
    conn = _ConexaoFake()
    actor = {'role': 'master_admin', 'company_id': None}
    with pytest.raises(ValueError):
        _resolve_settings_company_id(conn, actor, '', require=True)
    # Em leitura, devolve None (pré-visualização dos padrões) sem quebrar.
    assert _resolve_settings_company_id(conn, actor, '', require=False) is None


def test_master_nao_configura_empresa_inexistente():
    conn = _ConexaoFake()
    actor = {'role': 'master_admin', 'company_id': None}
    with pytest.raises(ValueError):
        _resolve_settings_company_id(conn, actor, '404')


@pytest.mark.parametrize('papel', ['general_admin', 'registry_admin', 'admin', 'user'])
def test_company_id_forjado_e_rejeitado_nao_ignorado(papel):
    # O ponto do teste: um perfil de empresa que MANDA outro company_id não
    # pode ser silenciosamente redirecionado para a própria empresa — tem de
    # ser recusado, senão o comportamento diverge do que a requisição pediu e
    # o erro passa despercebido. Nenhum caminho atravessa tenants.
    conn = _ConexaoFake()
    actor = {'role': papel, 'company_id': 7}
    with pytest.raises((ValueError, PermissionError)):
        _resolve_settings_company_id(conn, actor, '9')

    # A própria empresa continua permitida.
    assert _resolve_settings_company_id(conn, actor, '7') == 7
    assert _resolve_settings_company_id(conn, actor, '') == 7


def test_perfil_sem_empresa_vinculada_nao_configura():
    conn = _ConexaoFake()
    actor = {'role': 'general_admin', 'company_id': None}
    with pytest.raises(PermissionError):
        _resolve_settings_company_id(conn, actor, '')


# ── o cliente torna a seleção possível ───────────────────────────────────────

def test_o_cliente_dart_envia_company_id_nas_duas_pontas():
    api = SETTINGS_API.read_text(encoding='utf-8')
    for trecho in ('getFichaConfig({int? companyId})',
                   'updateFichaConfig(FichaConfig config, {int? companyId})'):
        assert trecho in api, f'faltando: {trecho}'
    assert "'company_id': companyId" in api


def test_o_estado_de_configuracoes_conhece_o_master_e_a_empresa_escolhida():
    cubit = SETTINGS_CUBIT.read_text(encoding='utf-8')
    for campo in ('isMaster', 'companies', 'selectedCompanyId'):
        assert campo in cubit, f'faltando no SettingsState: {campo}'
    # Sem entrar em props, dois estados diferentes comparariam como iguais e a
    # tela não reconstruiria ao trocar de empresa.
    props = cubit[cubit.index('get props'):]
    for campo in ('isMaster', 'companies', 'selectedCompanyId'):
        assert campo in props, f'{campo} fora de props'


def test_a_tela_oferece_o_seletor_apenas_ao_master():
    tela = SETTINGS_SCREEN.read_text(encoding='utf-8')
    assert '_CompanySelector' in tela, \
        'sem o seletor o master_admin não configura a Ficha de nenhum tenant'
    # O seletor é condicionado ao perfil — não é um campo solto para todos.
    assert re.search(r'if \(state\.isMaster\)\s*_CompanySelector', tela), \
        'o seletor precisa aparecer só para o master_admin'
