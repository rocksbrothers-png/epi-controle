"""Gates 1-6 da #313 — a identidade técnica da certificação B4-B.

O que estes gates existem para impedir, em ordem de gravidade:

1. que `certification_readonly` ganhe uma permissão de escrita — a credencial
   roda sozinha no CI, e o motivo de ela existir é não ser `registry_admin`,
   que carrega 26 escritas incluindo `users:delete` e `units:delete`;
2. que o papel entre numa lista privilegiada por associação — `BILLABLE_ROLES`,
   `EPI_ALL_UNITS_PROFILES`, `CONFIGURATION_ADMIN_ROLES` ou o conjunto que
   `general_admin`/`registry_admin` podem gerenciar;
3. que a exigência de empresa desapareça. Ela NÃO é herdada de `BILLABLE_ROLES`
   — o papel está fora de lá de propósito — e sem `company_id` o escopo
   enumerado sai vazio.

Os gates de escopo contra banco real (3, 4 e 5 do contrato) vivem em
`tests_postgres/test_313_escopo_tenant_postgres.py`: a propriedade que eles
provam é isolamento entre tenants, e isso se mede consultando, não lendo.
"""

import ast
import pathlib
import re

import pytest

from core.permissions import PERMISSIONS
from core.roles import (
    BILLABLE_ROLES,
    CERTIFICATION_READONLY_ROLE,
    ROLE_ALIASES,
    ROLE_WEIGHT,
)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CONSTANTS_JS = RAIZ / 'static' / 'js' / 'core' / 'constants.js'
USERS_SERVICE = RAIZ / 'modules' / 'users' / 'service.py'
USERS_SCREEN = RAIZ / 'flutter' / 'apps' / 'epi_admin' / 'lib' / 'features' / 'users' / 'users_screen.dart'

PAPEL = CERTIFICATION_READONLY_ROLE


def _lista_js(nome):
    """Extrai uma lista de literais de `constants.js`, ou falha dizendo isso.

    Devolver `[]` para lista inexistente transformaria "não encontrei a regra"
    em "o papel não está lá" — que é justamente o falso verde que o gate 2
    existe para impedir.
    """
    texto = CONSTANTS_JS.read_text(encoding='utf-8')
    casado = re.search(rf'{nome}\s*=\s*Object\.freeze\(\[(.*?)\]\)', texto, re.DOTALL)
    assert casado, f'{nome} não foi encontrada em constants.js — matcher quebrado'
    itens = re.findall(r"'([^']+)'", casado.group(1))
    assert itens, f'{nome} foi encontrada vazia — matcher quebrado'
    return itens


# ── Gate 1 ───────────────────────────────────────────────────────────────────

def test_o_papel_tem_exatamente_as_duas_permissoes():
    """Igualdade, não continência.

    Continência (`⊆`) aceitaria uma conta com UMA das duas, que reprovaria a
    certificação por falta de acesso e mandaria investigar o deployment. E
    aceitaria também o conjunto vazio.
    """
    assert PERMISSIONS[PAPEL] == frozenset({'units:view', 'stock:view'})


def test_o_papel_existe_no_enum_e_nos_aliases():
    """`create_user` reprova papel ausente de `ROLE_WEIGHT` — sem isto a
    identidade não é sequer criável, e o erro apareceria só no provisionamento."""
    assert ROLE_WEIGHT[PAPEL] == 0
    assert ROLE_ALIASES[PAPEL] == PAPEL


# ── Gate 2 ───────────────────────────────────────────────────────────────────

def test_fora_de_billable_roles():
    assert PAPEL not in BILLABLE_ROLES


@pytest.mark.parametrize('lista', [
    'USER_COMPANY_REQUIRED_ROLES',
    'CONFIGURATION_ADMIN_ROLES',
    'EPI_ALL_UNITS_PROFILES',
])
def test_fora_das_listas_privilegiadas_do_web_legado(lista):
    """`EPI_ALL_UNITS_PROFILES` é a que morde: é o espelho JS de "perfil livre",
    e entrar nela daria ao papel a visão de todas as Unidades no front."""
    assert PAPEL not in _lista_js(lista)


