"""Gates de provisionamento da identidade de certificação (#313, emenda).

O requisito que justificou criar `certification_readonly` — uma credencial de
automação **sem colaborador fictício em produção** — estava implementado pela
metade. A proibição de vínculo vivia em `resolve_target_company_id`, mas
`resolve_user_employee_link` continuava exigindo colaborador para qualquer
papel. As duas regras se fechavam uma contra a outra:

    com `linked_employee_id`   → "não pode ser vinculada a um colaborador"
    sem `linked_employee_id`   → "Campo obrigatório: employee_id_code"

O papel era inalcançável pela API, e foi por isso que a conta técnica do SaaS
nasceu `registry_admin` — o papel mais privilegiado do inventário, que é
justamente o que esta frente existe para não usar.

Estes gates medem o caminho inteiro contra PostgreSQL real, porque foi
exatamente a ausência de um gate de PROVISIONAMENTO que deixou o furo passar:
os gates anteriores provaram o papel, as permissões, o escopo de tenant e o
fail-closed — nenhum provou que a identidade podia ser criada.
"""

import os
import sys
from contextlib import closing

import pytest

# Defensivo: hoje `test_313_escopo_tenant_postgres.py` sorteia antes e já faz
# este ajuste, mas o CI roda o console script `pytest` — que não põe o CWD no
# `sys.path` — e a ordem alfabética muda ao renomear um arquivo. Ver #315.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_connection
from core.roles import CERTIFICATION_READONLY_ROLE
from core.security import hash_password
from modules.users.service import create_user, update_user

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Exige DATABASE_URL apontando para PostgreSQL real.',
)

EMPRESA = 'T313P Empresa'
CNPJ = '00000000031300'
USUARIO = 't313p_cert'
ALVO = 't313p_alvo'


def _limpar(conexao):
    # Prefixo, não lista fixa: o gate de regressão cria `<USUARIO>_<papel>` e
    # uma limpeza por igualdade deixaria essas linhas para trás. Debris de um
    # teste é `UniqueViolation` no próximo — e a falha aparece longe da causa,
    # num arquivo que passou.
    conexao.execute("DELETE FROM users WHERE username LIKE 't313p%'")
    conexao.execute(
        'DELETE FROM employees WHERE company_id IN (SELECT id FROM companies WHERE name = ?)',
        (EMPRESA,))
    conexao.execute(
        'DELETE FROM units WHERE company_id IN (SELECT id FROM companies WHERE name = ?)',
        (EMPRESA,))
    conexao.execute('DELETE FROM companies WHERE name = ?', (EMPRESA,))
    conexao.commit()


@pytest.fixture
def cenario():
    """Empresa e ator `master_admin` — o único perfil que pode criar o papel."""
    from core.bootstrap import init_db
    init_db()

    with closing(get_connection()) as conexao:
        _limpar(conexao)
        conexao.execute(
            'INSERT INTO companies (name, cnpj, logo_type) VALUES (?, ?, ?)',
            (EMPRESA, CNPJ, 'none'))
        conexao.commit()
        empresa = int(conexao.execute(
            'SELECT id FROM companies WHERE name = ?', (EMPRESA,)).fetchone()[0])
        master = int(conexao.execute(
            "SELECT id FROM users WHERE role = 'master_admin' LIMIT 1").fetchone()[0])

    yield {'empresa': empresa, 'master': master}

    with closing(get_connection()) as conexao:
        _limpar(conexao)


def _colaboradores(conexao):
    return int(conexao.execute('SELECT count(*) FROM employees').fetchone()[0])


def _conta(conexao, username):
    linha = conexao.execute(
        'SELECT role, company_id, linked_employee_id, active FROM users WHERE username = ?',
        (username,)).fetchone()
    if not linha:
        return None
    return {'role': linha[0], 'company_id': linha[1],
            'linked_employee_id': linha[2], 'active': linha[3]}


# ── Gates 1, 3, 4 ────────────────────────────────────────────────────────────

