"""FIX-USERS-ACTIVE-V1 — editar usuário não altera o status da conta (PostgreSQL real).

Antes: o formulário de edição (sem campo de status) mandava `active = 1` e o
servidor usava `payload.get('active', 1)` — salvar qualquer edição reativava uma
conta inativa. Agora, sem `active` explícito o status atual é mantido; ativar e
desativar seguem pelo mesmo PUT com `active` explícito, sob as mesmas regras de
permissão e de empresa, e a troca de status entra na trilha de auditoria.

Cenários da demanda:
  1. editar usuário inativo sem mexer no status;
  2. editar usuário ativo sem mexer no status;
  3. reativar com ação explícita e autorizada (com auditoria);
  4. perfil sem permissão não reativa;
  5. outra empresa não reativa;
  6. o status persiste numa leitura nova do banco (equivale a recarregar a página).
"""

import os
import sys
from contextlib import closing

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_connection
from core.security import hash_password
from modules.users.service import update_user

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Exige DATABASE_URL apontando para PostgreSQL real.',
)

PREFIXO = 'fua1'
EMPRESAS = {'A': ('FUA1 Empresa A', '00000000071001'), 'B': ('FUA1 Empresa B', '00000000071002')}


def _limpar(conexao):
    nomes = tuple(nome for nome, _ in EMPRESAS.values())
    marcadores = ', '.join('?' for _ in nomes)
    # A trilha referencia os usuários (actor_user_id): sai antes deles.
    por_empresa = f'company_id IN (SELECT id FROM companies WHERE name IN ({marcadores}))'
    conexao.execute(f'DELETE FROM company_audit_logs WHERE {por_empresa}', nomes)
    conexao.execute(f"DELETE FROM users WHERE username LIKE '{PREFIXO}%'")
    for tabela in ('employees', 'units'):
        conexao.execute(f'DELETE FROM {tabela} WHERE {por_empresa}', nomes)
    conexao.execute(f'DELETE FROM companies WHERE name IN ({marcadores})', nomes)
    conexao.commit()


def _um(conexao, sql, params=()):
    return conexao.execute(sql, params).fetchone()[0]


@pytest.fixture
def cenario():
    from core.bootstrap import init_db
    init_db()
    with closing(get_connection()) as conexao:
        _limpar(conexao)
        ids = {}
        for chave, (nome, cnpj) in EMPRESAS.items():
            conexao.execute(
                'INSERT INTO companies (name, cnpj, logo_type, user_limit, active) VALUES (?, ?, ?, ?, ?)',
                (nome, cnpj, 'none', 50, 1))
            empresa = int(_um(conexao, 'SELECT id FROM companies WHERE name = ?', (nome,)))
            conexao.execute(
                'INSERT INTO units (company_id, name, unit_type, city) VALUES (?, ?, ?, ?)',
                (empresa, f'Base {chave}', 'base', 'Macaé'))
            ids[f'empresa_{chave}'] = empresa
            ids[f'unidade_{chave}'] = int(_um(conexao, 'SELECT id FROM units WHERE company_id = ?', (empresa,)))

        def usuario(nome, papel, empresa, ativo, com_colaborador=True):
            colaborador = None
            if com_colaborador:
                conexao.execute(
                    'INSERT INTO employees (company_id, unit_id, employee_id_code, name, sector, role_name, '
                    'admission_date, schedule_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (ids[f'empresa_{empresa}'], ids[f'unidade_{empresa}'], f'MAT-{nome}', nome, 'Suprimentos',
                     'Analista', '2026-01-05', '5x2'))
                colaborador = int(_um(conexao, 'SELECT id FROM employees WHERE employee_id_code = ?', (f'MAT-{nome}',)))
            conexao.execute(
                'INSERT INTO users (username, password, full_name, role, company_id, active, linked_employee_id) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                (f'{PREFIXO}_{nome}', hash_password('senha-forte-para-teste'), nome.replace('_', ' ').title(), papel,
                 ids[f'empresa_{empresa}'], ativo, colaborador))
            ids[nome] = int(_um(conexao, 'SELECT id FROM users WHERE username = ?', (f'{PREFIXO}_{nome}',)))
            ids[f'colab_{nome}'] = colaborador

        usuario('geral_a', 'general_admin', 'A', 1)
        usuario('registro_a', 'registry_admin', 'A', 1)
        usuario('gestor_ativo_a', 'user', 'A', 1)
        usuario('gestor_inativo_a', 'user', 'A', 0)
        usuario('comprador_a', 'buyer', 'A', 1)
        usuario('geral_b', 'general_admin', 'B', 1)
        usuario('gestor_inativo_b', 'user', 'B', 0)
        conexao.commit()
    yield ids
    with closing(get_connection()) as conexao:
        _limpar(conexao)


