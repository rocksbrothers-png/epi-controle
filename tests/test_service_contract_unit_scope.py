"""Contratos de serviço recortados por Unidade (achado da validação da #226).

A empresa terceirizada é ÚNICA no tenant e pode ter vínculo com várias
Unidades, cada uma com o seu contrato: número, vigência e — o que mais pesa —
``epi_responsibility_override``, que decide quem paga o EPI.

``fetch_service_contracts`` filtrava só por tenant e empresa, ignorando
``service_contracts.unit_id``. Isso ficou invisível enquanto apenas a Unidade
de ORIGEM alcançava a empresa: não havia uma segunda Unidade para vazar
contrato. O fluxo de vínculo da #226 criou essa segunda Unidade — e a validação
ponta a ponta pegou a Unidade Sul lendo ``CT-NORTE-001`` no instante seguinte
ao vínculo.

Uma feature pode tornar alcançável um vazamento que já estava escrito. É por
isso que o roteiro afirma a ausência de herança em vez de presumi-la.
"""

import sqlite3

import pytest

from modules.outsourced_companies.service import fetch_service_contracts

CO, OUTRA_CO = 1, 2
OSC = 10
UNIT_NORTE, UNIT_SUL = 1, 2


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class _PgStyleConn:
    """O service escreve `?`; o wrapper de Postgres traduz. Aqui é sqlite
    direto, então só repassa."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(str(sql).replace('%s', '?'), params)

    def __getattr__(self, name):
        return getattr(self._conn, name)


@pytest.fixture()
def conexao():
    raw = sqlite3.connect(':memory:')
    raw.row_factory = _dict_factory
    raw.executescript(
        '''
        CREATE TABLE service_contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, outsourced_company_id INTEGER NOT NULL,
            unit_id INTEGER, contract_ref TEXT NOT NULL, service_order_ref TEXT DEFAULT '',
            start_date TEXT DEFAULT '', end_date TEXT DEFAULT '',
            epi_responsibility_override TEXT DEFAULT '', override_reason TEXT DEFAULT '',
            status TEXT DEFAULT 'active', created_by_user_id INTEGER,
            created_at TEXT DEFAULT '', updated_at TEXT DEFAULT ''
        );
        '''
    )
    contratos = (
        (CO, OSC, UNIT_NORTE, 'CT-NORTE-001', 'Empresa Terceirizada'),
        (CO, OSC, UNIT_SUL, 'CT-SUL-001', 'Contratante'),
        (CO, OSC, None, 'CT-CORP-001', ''),
        # Mesmo número de contrato em outro tenant: o filtro por company_id
        # não pode ser eclipsado pelo filtro por Unidade.
        (OUTRA_CO, OSC, UNIT_SUL, 'CT-SUL-001', ''),
    )
    for company_id, osc, unit_id, ref, responsabilidade in contratos:
        raw.execute(
            'INSERT INTO service_contracts (company_id, outsourced_company_id, unit_id, '
            'contract_ref, epi_responsibility_override) VALUES (?,?,?,?,?)',
            (company_id, osc, unit_id, ref, responsabilidade),
        )
    raw.commit()
    return _PgStyleConn(raw)


def _refs(contratos):
    return sorted(c['contract_ref'] for c in contratos)


def test_unidade_nao_ve_contrato_de_outra_unidade(conexao):
    # O caso que a validação da #226 flagrou.
    assert 'CT-NORTE-001' not in _refs(fetch_service_contracts(conexao, CO, OSC, scope_unit_id=UNIT_SUL))


def test_unidade_ve_o_proprio_contrato_e_os_corporativos(conexao):
    # `unit_id IS NULL` é contrato de alcance do tenant — some para a Unidade
    # seria o erro oposto, e igualmente ruim: ela deixaria de ver o contrato
    # que de fato a rege.
    assert _refs(fetch_service_contracts(conexao, CO, OSC, scope_unit_id=UNIT_SUL)) == [
        'CT-CORP-001', 'CT-SUL-001',
    ]


def test_perfil_nao_escopado_continua_vendo_todos(conexao):
    # Administrador Geral/de Registro enxergam o tenant inteiro — o recorte é
    # por Unidade do ator, não uma restrição nova para todo mundo.
    assert _refs(fetch_service_contracts(conexao, CO, OSC)) == [
        'CT-CORP-001', 'CT-NORTE-001', 'CT-SUL-001',
    ]


def test_o_recorte_por_unidade_nao_atravessa_tenant(conexao):
    # Duas linhas têm `unit_id = UNIT_SUL`; só a do tenant certo pode voltar.
    contratos = fetch_service_contracts(conexao, CO, OSC, scope_unit_id=UNIT_SUL)
    assert {c['company_id'] for c in contratos} == {CO}


def test_a_responsabilidade_por_epi_de_outra_unidade_nao_vaza(conexao):
    # `epi_responsibility_override` decide quem paga o EPI. Vazá-lo entre
    # Unidades não é só ruído de listagem: é informação contratual de outra
    # operação.
    visiveis = fetch_service_contracts(conexao, CO, OSC, scope_unit_id=UNIT_SUL)
    assert 'Empresa Terceirizada' not in {c['epi_responsibility_override'] for c in visiveis}


def test_a_rota_deriva_o_escopo_do_ator_e_so_para_perfis_escopados():
    """O escopo sai de `actor_operational_unit_id`, nunca do request.

    Aceitar um `unit_id` vindo do cliente devolveria a decisão de escopo a
    quem monta a requisição — o oposto do que a #226 estabeleceu.
    """
    import inspect

    import modules.outsourced_companies.routes as rotas

    corpo = inspect.getsource(rotas.handle_get_service_contracts)
    assert 'scope_unit_id=scope_unit_id' in corpo
    assert 'actor_operational_unit_id(connection, actor)' in corpo
    assert "actor.get('role') in ('admin', 'user')" in corpo
    assert 'parse_qs' not in corpo, 'o escopo não pode vir da query string'