def test_criacao_sem_colaborador_e_sem_campos_employee(cenario):
    """`create_user` produz a identidade sem tocar em `employees`.

    A contagem antes/depois é o que separa "funcionou" de "funcionou criando um
    colaborador escondido" — que passaria despercebido numa asserção sobre o
    usuário apenas.
    """
    with closing(get_connection()) as conexao:
        antes = _colaboradores(conexao)

        create_user(conexao, {
            'actor_user_id': cenario['master'],
            'username': USUARIO,
            'full_name': 'Certificacao B4-B (automacao)',
            'role': CERTIFICATION_READONLY_ROLE,
            'company_id': cenario['empresa'],
            'password': 'senha-forte-para-teste',
            'active': 1,
        })

        depois = _colaboradores(conexao)
        conta = _conta(conexao, USUARIO)

    assert conta is not None, 'a conta não foi criada'
    assert conta['role'] == CERTIFICATION_READONLY_ROLE
    assert int(conta['company_id']) == cenario['empresa']
    assert conta['linked_employee_id'] is None, 'a identidade ficou vinculada a um colaborador'
    assert int(conta['active']) == 1
    assert depois == antes, f'{depois - antes} colaborador(es) criado(s) como efeito colateral'


# ── Gate 2 ───────────────────────────────────────────────────────────────────

def test_promocao_de_registry_admin_para_a_identidade_tecnica(cenario):
    """O caminho de correção da conta que existe hoje em produção."""
    with closing(get_connection()) as conexao:
        conexao.execute(
            'INSERT INTO users (username, password, full_name, role, company_id, active) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (ALVO, hash_password('senha-forte-para-teste'), 'Alvo',
             'registry_admin', cenario['empresa'], 1))
        conexao.commit()
        alvo = int(conexao.execute(
            'SELECT id FROM users WHERE username = ?', (ALVO,)).fetchone()[0])
        antes = _colaboradores(conexao)

        # Sem `password` de propósito: `update_user` chama `mark_temp_password`
        # sempre que recebe senha, e isso religaria `must_change_password = 1`,
        # que bloqueia toda rota autenticada com 403.
        update_user(conexao, alvo, {
            'actor_user_id': cenario['master'],
            'username': ALVO,
            'full_name': 'Alvo',
            'role': CERTIFICATION_READONLY_ROLE,
            'company_id': cenario['empresa'],
            'active': 1,
        })

        depois = _colaboradores(conexao)
        conta = _conta(conexao, ALVO)
        politica = conexao.execute(
            'SELECT must_change_password FROM users WHERE id = ?', (alvo,)).fetchone()[0]

    assert conta['role'] == CERTIFICATION_READONLY_ROLE
    assert conta['linked_employee_id'] is None
    assert depois == antes, f'{depois - antes} colaborador(es) criado(s) como efeito colateral'
    assert int(politica or 0) == 0, \
        'must_change_password foi religado: a conta ficaria bloqueada em 403'


# ── Gate 5 ───────────────────────────────────────────────────────────────────

def test_empresa_continua_obrigatoria(cenario):
    """A saída antecipada preserva `company_id` — não o torna opcional.

    Sem empresa o escopo enumerado sai vazio e o isolamento por tenant deixaria
    de ser verificável; é a mesma regra que `resolve_target_company_id` impõe.
    """
    with closing(get_connection()) as conexao, \
            pytest.raises(ValueError, match='exige empresa vinculada'):
        create_user(conexao, {
            'actor_user_id': cenario['master'],
            'username': USUARIO,
            'full_name': 'Sem empresa',
            'role': CERTIFICATION_READONLY_ROLE,
            'password': 'senha-forte-para-teste',
            'active': 1,
        })


def test_vinculo_explicito_continua_recusado(cenario):
    """A saída antecipada NÃO afrouxa a proibição de vínculo.

    Os dois lados da tesoura precisam continuar existindo: este teste falha se
    alguém "simplificar" removendo a guarda de `resolve_target_company_id`.
    """
    with closing(get_connection()) as conexao, \
            pytest.raises(ValueError, match='não pode ser vinculada'):
        create_user(conexao, {
            'actor_user_id': cenario['master'],
            'username': USUARIO,
            'full_name': 'Com vinculo',
            'role': CERTIFICATION_READONLY_ROLE,
            'company_id': cenario['empresa'],
            'linked_employee_id': 1,
            'password': 'senha-forte-para-teste',
            'active': 1,
        })


