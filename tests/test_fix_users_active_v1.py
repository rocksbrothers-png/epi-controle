"""FIX-USERS-ACTIVE-V1 — regra de status na edição de usuário (sem banco).

O caminho completo (permissão, empresa, auditoria) roda contra PostgreSQL em
tests_postgres/test_fix_users_active_v1_postgres.py.
"""
import pytest

import modules.users.service as users_service
from modules.companies.service import company_action_label
from modules.users.service import register_user_status_audit, resolve_user_active


@pytest.mark.parametrize('current', [0, 1])
@pytest.mark.parametrize('payload', [{}, {'active': None}, {'active': ''}, {'active': '  '}])
def test_sem_status_explicito_mantem_o_atual(payload, current):
    assert resolve_user_active(payload, {'active': current}) == current


@pytest.mark.parametrize(('raw', 'esperado'), [(0, 0), (1, 1), ('0', 0), ('1', 1), (' 1 ', 1), (True, 1), (False, 0)])
def test_status_explicito_e_respeitado(raw, esperado):
    assert resolve_user_active({'active': raw}, {'active': 1 - esperado}) == esperado


@pytest.mark.parametrize('raw', ['x', '2', 2, -1, '1.0'])
def test_status_invalido_e_recusado(raw):
    with pytest.raises(ValueError, match='Status do usuário inválido'):
        resolve_user_active({'active': raw}, {'active': 0})


def test_status_atual_nulo_conta_como_inativo():
    assert resolve_user_active({}, {'active': None}) == 0


class _Registro:
    def __init__(self):
        self.chamadas = []

    def __call__(self, connection, company_id, actor, action_type, summary, details=None, **kwargs):
        self.chamadas.append((company_id, action_type, summary, details))


@pytest.mark.parametrize(('active', 'acao', 'texto', 'antes', 'depois'), [
    (1, 'user_reactivate', 'reativado', 'Inativo', 'Ativo'),
    (0, 'user_deactivate', 'desativado', 'Ativo', 'Inativo'),
])
def test_troca_de_status_vai_para_a_trilha_da_empresa(monkeypatch, active, acao, texto, antes, depois):
    registro = _Registro()
    monkeypatch.setattr(users_service, 'register_company_audit', registro)
    register_user_status_audit(None, {'id': 2, 'full_name': 'Geral A'}, {'username': 'gestor.a'}, active, '7')
    assert registro.chamadas == [(7, acao, f'Usuário gestor.a {texto} por Geral A.',
                                  [{'field': 'Status do usuário', 'before': antes, 'after': depois}])]


def test_usuario_sem_empresa_nao_gera_registro(monkeypatch):
    registro = _Registro()
    monkeypatch.setattr(users_service, 'register_company_audit', registro)
    register_user_status_audit(None, {'id': 1, 'full_name': 'Master'}, {'username': 'x'}, 1, None)
    assert registro.chamadas == []


def test_rotulos_do_historico():
    assert company_action_label('user_reactivate') == 'Usuário reativado'
    assert company_action_label('user_deactivate') == 'Usuário desativado'


def test_update_user_usa_a_regra_e_audita_so_quando_muda():
    import inspect
    fonte = inspect.getsource(users_service.update_user)
    assert "payload.get('active', 1)" not in fonte  # o padrão 1 reativava contas
    assert 'active = resolve_user_active(payload, current)' in fonte
    assert 'register_user_status_audit(' in fonte
