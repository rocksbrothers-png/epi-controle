"""`GET /api/dashboard/summary` — escopo, KPIs e filtros no servidor (1.1D-B).

Hoje o Dashboard não tem rota. O `DashboardCubit` baixa `/api/bootstrap`
inteiro e recomputa os KPIs em Dart; o Web Legado faz o mesmo em
`dashboard.js`, com outro código. Duas reimplementações da mesma regra.

Esta fatia move escopo, KPIs e fontes do filtro para o servidor **sem migrar
nenhum consumidor**: o bootstrap segue emitindo tudo, e os dois clientes seguem
lendo de lá.

Duas classes de teste, deliberadamente diferentes:

- **equivalência** para `deliveries_today`, `expiring_epis` e
  `pending_purchases`: reproduzem o comportamento atual, e o teste compara
  contra uma reimplementação da regra do cliente sobre os mesmos dados;
- **divergência PROVADA** para `critical_stock`: a regra mudou de propósito
  (`unit_stock_quantity <= unit_minimum_stock`, fatia 1.1D-B0) e o teste
  demonstra que o número novo difere do antigo — casar os dois seria manter o
  defeito.
"""

import pathlib
import re
import sqlite3
from datetime import date, timedelta

import pytest

from modules.dashboard.service import build_dashboard_summary
from modules.stock.service import is_stock_critical

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SERVICE = RAIZ / 'modules/dashboard/service.py'
ROUTES = RAIZ / 'modules/dashboard/routes.py'
APP = RAIZ / 'app.py'

HOJE = date.today()
ONTEM = HOJE - timedelta(days=1)
DAQUI_10 = HOJE + timedelta(days=10)
DAQUI_90 = HOJE + timedelta(days=90)

MASTER = {'id': 1, 'role': 'master_admin', 'company_id': None, 'linked_employee_id': None}
GERAL = {'id': 2, 'role': 'general_admin', 'company_id': 1, 'linked_employee_id': None}
GESTOR_A = {'id': 5, 'role': 'user', 'company_id': 1, 'linked_employee_id': 50}
GESTOR_SEM_UNIDADE = {'id': 6, 'role': 'user', 'company_id': 1, 'linked_employee_id': None}