def _status(alvo):
    # Conexão nova a cada leitura: o mesmo que recarregar a página (cenário 6).
    with closing(get_connection()) as conexao:
        return int(_um(conexao, 'SELECT active FROM users WHERE id = ?', (alvo,)))


def _auditoria(empresa):
    with closing(get_connection()) as conexao:
        return [tuple(linha) for linha in conexao.execute(
            "SELECT action_type, summary FROM company_audit_logs WHERE company_id = ? AND action_type IN ('user_reactivate', 'user_deactivate') "
            'ORDER BY id', (empresa,)).fetchall()]


def _editar(cenario, ator, alvo, **extra):
    """Corpo igual ao do formulário de edição: sem `active` (ele não tem esse campo)."""
    nome = alvo.removeprefix(f'{PREFIXO}_') if isinstance(alvo, str) else None
    alvo_id = cenario[nome] if nome else alvo
    with closing(get_connection()) as conexao:
        linha = conexao.execute('SELECT username, full_name, role, company_id, linked_employee_id FROM users WHERE id = ?',
                                (alvo_id,)).fetchone()
        payload = {'actor_user_id': cenario[ator], 'username': linha[0], 'full_name': f'{linha[1]} (editado)',
                   'password': '', 'role': linha[2], 'company_id': linha[3], 'linked_employee_id': linha[4], **extra}
        update_user(conexao, alvo_id, payload, actor_user_id=cenario[ator])
    return alvo_id


# 1 e 6
@pytest.mark.parametrize('ator', ['geral_a', 'registro_a'])
def test_editar_inativo_sem_status_mantem_inativo(cenario, ator):
    alvo = _editar(cenario, ator, 'gestor_inativo_a')
    assert _status(alvo) == 0
    assert _auditoria(cenario['empresa_A']) == []  # nenhuma troca de status


def test_editar_inativo_com_status_vazio_mantem_inativo(cenario):
    alvo = _editar(cenario, 'geral_a', 'gestor_inativo_a', active='')
    assert _status(alvo) == 0


# 2
def test_editar_ativo_sem_status_mantem_ativo(cenario):
    alvo = _editar(cenario, 'geral_a', 'gestor_ativo_a')
    assert _status(alvo) == 1


# 3
def test_reativar_e_desativar_explicitos_autorizados_com_auditoria(cenario):
    alvo = _editar(cenario, 'geral_a', 'gestor_inativo_a', active=1)
    assert _status(alvo) == 1
    _editar(cenario, 'registro_a', 'gestor_inativo_a', active=0)
    assert _status(alvo) == 0
    trilha = _auditoria(cenario['empresa_A'])
    assert [acao for acao, _ in trilha] == ['user_reactivate', 'user_deactivate']
    assert f'{PREFIXO}_gestor_inativo_a reativado por Geral A' in trilha[0][1]
    assert f'{PREFIXO}_gestor_inativo_a desativado por Registro A' in trilha[1][1]


def test_status_invalido_e_recusado_sem_alterar(cenario):
    for valor in ('x', 2, -1):
        with pytest.raises(ValueError):
            _editar(cenario, 'geral_a', 'gestor_inativo_a', active=valor)
    assert _status(cenario['gestor_inativo_a']) == 0


# 4
@pytest.mark.parametrize('ator', ['gestor_ativo_a', 'comprador_a'])
def test_perfil_sem_permissao_nao_reativa(cenario, ator):
    with pytest.raises(PermissionError):
        _editar(cenario, ator, 'gestor_inativo_a', active=1)
    assert _status(cenario['gestor_inativo_a']) == 0
    assert _auditoria(cenario['empresa_A']) == []


# 5
@pytest.mark.parametrize(('ator', 'alvo', 'empresa'), [('geral_b', 'gestor_inativo_a', 'A'),
                                                       ('geral_a', 'gestor_inativo_b', 'B')])
def test_outra_empresa_nao_reativa(cenario, ator, alvo, empresa):
    with pytest.raises((PermissionError, ValueError)):
        _editar(cenario, ator, alvo, active=1)
    assert _status(cenario[alvo]) == 0
    assert _auditoria(cenario[f'empresa_{empresa}']) == []
