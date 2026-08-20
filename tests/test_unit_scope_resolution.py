"""Contexto de Unidade — resolução única e validada (fatia 1.1D-A).

`modules/stock/routes.py` tinha sete cópias da mesma linha:

    scope_unit_id = actor_operational_unit_id(connection, actor)
    unit_filter = scope_unit_id or query.get('unit_id', [''])[0]

Duas coisas erradas nela:

1. o `or` decide a ORIGEM do recorte por truthiness — a mesma família de
   defeito que a 1.1B tirou do saldo de estoque;
2. o `unit_id` do cliente entrava **sem nenhuma validação de tenant**. Não
   vazava lista, porque `company_filter` recortava depois, mas o isolamento
   dependia da composição incidental de dois filtros — e o saldo por unidade
   (`get_unit_stock`, `fetch_epi_size_balance`) era lido da unidade PEDIDA
   antes desse recorte existir.

`core.repository.resolve_unit_scope` passa a ser o ponto único: perfil travado
usa a unidade do ator (com movimento temporário vigente tendo precedência) e
descarta o que o cliente mandar; perfil livre precisa de uma unidade que exista
e pertença à própria empresa, senão 400.

Esta fatia aplica o helper apenas em `/api/stock/epis` — os outros seis pontos
seguem como estão, por escopo. O teste
`test_os_demais_pontos_de_estoque_seguem_no_padrao_antigo` registra isso
explicitamente, para que a dívida não fique só num comentário de PR.
"""

import pathlib
import re
import sqlite3

import pytest

from core.repository import UnitScope, resolve_unit_scope

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ROUTES = RAIZ / 'modules/stock/routes.py'
SESSION_CONTEXT = (
    RAIZ / 'flutter/apps/epi_admin/lib/core/session/session_context.dart'
)

MASTER = {'id': 1, 'role': 'master_admin', 'company_id': None, 'linked_employee_id': None}
GERAL = {'id': 2, 'role': 'general_admin', 'company_id': 1, 'linked_employee_id': None}
GERAL_OUTRA = {'id': 3, 'role': 'general_admin', 'company_id': 2, 'linked_employee_id': None}
ADMIN_LOCAL = {'id': 4, 'role': 'admin', 'company_id': 1, 'linked_employee_id': 40}
GESTOR = {'id': 5, 'role': 'user', 'company_id': 1, 'linked_employee_id': 50}
ADMIN_SEM_UNIDADE = {'id': 6, 'role': 'admin', 'company_id': 1, 'linked_employee_id': None}