class _PgStyleConn:
    """Traduz `%s` para `?`, como o wrapper de Postgres em produção.

    Várias consultas do projeto (`get_unit_active_jv_name`, entre outras) têm
    `%s` fixo no texto. Sem esta ponte elas quebram contra sqlite direto — o
    mesmo molde já usado em `test_stock_minimum_scope.py`.
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(str(sql).replace('%s', '?'), params)

    def commit(self):
        self._conn.commit()

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        self._conn.close()
        return False

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _conexao():
    """Empresa 1: CNPJ 4 com Unidades 10 e 11; CNPJ 5 com a Unidade 12.

    EPI 7 (mínimo corporativo 100) com saldos 30 / 30 / 40 — o caso da 1.1D-B0.
    EPI 8 é de nível empresa (`unit_id` nulo) com CA vencendo em 10 dias.
    """
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        '''
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, legal_entity_id INTEGER, name TEXT);
        CREATE TABLE employees (id INTEGER PRIMARY KEY, unit_id INTEGER, sector TEXT);
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER, movement_type TEXT, start_date TEXT,
            end_date TEXT DEFAULT '', target_unit_id INTEGER
        );
        CREATE TABLE epis (id INTEGER PRIMARY KEY, company_id INTEGER, minimum_stock INTEGER);
        CREATE TABLE unit_epi_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER, unit_id INTEGER, epi_id INTEGER, quantity INTEGER
        );
        CREATE TABLE unit_epi_minimum_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            minimum_stock INTEGER NOT NULL DEFAULT 0,
            created_by_user_id INTEGER, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE (company_id, unit_id, epi_id)
        );
        -- #271: faixa de atenção e liga/desliga do alerta. Sem linhas — a
        -- ausência É a herança (20% da empresa, alerta habilitado).
        CREATE TABLE company_stock_attention_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL UNIQUE,
            attention_percentage INTEGER NOT NULL DEFAULT 20, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE unit_epi_attention_percentage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            attention_percentage INTEGER NOT NULL DEFAULT 0,
            created_by_user_id INTEGER, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE (company_id, unit_id, epi_id)
        );
        CREATE TABLE unit_epi_stock_alert_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            alert_enabled INTEGER NOT NULL DEFAULT 1,
            created_by_user_id INTEGER, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE (company_id, unit_id, epi_id)
        );
        CREATE TABLE unit_epi_stock_config_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            parameter TEXT NOT NULL, previous_value TEXT, new_value TEXT NOT NULL,
            previous_source TEXT NOT NULL DEFAULT '', actor_user_id INTEGER,
            actor_name TEXT NOT NULL DEFAULT '', actor_role TEXT NOT NULL DEFAULT '',
            ip_address TEXT NOT NULL DEFAULT '', user_agent TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE unit_joint_venture_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_id INTEGER NOT NULL, joint_venture_name TEXT, started_at TEXT, ended_at TEXT
        );
        '''
    )
    conn.executemany(
        'INSERT INTO units (id, company_id, legal_entity_id, name) VALUES (?, 1, ?, ?)',
        [(10, 4, 'Skandi Paraty'), (11, 4, 'Skandi Amazonas'), (12, 5, 'Norskan Alpha')],
    )
    conn.executemany(
        'INSERT INTO employees (id, unit_id, sector) VALUES (?, ?, ?)',
        [(50, 10, 'Convés'), (51, 10, 'Máquinas'), (52, 11, 'Convés'), (53, 12, 'Cozinha')],
    )
    conn.executemany(
        'INSERT INTO epis (id, company_id, minimum_stock) VALUES (?, 1, ?)',
        [(7, 100), (8, 100)],
    )
    conn.executemany(
        'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity) VALUES (1, ?, 7, ?)',
        [(10, 30), (11, 30), (12, 40)],
    )
    conn.commit()
    return _PgStyleConn(conn)


UNIDADES = [
    {'id': 10, 'company_id': 1, 'legal_entity_id': 4, 'name': 'Skandi Paraty'},
    {'id': 11, 'company_id': 1, 'legal_entity_id': 4, 'name': 'Skandi Amazonas'},
    {'id': 12, 'company_id': 1, 'legal_entity_id': 5, 'name': 'Norskan Alpha'},
]
COLABORADORES = [
    {'id': 50, 'unit_id': 10, 'sector': 'Convés'},
    {'id': 51, 'unit_id': 10, 'sector': 'Máquinas'},
    {'id': 52, 'unit_id': 11, 'sector': 'Convés'},
    {'id': 53, 'unit_id': 12, 'sector': 'Cozinha'},
]
CNPJS = [
    {'id': 4, 'trade_name': 'Skandi', 'legal_name': 'Skandi LTDA', 'cnpj': '00.000.000/0001-00'},
    {'id': 5, 'trade_name': '', 'legal_name': 'Norskan SA', 'cnpj': '00.000.000/0002-00'},
]
ENTREGAS = [
    {'id': 1, 'unit_id': 10, 'sector': 'Convés', 'delivery_date': HOJE.isoformat()},
    {'id': 2, 'unit_id': 10, 'sector': 'Máquinas', 'delivery_date': HOJE.isoformat()},
    {'id': 3, 'unit_id': 11, 'sector': 'Convés', 'delivery_date': HOJE.isoformat()},
    {'id': 4, 'unit_id': 10, 'sector': 'Convés', 'delivery_date': ONTEM.isoformat()},
    # Sem data operacional: cai em `created_at`, como no cliente.
    {'id': 5, 'unit_id': 12, 'sector': 'Cozinha', 'delivery_date': '',
     'created_at': f'{HOJE.isoformat()}T08:30:00'},
]
EPIS = [
    {'id': 7, 'company_id': 1, 'unit_id': 10, 'ca_expiry': DAQUI_10.isoformat()},
    {'id': 8, 'company_id': 1, 'unit_id': None, 'ca_expiry': DAQUI_10.isoformat()},
    {'id': 9, 'company_id': 1, 'unit_id': 11, 'ca_expiry': DAQUI_90.isoformat()},
    {'id': 10, 'company_id': 1, 'unit_id': 10, 'ca_expiry': ONTEM.isoformat()},
]


def _resumo(conn, actor, *, unit_id=None, legal_entity_id=None, sector=None,
            epis=None, entregas=None, pendentes=0, alertas=None, conformidade=None):
    return build_dashboard_summary(
        conn, actor,
        requested_unit_id=unit_id,
        requested_legal_entity_id=legal_entity_id,
        requested_sector=sector,
        fetch_units=lambda c, a: list(UNIDADES),
        fetch_employees=lambda c, a: list(COLABORADORES),
        fetch_epis=lambda c, a, u: list(EPIS if epis is None else epis),
        fetch_deliveries=lambda c, a: list(ENTREGAS if entregas is None else entregas),
        fetch_legal_entities=lambda c, a: list(CNPJS),
        compute_alerts=lambda c, a: list(alertas or []),
        compute_stock_compliance=lambda c, cid, uid: dict(conformidade or {'summary': {}}),
        count_pending_purchases=lambda: pendentes,
    )


# ═══════════════════════════════════════════════════════════════════════════
# scope — vem do servidor, não é deduzido no cliente
# ═══════════════════════════════════════════════════════════════════════════

def test_perfil_travado_recebe_locked_e_a_propria_unidade():
    with _conexao() as conn:
        escopo = _resumo(conn, GESTOR_A)['scope']
    assert escopo['unit_id'] == 10
    assert escopo['unit_scope_source'] == 'actor'
    assert escopo['locked'] is True


def test_perfil_travado_nao_troca_de_unidade_pela_query():
    with _conexao() as conn:
        escopo = _resumo(conn, GESTOR_A, unit_id='11')['scope']
    assert escopo['unit_id'] == 10, 'perfil travado trocou de Unidade pelo payload'
    assert escopo['locked'] is True


def test_perfil_livre_sem_selecao_nao_tem_unidade():
    with _conexao() as conn:
        escopo = _resumo(conn, GERAL)['scope']
    assert escopo['unit_id'] is None
    assert escopo['unit_scope_source'] == 'none'
    assert escopo['locked'] is False


def test_perfil_livre_com_unidade_da_propria_empresa():
    with _conexao() as conn:
        escopo = _resumo(conn, GERAL, unit_id='11')['scope']
    assert escopo['unit_id'] == 11
    assert escopo['unit_scope_source'] == 'selected'
    assert escopo['locked'] is False


def test_unidade_de_outro_tenant_e_recusada():
    """`ValueError` → 400, contrato herdado da 1.1D-A."""
    with _conexao() as conn:
        conn.execute('INSERT INTO units (id, company_id, legal_entity_id, name) '
                     "VALUES (99, 2, 9, 'De outra empresa')")
        conn.commit()
        with pytest.raises(ValueError):
            _resumo(conn, GERAL, unit_id='99')


def test_perfil_travado_sem_unidade_e_fail_closed():
    with _conexao() as conn:
        with pytest.raises(PermissionError, match='painel'):
            _resumo(conn, GESTOR_SEM_UNIDADE)


def test_o_cnpj_do_perfil_travado_deriva_da_unidade():
    """Perfil travado não escolhe CNPJ: ele vem de `units.legal_entity_id`.

    Aceitar o CNPJ do payload aqui abriria a cascata por um caminho lateral,
    justamente para o perfil que não deve escolher nada.
    """
    with _conexao() as conn:
        escopo = _resumo(conn, GESTOR_A, legal_entity_id='5')['scope']
    assert escopo['legal_entity_id'] == 4, 'perfil travado escolheu CNPJ pelo payload'


# ═══════════════════════════════════════════════════════════════════════════
# critical_stock — três estados distintos
# ═══════════════════════════════════════════════════════════════════════════

def test_critical_stock_null_sem_contexto_de_unidade():
    """`None` não é "nada crítico": é "a pergunta não se aplica"."""
    with _conexao() as conn:
        kpis = _resumo(conn, GERAL)['kpis']
    assert kpis['critical_stock'] is None
    # Não é 0 disfarçado: `0 == False` e `None == False` são ambos falsos em
    # Python, mas só `None` sobrevive ao JSON como `null`. Checar o TIPO é o
    # que distingue "sem resposta" de "resposta zero" na serialização.
    assert not isinstance(kpis['critical_stock'], int)


def test_critical_stock_zero_com_unidade_e_nenhum_epi_critico():
    with _conexao() as conn:
        # Mínimo 5 contra saldo 30: folgado.
        conn.execute('INSERT INTO unit_epi_minimum_stock (company_id, unit_id, epi_id, minimum_stock) '
                     'VALUES (1, 10, 7, 5)')
        conn.commit()
        kpis = _resumo(conn, GERAL, unit_id='10', epis=[EPIS[0]])['kpis']
    assert kpis['critical_stock'] == 0, 'Unidade resolvida sem críticos deve ser 0, não null'


def test_saldo_zero_com_minimo_zero_e_critico():
    """`0 <= 0` é crítico, e isso é a regra — não um efeito colateral.

    A Unidade que configura mínimo 0 está dizendo "só me avise ao zerar". É
    exatamente quando o saldo chega a zero que ela quer o alerta.
    """
    with _conexao() as conn:
        conn.execute('DELETE FROM unit_epi_stock WHERE unit_id = 10 AND epi_id = 7')
        conn.execute('INSERT INTO unit_epi_minimum_stock (company_id, unit_id, epi_id, minimum_stock) '
                     'VALUES (1, 10, 7, 0)')
        conn.commit()
        kpis = _resumo(conn, GERAL, unit_id='10', epis=[EPIS[0]])['kpis']
    assert kpis['critical_stock'] == 1


def test_epi_de_outra_unidade_nao_entra_na_contagem():
    """Visibilidade GLOBAL/JV vale para o KPI: contar EPI que a Unidade nem
    enxerga na tela de estoque inflaria o painel com item que ela não opera."""
    with _conexao() as conn:
        de_outra_unidade = [{'id': 9, 'company_id': 1, 'unit_id': 11}]
        assert _resumo(conn, GERAL, unit_id='10', epis=de_outra_unidade)['kpis']['critical_stock'] == 0


def test_critical_stock_maior_que_zero_conta_os_criticos_da_unidade():
    with _conexao() as conn:
        conn.execute('INSERT INTO unit_epi_minimum_stock (company_id, unit_id, epi_id, minimum_stock) '
                     'VALUES (1, 10, 7, 40)')
        conn.commit()
        kpis = _resumo(conn, GERAL, unit_id='10',
                       epis=[EPIS[0]])['kpis']
    assert kpis['critical_stock'] == 1  # saldo 30 <= mínimo 40


def test_os_tres_estados_sao_distinguiveis():
    """`null`, `0` e `>0` significam coisas diferentes e o teste exige as três."""
    with _conexao() as conn:
        conn.execute('INSERT INTO unit_epi_minimum_stock (company_id, unit_id, epi_id, minimum_stock) '
                     'VALUES (1, 10, 7, 40), (1, 11, 7, 5)')
        conn.commit()
        sem_unidade = _resumo(conn, GERAL, epis=[EPIS[0]])['kpis']['critical_stock']
        critico = _resumo(conn, GERAL, unit_id='10', epis=[EPIS[0]])['kpis']['critical_stock']
        tranquilo = _resumo(conn, GERAL, unit_id='11', epis=[EPIS[0]])['kpis']['critical_stock']

    assert sem_unidade is None
    assert critico == 1
    assert tranquilo == 0
    assert sem_unidade != tranquilo, 'null e 0 colapsaram no mesmo valor'


def test_o_caso_100_30_30_40_com_a_regra_nova():
    """A divergência com o KPI antigo é PROVADA, não evitada.

    Antes: `stockQuantity <= minimumStock` → 100 <= 100 → crítico para TODA
    Unidade, porque o operando era o total da empresa contra o mínimo da
    empresa. O número era o mesmo em qualquer Unidade — o que já denuncia que
    ele não falava de nenhuma.

    Agora cada Unidade responde pelo próprio parâmetro.
    """
    with _conexao() as conn:
        conn.execute('INSERT INTO unit_epi_minimum_stock (company_id, unit_id, epi_id, minimum_stock) '
                     'VALUES (1, 10, 7, 40), (1, 11, 7, 25), (1, 12, 7, 40)')
        conn.commit()
        epi = [{'id': 7, 'company_id': 1, 'unit_id': None}]
        novo = {
            u: _resumo(conn, GERAL, unit_id=str(u), epis=epi)['kpis']['critical_stock']
            for u in (10, 11, 12)
        }

    assert novo == {10: 1, 11: 0, 12: 1}, \
        'saldos 30/30/40 contra mínimos 40/25/40 — a Unidade 11 não é crítica'

    # A regra ANTIGA, computada de verdade sobre os mesmos dados: saldo
    # corporativo (soma das Unidades) contra `epis.minimum_stock`. Não é
    # literal — sai do banco, senão a comparação abaixo seria tautologia.
    with _conexao() as conn:
        corporativo = conn.execute(
            'SELECT SUM(quantity) AS saldo FROM unit_epi_stock '
            'WHERE company_id = 1 AND epi_id = 7'
        ).fetchone()['saldo']
        minimo_da_empresa = conn.execute(
            'SELECT minimum_stock FROM epis WHERE id = 7'
        ).fetchone()['minimum_stock']

    # O veredito antigo é UM SÓ para as três Unidades — ele não conseguia
    # distingui-las, porque nenhum dos dois operandos era delas.
    antigo = is_stock_critical(corporativo, minimo_da_empresa)
    assert antigo is True, 'o cenário perdeu a propriedade que o torna interessante'
    # A regra antiga daria ESTE MESMO veredito para as três Unidades — nenhum
    # dos seus operandos era delas. A nova não pode colapsar de volta nisso.
    assert set(novo.values()) != {1 if antigo else 0}, \
        'a regra nova voltou a dar o mesmo veredito para todas as Unidades'
    assert novo[11] == 0, \
        'o KPI voltou a usar o mínimo corporativo e a Unidade 11 virou crítica de novo'


def test_sem_linha_de_saldo_a_unidade_tem_zero_e_e_critica():
    """Ausência em `unit_epi_stock` é saldo zero, não "sem dado" — e zero contra
    mínimo positivo precisa aparecer no painel."""
    with _conexao() as conn:
        conn.execute('DELETE FROM unit_epi_stock WHERE unit_id = 10')
        conn.execute('INSERT INTO unit_epi_minimum_stock (company_id, unit_id, epi_id, minimum_stock) '
                     'VALUES (1, 10, 7, 5)')
        conn.commit()
        kpis = _resumo(conn, GERAL, unit_id='10', epis=[EPIS[0]])['kpis']
    assert kpis['critical_stock'] == 1


# ═══════════════════════════════════════════════════════════════════════════
# Equivalência com o comportamento atual do cliente
# ═══════════════════════════════════════════════════════════════════════════

def _deliveries_today_como_o_cliente(entregas, unidades_no_escopo, setor):
    """Reimplementação da regra do `DashboardCubit` sobre os mesmos dados."""
    hoje_iso = HOJE.isoformat()
    total = 0
    for d in entregas:
        if unidades_no_escopo is not None and d.get('unit_id') not in unidades_no_escopo:
            continue
        if setor is not None and str(d.get('sector') or '') != setor:
            continue
        texto = d.get('delivery_date') or d.get('created_at') or ''
        if str(texto).startswith(hoje_iso):
            total += 1
    return total


def _expiring_epis_como_o_cliente(epis, unidades_no_escopo):
    total = 0
    for e in epis:
        unidade = e.get('unit_id')
        if unidade is not None and unidades_no_escopo is not None \
                and unidade not in unidades_no_escopo:
            continue
        quando = e.get('ca_expiry')
        if not quando:
            continue
        alvo = date.fromisoformat(quando)
        if HOJE <= alvo < HOJE + timedelta(days=30):
            total += 1
    return total


@pytest.mark.parametrize('unidade,escopo', [(None, None), ('10', {10}), ('11', {11})])
def test_deliveries_today_equivale_ao_calculo_do_cliente(unidade, escopo):
    with _conexao() as conn:
        servidor = _resumo(conn, GERAL, unit_id=unidade)['kpis']['deliveries_today']
    assert servidor == _deliveries_today_como_o_cliente(ENTREGAS, escopo, None)


def test_deliveries_today_respeita_o_filtro_de_setor():
    with _conexao() as conn:
        servidor = _resumo(conn, GERAL, unit_id='10', sector='Convés')['kpis']['deliveries_today']
    assert servidor == _deliveries_today_como_o_cliente(ENTREGAS, {10}, 'Convés') == 1


def test_entrega_sem_data_operacional_usa_created_at():
    with _conexao() as conn:
        servidor = _resumo(conn, GERAL, unit_id='12')['kpis']['deliveries_today']
    assert servidor == 1, '`created_at` deixou de ser a data reserva da entrega'


def test_entrega_de_ontem_nao_conta():
    with _conexao() as conn:
        so_ontem = [ENTREGAS[3]]
        assert _resumo(conn, GERAL, unit_id='10', entregas=so_ontem)['kpis']['deliveries_today'] == 0


@pytest.mark.parametrize('unidade,escopo', [(None, None), ('10', {10}), ('11', {11})])
def test_expiring_epis_equivale_ao_calculo_do_cliente(unidade, escopo):
    with _conexao() as conn:
        servidor = _resumo(conn, GERAL, unit_id=unidade)['kpis']['expiring_epis']
    assert servidor == _expiring_epis_como_o_cliente(EPIS, escopo)


def test_epi_corporativo_conta_em_qualquer_recorte():
    """EPI de nível empresa (`unit_id` nulo) não pertence a uma Unidade.

    Escondê-lo ao filtrar por Unidade faria sumir do painel um CA prestes a
    vencer que afeta todas elas. Regra atual do cliente, preservada.
    """
    with _conexao() as conn:
        corporativo = [EPIS[1]]
        for unidade in (None, '10', '11', '12'):
            assert _resumo(conn, GERAL, unit_id=unidade, epis=corporativo)['kpis']['expiring_epis'] == 1


def test_epi_ja_vencido_nao_conta_como_a_vencer():
    """'expired' não é 'expiring'. Vencidos têm categoria própria em
    `compliance`; contá-los aqui inflaria o KPI de atenção."""
    with _conexao() as conn:
        vencido = [EPIS[3]]
        assert _resumo(conn, GERAL, unit_id='10', epis=vencido)['kpis']['expiring_epis'] == 0


def test_epi_com_validade_distante_nao_conta():
    with _conexao() as conn:
        distante = [EPIS[2]]
        assert _resumo(conn, GERAL, unit_id='11', epis=distante)['kpis']['expiring_epis'] == 0


def test_pending_purchases_vem_do_backend_sem_recorte_no_cliente():
    with _conexao() as conn:
        assert _resumo(conn, GERAL, pendentes=7)['kpis']['pending_purchases'] == 7


# ═══════════════════════════════════════════════════════════════════════════
# filters — a rota é autossuficiente
# ═══════════════════════════════════════════════════════════════════════════

def test_setores_vem_do_servidor_ja_recortados():
    with _conexao() as conn:
        todos = _resumo(conn, GERAL)['filters']['sectors']
        da_unidade_10 = _resumo(conn, GERAL, unit_id='10')['filters']['sectors']
    assert todos == ['Convés', 'Cozinha', 'Máquinas'], 'setores devem vir ordenados e sem repetição'
    assert da_unidade_10 == ['Convés', 'Máquinas']


def test_perfil_travado_so_enxerga_a_propria_unidade_no_filtro():
    """A trava vira fato da resposta, não regra reimplementada em dois clientes."""
    with _conexao() as conn:
        filtros = _resumo(conn, GESTOR_A)['filters']
    assert [u['id'] for u in filtros['units']] == [10]
    assert filtros['sectors'] == ['Convés', 'Máquinas']


def test_unidades_trazem_o_cnpj_para_a_cascata():
    with _conexao() as conn:
        unidades = _resumo(conn, GERAL)['filters']['units']
    assert {u['id']: u['legal_entity_id'] for u in unidades} == {10: 4, 11: 4, 12: 5}


def test_cnpj_sem_nome_fantasia_cai_na_razao_social():
    with _conexao() as conn:
        cnpjs = _resumo(conn, GERAL)['filters']['legal_entities']
    assert cnpjs == [{'id': 4, 'name': 'Skandi'}, {'id': 5, 'name': 'Norskan SA'}]


def test_filtrar_por_cnpj_recorta_as_unidades_do_cnpj():
    with _conexao() as conn:
        setores = _resumo(conn, GERAL, legal_entity_id='5')['filters']['sectors']
    assert setores == ['Cozinha'], 'o recorte por CNPJ não alcançou os setores'


def test_cnpj_sem_unidades_zera_em_vez_de_abrir_para_a_empresa():
    """Conjunto vazio e `None` são coisas diferentes: vazio fecha o recorte.

    Trocar um pelo outro é como um filtro sem correspondência acabaria
    mostrando a empresa inteira.
    """
    with _conexao() as conn:
        resumo = _resumo(conn, GERAL, legal_entity_id='999')
    assert resumo['filters']['sectors'] == []
    assert resumo['kpis']['deliveries_today'] == 0


# ═══════════════════════════════════════════════════════════════════════════
# alerts e compliance — repassados sem mudar a regra
# ═══════════════════════════════════════════════════════════════════════════

def test_alerts_sao_repassados_sem_alteracao():
    alertas = [{'type': 'danger', 'category': 'stock', 'title': 'X'}]
    with _conexao() as conn:
        assert _resumo(conn, GERAL, alertas=alertas)['alerts'] == alertas


def test_compliance_e_repassado_sem_alteracao():
    conformidade = {'summary': {'ca_expired': 2}, 'categories': {}}
    with _conexao() as conn:
        assert _resumo(conn, GERAL, conformidade=conformidade)['compliance'] == conformidade


def test_sem_empresa_a_conformidade_e_vazia_e_nao_derruba_o_painel():
    """`master_admin` não tem empresa própria: painel legítimo, sem essa seção."""
    with _conexao() as conn:
        resumo = _resumo(conn, MASTER)
    assert resumo['compliance'] == {}
    assert resumo['scope']['company_id'] is None


# ═══════════════════════════════════════════════════════════════════════════
# Fiação e sabotagem
# ═══════════════════════════════════════════════════════════════════════════

def _sem_comentarios(fonte: str) -> str:
    return '\n'.join(l for l in fonte.split('\n') if not l.lstrip().startswith('#'))


def test_a_rota_esta_registrada_e_gateada_por_permissao():
    corpo = ROUTES.read_text(encoding='utf-8')
    assert "'/api/dashboard/summary'" in corpo
    assert "'dashboard:view'" in corpo, 'a rota do painel ficou sem gate de permissão'
    assert '_reg_dashboard(router)' in APP.read_text(encoding='utf-8')


def test_a_unidade_vem_do_ponto_unico_de_resolucao():
    """Sabotagem: resolver a Unidade aqui de novo reabre o buraco fechado na
    1.1D-A — `unit_id` do cliente sem validação de tenant."""
    corpo = _sem_comentarios(SERVICE.read_text(encoding='utf-8'))
    assert 'resolve_unit_scope(' in corpo
    # `actor_operational_unit_id` mesmo aliasado (`as _aoui`) — um `import ...
    # as` escaparia de uma busca pelo nome da chamada, que foi como uma
    # sabotagem passou na primeira medição.
    assert 'actor_operational_unit_id' not in corpo, \
        'a resolução de Unidade voltou a ser feita fora do ponto único'
    assert not re.search(r"\bor\s+\w*requested_unit_id", corpo), \
        'voltou o fallback por truthiness na escolha da Unidade'
    # O `escopo` sai do helper e não é reescrito depois: `_replace` num
    # NamedTuple é a forma silenciosa de devolver ao cliente o poder de
    # escolher a Unidade.
    assert '_replace(' not in corpo, \
        'o escopo resolvido foi reescrito depois do helper'


def test_a_criticidade_usa_o_minimo_da_unidade():
    """Na #271 o KPI passou a contar por `stock_status`, da fonte única.

    `resolve_unit_minimum_stock` continua sendo a origem do mínimo, mas agora
    de dentro de `classify_unit_epi_stock` — que também aplica a faixa de
    atenção e o liga/desliga do alerta. O painel não pode montar nenhuma das
    três regras por conta própria.
    """
    corpo = _sem_comentarios(SERVICE.read_text(encoding='utf-8'))
    assert 'classify_unit_epi_stock(' in corpo, \
        'o KPI voltou a sair de fora da fonte única de classificação'
    assert not re.search(r"minimum_stock['\"]\s*\)", corpo), \
        'o painel voltou a ler `epis.minimum_stock` direto'
    assert 'is_stock_critical(' not in corpo, \
        'o painel voltou a comparar saldo com mínimo por conta própria'


def test_disabled_nao_entra_em_nenhum_dos_dois_kpis():
    """Contar por `stock_status` (e não por `underlying_status`) é o que tira
    o EPI desabilitado dos dois KPIs sem transformá-lo em `normal`."""
    corpo = _sem_comentarios(SERVICE.read_text(encoding='utf-8'))
    assert 'classificacao.stock_status == status_alvo' in corpo
    # A docstring do contador CITA `underlying_status` para explicar a escolha;
    # o que não pode existir é o uso dele como operando da contagem.
    assert 'classificacao.underlying_status' not in corpo, \
        'o KPI passou a contar pela condição física, ignorando o liga/desliga'


def test_a_fatia_nao_migrou_nenhum_consumidor():
    """Escopo da 1.1D-B: rota nova, nada trocado.

    `DashboardCubit` e `dashboard.js` seguem no bootstrap, e nenhum campo sai
    de lá. Quando forem migrados, este teste falha pedindo a atualização.
    """
    cubit = (RAIZ / 'flutter/apps/epi_admin/lib/core/bloc/dashboard_cubit.dart').read_text(encoding='utf-8')
    assert 'ApiClient.auth.bootstrap()' in cubit, \
        'o DashboardCubit foi migrado — atualize este teste e a fatia 1.1D-C'
    assert '/api/dashboard/summary' not in cubit

    bootstrap = (RAIZ / 'modules/auth/service.py').read_text(encoding='utf-8')
    for campo in ("'deliveries'", "'epis'", "'employees'", "'legal_entities'",
                  "'units'", "'alerts'", "'pending_purchases'"):
        assert campo in bootstrap, f'{campo} foi removido do bootstrap nesta fatia'


def test_alerts_mantem_a_mesma_fiacao_do_bootstrap():
    """`alerts` sai desta fatia com a regra ERRADA de propósito.

    Ela cruza saldo local com mínimo corporativo (via `fetch_low_stock_items`) e
    está rastreada para correção. Consertar só aqui faria o mesmo painel mostrar
    números diferentes conforme a fonte durante a janela de migração.
    """
    corpo = ROUTES.read_text(encoding='utf-8')
    assert 'fetch_low_stock_items' in corpo
    assert 'resolve_unit_minimum_stock' not in corpo, \
        'a regra de alerts foi corrigida nesta fatia; ela pertence à issue de dívida'