def test_tem_rotulo_na_ui():
    """Decisão explícita: a conta técnica precisa ser identificável numa
    listagem ou auditoria. Rótulo é visibilidade, não permissão."""
    texto = CONSTANTS_JS.read_text(encoding='utf-8')
    casado = re.search(r'ROLE_LABELS\s*=\s*Object\.freeze\(\{(.*?)\}\)', texto, re.DOTALL)
    assert casado, 'ROLE_LABELS não encontrada — matcher quebrado'
    assert f'{PAPEL}:' in casado.group(1)


def test_fora_do_seletor_de_criacao_do_flutter():
    """Visível em listagem, ausente de todo seletor de criação/edição."""
    if not USERS_SCREEN.exists():
        pytest.skip('users_screen.dart ausente neste repositório')
    assert PAPEL not in USERS_SCREEN.read_text(encoding='utf-8')


def test_nao_e_gerenciavel_por_general_admin_nem_registry_admin():
    """Só `master_admin` mint a identidade.

    Medido, não suposto: `authorize_user_management` restringe os dois perfis
    administrativos a uma lista literal de seis papéis, e o novo não entra
    nela. O gate lê a lista real do código — se ela mudar de forma, a asserção
    de que a lista foi encontrada falha primeiro.
    """
    arvore = ast.parse(USERS_SERVICE.read_text(encoding='utf-8'))
    literais = [
        {no.value for no in n.elts if isinstance(no, ast.Constant)}
        for n in ast.walk(arvore)
        if isinstance(n, ast.Tuple) and {e.value for e in n.elts
                                         if isinstance(e, ast.Constant)} >= {'registry_admin', 'buyer', 'approver'}
    ]
    assert literais, 'lista de papéis gerenciáveis não encontrada — matcher quebrado'
    for conjunto in literais:
        assert PAPEL not in conjunto


# ── Gate 6 ───────────────────────────────────────────────────────────────────

def test_nenhuma_permissao_de_escrita():
    """Duas asserções que falham por motivos diferentes, de propósito.

    A primeira é sintática e pega uma permissão nova de escrita. A segunda é
    relacional e pega o caso em que alguém batiza uma escrita com sufixo
    `:view` — ela seria invisível para a primeira, mas apareceria no conjunto
    de escritas dos outros papéis.
    """
    assert all(p.endswith(':view') for p in PERMISSIONS[PAPEL])

    escritas = {p for perms in PERMISSIONS.values() for p in perms
                if not p.endswith(':view')}
    assert escritas, 'nenhuma escrita no sistema inteiro — matcher quebrado'
    assert not (PERMISSIONS[PAPEL] & escritas)


def test_e_o_papel_de_menor_privilegio_que_serve_ao_smoke():
    """A razão de existir da #313, verificável.

    Se um papel preexistente com menos permissões já servisse, criar um novo
    seria custo sem ganho — e este gate reprovaria a decisão.
    """
    necessarias = {'units:view', 'stock:view'}
    servem = {r: p for r, p in PERMISSIONS.items() if necessarias <= p}
    assert PAPEL in servem
    assert len(PERMISSIONS[PAPEL]) == min(len(p) for p in servem.values())


# ── Exigência de tenant ──────────────────────────────────────────────────────

def test_sem_empresa_a_identidade_nao_e_criavel():
    """A regra NÃO é herdada de `BILLABLE_ROLES` — o papel está fora de lá.

    É exatamente por isso que ela precisa existir explicitamente: tirar o papel
    da lista de cobrança (decisão correta, é automação e não assento) desliga
    de carona a única validação que exigia empresa. Sem `company_id` o escopo
    enumerado devolve `()`, e o isolamento passaria a depender de ninguém
    olhar.
    """
    from modules.users.service import resolve_target_company_id

    ator = {'role': 'master_admin', 'company_id': None}
    with pytest.raises(ValueError, match='exige empresa vinculada'):
        resolve_target_company_id(ator, None, PAPEL, None)

    assert resolve_target_company_id(ator, 7, PAPEL, None) == 7


def test_a_identidade_nao_pode_ter_colaborador_vinculado():
    """Sem colaborador fictício em produção — a regra que descartou `approver`,
    `buyer`, `admin` e `user` como candidatos na auditoria."""
    from modules.users.service import resolve_target_company_id

    ator = {'role': 'master_admin', 'company_id': None}
    with pytest.raises(ValueError, match='não pode ser vinculada'):
        resolve_target_company_id(ator, 7, PAPEL, 42)