def _conexao():
    """Empresa 1 com as unidades 10 e 11; empresa 2 com a unidade 20."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER)')
    conn.execute('CREATE TABLE employees (id INTEGER PRIMARY KEY, unit_id INTEGER)')
    conn.execute(
        'CREATE TABLE employee_unit_movements ('
        ' id INTEGER PRIMARY KEY, employee_id INTEGER, movement_type TEXT,'
        ' start_date TEXT, end_date TEXT, target_unit_id INTEGER)'
    )
    conn.executemany(
        'INSERT INTO units (id, company_id) VALUES (?, ?)',
        [(10, 1), (11, 1), (20, 2)],
    )
    conn.executemany(
        'INSERT INTO employees (id, unit_id) VALUES (?, ?)',
        [(40, 10), (50, 10)],
    )
    conn.commit()
    return conn


# ═══════════════════════════════════════════════════════════════════════════
# Perfil travado — a unidade é do ator, e só dele
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize('ator', [ADMIN_LOCAL, GESTOR])
def test_perfil_travado_usa_a_unidade_do_ator(ator):
    with _conexao() as conn:
        escopo = resolve_unit_scope(conn, ator)
    assert escopo == UnitScope(10, 'actor', True)


@pytest.mark.parametrize('ator', [ADMIN_LOCAL, GESTOR])
@pytest.mark.parametrize('pedido', ['11', '20', 11, 20])
def test_perfil_travado_nao_troca_de_unidade_pelo_pedido(ator, pedido):
    """Nem para outra unidade da MESMA empresa (11), nem para outra empresa (20).

    Descartar em vez de recusar é deliberado: um cliente que ainda mande
    `unit_id` não vira erro — ele só não é ouvido. A autorização não depende
    de o cliente parar de mandar.
    """
    with _conexao() as conn:
        escopo = resolve_unit_scope(conn, ator, pedido)
    assert escopo.unit_id == 10, 'perfil travado trocou de unidade pelo payload'
    assert escopo.source == 'actor'
    assert escopo.locked is True


@pytest.mark.parametrize('ator', [ADMIN_LOCAL, GESTOR])
def test_movimento_temporario_vigente_tem_precedencia(ator):
    """A unidade efetiva é para onde o colaborador foi movido, não a de origem."""
    with _conexao() as conn:
        conn.execute(
            'INSERT INTO employee_unit_movements '
            '(employee_id, movement_type, start_date, end_date, target_unit_id) '
            "VALUES (?, 'temporary', '2000-01-01', '9999-12-31', ?)",
            (int(ator['linked_employee_id']), 11),
        )
        conn.commit()
        escopo = resolve_unit_scope(conn, ator, '10')
    assert escopo.unit_id == 11, 'movimento temporário vigente perdeu a precedência'
    assert escopo.source == 'actor'


@pytest.mark.parametrize('ator', [ADMIN_LOCAL, GESTOR])
def test_movimento_temporario_encerrado_nao_vale(ator):
    with _conexao() as conn:
        conn.execute(
            'INSERT INTO employee_unit_movements '
            '(employee_id, movement_type, start_date, end_date, target_unit_id) '
            "VALUES (?, 'temporary', '2000-01-01', '2000-12-31', ?)",
            (int(ator['linked_employee_id']), 11),
        )
        conn.commit()
        escopo = resolve_unit_scope(conn, ator)
    assert escopo.unit_id == 10


def test_perfil_travado_sem_unidade_e_fail_closed():
    """Sem unidade resolvida, NEGA — nunca cai para a empresa inteira."""
    with _conexao() as conn:
        with pytest.raises(PermissionError):
            resolve_unit_scope(conn, ADMIN_SEM_UNIDADE)


def test_perfil_travado_sem_unidade_nega_mesmo_pedindo_uma_valida():
    """O `unit_id` do cliente não é rota de fuga do fail-closed.

    Se o descarte do item anterior fosse implementado como "usa o do cliente
    quando o ator não tem", o perfil travado escolheria a própria unidade —
    exatamente o que a 1.1D-A fecha.
    """
    with _conexao() as conn:
        with pytest.raises(PermissionError):
            resolve_unit_scope(conn, ADMIN_SEM_UNIDADE, '10')


def test_mensagem_de_negacao_e_do_chamador():
    with _conexao() as conn:
        with pytest.raises(PermissionError, match='consultar estoque'):
            resolve_unit_scope(
                conn, ADMIN_SEM_UNIDADE,
                denial_message='Perfil sem unidade operacional ativa para consultar estoque.',
            )


# ═══════════════════════════════════════════════════════════════════════════
# Perfil livre — unidade pedida é validada contra o tenant
# ═══════════════════════════════════════════════════════════════════════════

def test_perfil_livre_sem_selecao_mantem_visao_corporativa():
    with _conexao() as conn:
        escopo = resolve_unit_scope(conn, GERAL)
    assert escopo == UnitScope(None, 'none', False)


@pytest.mark.parametrize('vazio', [None, '', '   ', []])
def test_selecao_vazia_em_qualquer_forma_e_visao_corporativa(vazio):
    with _conexao() as conn:
        escopo = resolve_unit_scope(conn, GERAL, vazio)
    assert escopo.unit_id is None
    assert escopo.source == 'none'


def test_perfil_livre_com_unidade_da_propria_empresa_e_aceito():
    with _conexao() as conn:
        escopo = resolve_unit_scope(conn, GERAL, '11')
    assert escopo == UnitScope(11, 'selected', False)


def test_unidade_de_outro_tenant_e_recusada_com_valueerror():
    """`ValueError` porque `app.py` mapeia `ValueError` → 400, que é o status
    aprovado no contrato da 1.1D-A para `unit_id` externo ao tenant."""
    with _conexao() as conn:
        with pytest.raises(ValueError, match='não pertence'):
            resolve_unit_scope(conn, GERAL, '20')


def test_a_recusa_vale_nos_dois_sentidos():
    """Não é uma lista de empresas privilegiadas: a empresa 2 também não
    alcança a unidade da 1."""
    with _conexao() as conn:
        with pytest.raises(ValueError):
            resolve_unit_scope(conn, GERAL_OUTRA, '10')
        assert resolve_unit_scope(conn, GERAL_OUTRA, '20').unit_id == 20


def test_unidade_inexistente_e_recusada():
    with _conexao() as conn:
        with pytest.raises(ValueError, match='não encontrada'):
            resolve_unit_scope(conn, GERAL, '999')


@pytest.mark.parametrize('lixo', ['abc', '1;DROP', '1.5', '0', '-3'])
def test_unidade_nao_numerica_ou_nao_positiva_e_recusada(lixo):
    with _conexao() as conn:
        with pytest.raises(ValueError):
            resolve_unit_scope(conn, GERAL, lixo)


def test_master_admin_atravessa_tenants_por_desenho():
    """`master_admin` não tem `company_id` próprio; não há tenant contra o qual
    comparar. A checagem é pulada para ele — e só para ele."""
    with _conexao() as conn:
        assert resolve_unit_scope(conn, MASTER, '10').unit_id == 10
        assert resolve_unit_scope(conn, MASTER, '20').unit_id == 20


def test_company_id_nulo_nao_vira_curinga():
    """Um perfil livre sem empresa não passa a alcançar unidades órfãs.

    A comparação é textual (`str(...) == str(...)`); sem esta trava, `None`
    de um lado e `None` do outro casariam e liberariam a unidade.
    """
    with _conexao() as conn:
        conn.execute('INSERT INTO units (id, company_id) VALUES (?, NULL)', (30,))
        conn.commit()
        sem_empresa = {'id': 9, 'role': 'general_admin', 'company_id': None}
        with pytest.raises(ValueError):
            resolve_unit_scope(conn, sem_empresa, '30')


def test_unit_id_e_none_exatamente_quando_source_e_none():
    with _conexao() as conn:
        casos = [
            resolve_unit_scope(conn, GERAL),
            resolve_unit_scope(conn, GERAL, '11'),
            resolve_unit_scope(conn, ADMIN_LOCAL, '11'),
        ]
    for escopo in casos:
        assert (escopo.unit_id is None) == (escopo.source == 'none')
        assert escopo.unit_id != 0, 'zero não é unidade'


# ═══════════════════════════════════════════════════════════════════════════
# Fiação — `/api/stock/epis` usa o helper, e não a linha antiga
# ═══════════════════════════════════════════════════════════════════════════

def _handler_stock_epis() -> str:
    texto = ROUTES.read_text(encoding='utf-8')
    inicio = texto.index('def handle_get_stock_epis')
    fim = texto.index('\ndef ', inicio + 1)
    return texto[inicio:fim]


def _sem_comentarios(fonte: str) -> str:
    """Descarta comentários: eles CITAM o padrão proibido para explicá-lo."""
    return '\n'.join(
        linha for linha in fonte.split('\n')
        if not linha.lstrip().startswith('#')
    )


def test_stock_epis_resolve_a_unidade_pelo_helper():
    corpo = _sem_comentarios(_handler_stock_epis())
    assert 'resolve_unit_scope(' in corpo, (
        '/api/stock/epis voltou a resolver a Unidade por conta própria'
    )


def test_stock_epis_nao_tem_mais_o_or_que_escolhia_a_origem():
    """Sabotagem: reintroduzir o `or query.get('unit_id')` reabre o buraco —
    o `unit_id` do cliente volta a entrar sem validação de tenant."""
    corpo = _sem_comentarios(_handler_stock_epis())
    assert re.search(r"\bor\s+query\.get\(\s*'unit_id'", corpo) is None, (
        'o fallback por truthiness voltou: `unit_id` do cliente entra sem '
        'validação de empresa'
    )
    assert 'actor_operational_unit_id(' not in corpo, (
        'a resolução de Unidade voltou a ser feita direto no handler, fora do '
        'ponto único'
    )


def test_stock_epis_nao_le_unit_id_da_query_fora_do_helper():
    """O único caminho do `unit_id` do cliente até o handler é o helper."""
    corpo = _sem_comentarios(_handler_stock_epis())
    ocorrencias = re.findall(r"query\.get\(\s*'unit_id'[^)]*\)", corpo)
    assert len(ocorrencias) == 1, (
        f'`unit_id` lido da query em {len(ocorrencias)} pontos; deve ser só o '
        'argumento de resolve_unit_scope'
    )
    trecho = corpo[corpo.index('resolve_unit_scope('):]
    assert ocorrencias[0] in trecho.split(')\n')[0] + ')', (
        'a única leitura de `unit_id` não está dentro da chamada do helper'
    )


def test_stock_epis_mantem_a_mensagem_de_negacao_especifica():
    corpo = _handler_stock_epis()
    assert 'para consultar estoque' in corpo, (
        'a mensagem de negação perdeu o contexto da rota ao centralizar a regra'
    )


def test_os_demais_pontos_de_estoque_seguem_no_padrao_antigo():
    """Dívida REGISTRADA, não corrigida — a 1.1D-A aprovada cobre só
    `/api/stock/epis`.

    Outros cinco pontos de `modules/stock/routes.py` continuam com
    `actor_operational_unit_id(...) or query.get('unit_id')`, e um sexto
    (`handle_post_stock_status`) com a variante por payload. Quando forem
    migrados, este número cai e o teste falha pedindo a atualização — que é o
    objetivo: a dívida não some em silêncio, nem cresce em silêncio.
    """
    texto = _sem_comentarios(ROUTES.read_text(encoding='utf-8'))
    restantes = re.findall(r"\bor\s+query\.get\(\s*'unit_id'", texto)
    assert len(restantes) == 5, (
        f'{len(restantes)} pontos ainda resolvem Unidade pelo padrão antigo '
        '(eram 5 ao fim da 1.1D-A). Se migrou algum, atualize este número; se '
        'acrescentou um novo, use resolve_unit_scope.'
    )


# ═══════════════════════════════════════════════════════════════════════════
# SessionContext — `operational_unit_id` vence
# ═══════════════════════════════════════════════════════════════════════════

def _linha_unit_id_dart() -> str:
    for linha in SESSION_CONTEXT.read_text(encoding='utf-8').split('\n'):
        despido = linha.strip()
        if despido.startswith('unitId:') and 'user[' in despido:
            return despido
    raise AssertionError('não achei a montagem de `unitId` em SessionContext')


def test_session_context_prioriza_operational_unit_id():
    """`unit_id` é o vínculo cru do colaborador e não conhece movimentação
    temporária; `operational_unit_id` é o que o backend resolveu. Ler o cru
    primeiro faria a sessão divergir do recorte aplicado no servidor."""
    linha = _linha_unit_id_dart()
    assert "'operational_unit_id'" in linha and "'unit_id'" in linha
    assert linha.index("'operational_unit_id'") < linha.index("'unit_id'"), (
        '`unit_id` cru voltou a ter precedência sobre `operational_unit_id`'
    )


def test_session_context_usa_fallback_e_nao_soma():
    linha = _linha_unit_id_dart()
    assert '??' in linha, 'a precedência deixou de ser um `??`'