# ── Regressão: papéis operacionais inalterados ───────────────────────────────

def test_papeis_operacionais_mantem_a_exigencia_de_colaborador(cenario):
    """`admin` e `user` continuam exigindo colaborador — sem a emenda afrouxar.

    O gate afirma COMPORTAMENTO, não mensagem, porque `modules/users/service.py`
    diverge entre os dois repositórios: o `epi-controle-app` tem
    `_resolve_optional_employee_link`, que dispensa colaborador para perfis
    administrativos, e o corporativo não. Os textos de erro diferem
    legitimamente — o que precisa valer nos dois é que o perfil operacional não
    nasce sem vínculo e que nenhum colaborador é criado no caminho.

    `registry_admin` fica fora da lista de propósito: é exatamente onde os dois
    repositórios divergem hoje, e fixá-lo aqui transformaria uma diferença
    conhecida e anterior à #313 numa falha desta frente.
    """
    with closing(get_connection()) as conexao:
        antes = _colaboradores(conexao)

        for papel in ('admin', 'user'):
            nome = f'{USUARIO}_{papel}'
            with pytest.raises(ValueError):
                create_user(conexao, {
                    'actor_user_id': cenario['master'],
                    'username': nome,
                    'full_name': f'Operacional {papel}',
                    'role': papel,
                    'company_id': cenario['empresa'],
                    'password': 'senha-forte-para-teste',
                    'active': 1,
                })
            assert _conta(conexao, nome) is None, \
                f'{papel} foi criado sem colaborador vinculado'

        assert _colaboradores(conexao) == antes, \
            'a tentativa com perfil operacional criou colaborador'


def test_campos_de_colaborador_nao_criam_colaborador_para_a_identidade(cenario):
    """Campos `employee_*` acompanhando a identidade técnica NÃO criam ninguém.

    Este é o caminho onde a saída antecipada é sustentadora nos DOIS
    repositórios. No corporativo ela já governa o payload comum; no
    `epi-controle-app`, `_resolve_optional_employee_link` desvia antes e só
    encaminha para `resolve_user_employee_link` quando há vínculo explícito ou
    campos manuais — e vínculo explícito já é recusado em
    `resolve_target_company_id`. Sobra exatamente este caso: alguém colando um
    payload de cadastro de pessoa sobre a identidade de automação.

    Sem a saída antecipada, isto criaria uma linha em `employees` — o dado
    fictício em produção que a #313 existe para não ter.
    """
    with closing(get_connection()) as conexao:
        antes = _colaboradores(conexao)
        unidade = conexao.execute(
            'SELECT id FROM units WHERE company_id = ? LIMIT 1', (cenario['empresa'],)).fetchone()

        create_user(conexao, {
            'actor_user_id': cenario['master'],
            'username': USUARIO,
            'full_name': 'Certificacao B4-B (automacao)',
            'role': CERTIFICATION_READONLY_ROLE,
            'company_id': cenario['empresa'],
            'password': 'senha-forte-para-teste',
            'active': 1,
            # Payload de cadastro de pessoa, colado por engano:
            'employee_id_code': 'T313P-999',
            'employee_role_name': 'Tecnico',
            'employee_sector': 'SESMT',
            'employee_schedule_type': 'integral',
            'employee_admission_date': '2020-01-01',
            'employee_unit_id': str(int(unidade[0])) if unidade else '',
        })

        depois = _colaboradores(conexao)
        conta = _conta(conexao, USUARIO)

    assert conta is not None and conta['role'] == CERTIFICATION_READONLY_ROLE
    assert conta['linked_employee_id'] is None, 'a identidade ficou vinculada a um colaborador'
    assert int(conta['company_id']) == cenario['empresa'], \
        'a saída antecipada perdeu o tenant: sem empresa o escopo enumerado sai vazio'
    assert depois == antes, \
        f'{depois - antes} colaborador(es) criado(s) a partir dos campos employee_*'
