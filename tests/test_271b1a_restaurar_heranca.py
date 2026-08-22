"""#271-B1a — restaurar herança das três configurações por Unidade + EPI.

Antes desta fatia não havia NENHUM `DELETE` nas três tabelas de configuração:
dava para personalizar mínimo, percentual e alerta de uma Unidade, e não dava
para desfazer. "Restaurar padrão" simplesmente não existia.

Duas coisas que esta fatia trava:

**Restaurar ≠ reativar.** `set_unit_epi_alert_enabled(True)` REATIVA e o par
continua `unit_configured` — a Unidade decidiu manter ligado.
`clear_unit_epi_alert_enabled` apaga a decisão e devolve ao `system_default`.
As duas terminam com o alerta LIGADO e significam coisas opostas; tratá-las
como equivalentes apagaria quem decidiu.

**Isolamento entre Unidades.** A chave é `(company_id, unit_id, epi_id)`, mas
"isola por construção" é afirmação, não prova: os testes abaixo alteram e
restauram na Unidade A e conferem B e C.

Esta fatia também abriu a escrita para Administrador Geral e de Registro, que
antes não podiam configurar Unidade nenhuma. A Unidade deles vem do payload —
e é validada contra o tenant no servidor, nunca aceita de confiança.
"""

import io
import json
import sqlite3

import pytest

from modules.stock import routes
from modules.stock.service import (
    clear_unit_epi_alert_enabled,
    clear_unit_epi_attention_percentage,
    clear_unit_epi_minimum_stock,
    resolve_unit_attention_percentage,
    resolve_unit_epi_alert_enabled,
    resolve_unit_minimum_stock,
    set_unit_epi_alert_enabled,
    set_unit_epi_attention_percentage,
    set_unit_epi_minimum_stock,
)

ATOR = {'id': 1, 'full_name': 'Gestor', 'role': 'user'}


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class _PgStyleConn:
    """Traduz `%s` para `?`, como o wrapper de Postgres em produção."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(str(sql).replace('%s', '?'), params)

    def close(self):
        """No-op: as rotas usam `with closing(get_connection())` e fechariam a
        conexão do teste antes das asserções. Quem abriu aqui é quem fecha."""

    def __getattr__(self, name):
        return getattr(self._conn, name)


@pytest.fixture()
def conn():
    raw = sqlite3.connect(':memory:')
    raw.row_factory = _dict_factory
    raw.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, name TEXT);
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT);
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER,
            movement_type TEXT, start_date TEXT, end_date TEXT DEFAULT '',
            target_unit_id INTEGER);
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT DEFAULT '',
            purchase_code TEXT DEFAULT '', ca TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
            unit_measure TEXT DEFAULT '', glove_size TEXT DEFAULT '', size TEXT DEFAULT '',
            uniform_size TEXT DEFAULT '', active_joinventure TEXT,
            scope_type TEXT DEFAULT 'GLOBAL', minimum_stock INTEGER NOT NULL DEFAULT 10);
        CREATE TABLE unit_epi_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0, updated_at TEXT);
        CREATE TABLE unit_joint_venture_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT, unit_id INTEGER NOT NULL,
            joint_venture_name TEXT, started_at TEXT, ended_at TEXT);
        CREATE TABLE unit_epi_minimum_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            minimum_stock INTEGER NOT NULL DEFAULT 0,
            created_by_user_id INTEGER, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE (company_id, unit_id, epi_id));
        CREATE TABLE unit_epi_minimum_stock_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            action TEXT NOT NULL DEFAULT 'set',
            previous_minimum_stock INTEGER, new_minimum_stock INTEGER NOT NULL,
            previous_source TEXT NOT NULL DEFAULT '', actor_user_id INTEGER,
            actor_name TEXT NOT NULL DEFAULT '', actor_role TEXT NOT NULL DEFAULT '',
            ip_address TEXT NOT NULL DEFAULT '', user_agent TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL);
        CREATE TABLE company_stock_attention_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL UNIQUE,
            attention_percentage INTEGER NOT NULL DEFAULT 20, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '');
        CREATE TABLE unit_epi_attention_percentage (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            attention_percentage INTEGER NOT NULL DEFAULT 0,
            created_by_user_id INTEGER, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE (company_id, unit_id, epi_id));
        CREATE TABLE unit_epi_stock_alert_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            alert_enabled INTEGER NOT NULL DEFAULT 1,
            created_by_user_id INTEGER, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE (company_id, unit_id, epi_id));
        CREATE TABLE unit_epi_stock_config_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL, parameter TEXT NOT NULL,
            previous_value TEXT, new_value TEXT NOT NULL,
            previous_source TEXT NOT NULL DEFAULT '', actor_user_id INTEGER,
            actor_name TEXT NOT NULL DEFAULT '', actor_role TEXT NOT NULL DEFAULT '',
            ip_address TEXT NOT NULL DEFAULT '', user_agent TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL);
        INSERT INTO companies (id, name) VALUES (1, 'Norskan'), (2, 'Outro Tenant');
        INSERT INTO units (id, company_id, name) VALUES
            (10, 1, 'A'), (11, 1, 'B'), (12, 1, 'C'), (90, 2, 'Alheia');
        INSERT INTO epis (id, company_id, unit_id, name, scope_type, minimum_stock)
            VALUES (5, 1, NULL, 'Capacete', 'GLOBAL', 100);
        INSERT INTO employees (id, company_id, unit_id, name) VALUES (77, 1, 10, 'Gestor A');
        """
    )
    raw.commit()
    return _PgStyleConn(raw)


A, B, C, ALHEIA, EPI = 10, 11, 12, 90, 5


@pytest.fixture(autouse=True)
def _sqlite(monkeypatch):
    import epi_backend.db as db_module
    monkeypatch.setattr(db_module, '_is_sqlite_connection', lambda _c: True)


def _rota(conn, monkeypatch, handler_fn, actor, payload):
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(routes, 'get_connection', lambda: conn)

    class _H:
        path = '/api/stock'
        def send_response(self, *_a, **_k): pass
        def send_header(self, *_a, **_k): pass
        def end_headers(self): pass

    h = _H()
    h.wfile = io.BytesIO()
    handler_fn(h, None, {'actor_user_id': actor['id'], **payload}, None)
    return json.loads(h.wfile.getvalue().decode('utf-8'))


# ── restaurar devolve à herança ──────────────────────────────────────────────

def test_restaurar_minimo_volta_para_company_default(conn):
    set_unit_epi_minimum_stock(conn, 1, A, EPI, 7, actor=ATOR)
    assert resolve_unit_minimum_stock(conn, 1, A, EPI).source == 'unit_configured'

    resultado = clear_unit_epi_minimum_stock(conn, 1, A, EPI, actor=ATOR)

    assert resultado.source == 'company_default'
    assert resultado.value == 100, 'deveria voltar ao mínimo do catálogo da empresa'


def test_restaurar_percentual_volta_para_company_default(conn):
    set_unit_epi_attention_percentage(conn, 1, A, EPI, 55, actor=ATOR)
    assert resolve_unit_attention_percentage(conn, 1, A, EPI).value == 55

    resultado = clear_unit_epi_attention_percentage(conn, 1, A, EPI, actor=ATOR)

    assert resultado.source == 'company_default'
    assert resultado.value == 20, 'o padrão da empresa é 20%'


def test_restaurar_alerta_volta_para_system_default_habilitado(conn):
    set_unit_epi_alert_enabled(conn, 1, A, EPI, False, actor=ATOR)
    assert resolve_unit_epi_alert_enabled(conn, 1, A, EPI).enabled is False

    resultado = clear_unit_epi_alert_enabled(conn, 1, A, EPI, actor=ATOR)

    assert resultado.source == 'system_default'
    assert resultado.enabled is True


# ── restaurar ≠ reativar ─────────────────────────────────────────────────────

def test_reativar_alerta_mantem_unit_configured(conn):
    """A Unidade decidiu manter ligado — isso é diferente de nunca ter tocado."""
    set_unit_epi_alert_enabled(conn, 1, A, EPI, False, actor=ATOR)
    reativado = set_unit_epi_alert_enabled(conn, 1, A, EPI, True, actor=ATOR)

    assert reativado.enabled is True
    assert reativado.source == 'unit_configured'
    linhas = conn.execute(
        'SELECT COUNT(*) AS n FROM unit_epi_stock_alert_settings WHERE unit_id = ?', (A,)
    ).fetchone()['n']
    assert linhas == 1, 'reativar não pode apagar a linha'


def test_reativar_e_restaurar_terminam_ligados_com_origens_opostas(conn):
    set_unit_epi_alert_enabled(conn, 1, A, EPI, False, actor=ATOR)
    reativado = set_unit_epi_alert_enabled(conn, 1, A, EPI, True, actor=ATOR)

    set_unit_epi_alert_enabled(conn, 1, B, EPI, False, actor=ATOR)
    restaurado = clear_unit_epi_alert_enabled(conn, 1, B, EPI, actor=ATOR)

    assert reativado.enabled == restaurado.enabled is True
    assert reativado.source != restaurado.source
    assert (reativado.source, restaurado.source) == ('unit_configured', 'system_default')


# ── isolamento entre Unidades ────────────────────────────────────────────────

def test_configurar_A_nao_muda_B_nem_C(conn):
    set_unit_epi_minimum_stock(conn, 1, A, EPI, 7, actor=ATOR)
    set_unit_epi_attention_percentage(conn, 1, A, EPI, 55, actor=ATOR)
    set_unit_epi_alert_enabled(conn, 1, A, EPI, False, actor=ATOR)

    for unidade in (B, C):
        assert resolve_unit_minimum_stock(conn, 1, unidade, EPI).source == 'company_default'
        assert resolve_unit_attention_percentage(conn, 1, unidade, EPI).value == 20
        assert resolve_unit_epi_alert_enabled(conn, 1, unidade, EPI).enabled is True


def test_restaurar_em_A_nao_apaga_a_configuracao_de_B(conn):
    for unidade in (A, B):
        set_unit_epi_minimum_stock(conn, 1, unidade, EPI, 7, actor=ATOR)
        set_unit_epi_attention_percentage(conn, 1, unidade, EPI, 55, actor=ATOR)
        set_unit_epi_alert_enabled(conn, 1, unidade, EPI, False, actor=ATOR)

    clear_unit_epi_minimum_stock(conn, 1, A, EPI, actor=ATOR)
    clear_unit_epi_attention_percentage(conn, 1, A, EPI, actor=ATOR)
    clear_unit_epi_alert_enabled(conn, 1, A, EPI, actor=ATOR)

    assert resolve_unit_minimum_stock(conn, 1, B, EPI).value == 7
    assert resolve_unit_attention_percentage(conn, 1, B, EPI).value == 55
    assert resolve_unit_epi_alert_enabled(conn, 1, B, EPI).enabled is False


# ── idempotência ─────────────────────────────────────────────────────────────

def test_restaurar_o_que_ja_e_herdado_e_no_op_sem_auditoria(conn):
    antes = conn.execute('SELECT COUNT(*) AS n FROM unit_epi_stock_config_audit_logs').fetchone()['n']

    resultado = clear_unit_epi_attention_percentage(conn, 1, A, EPI, actor=ATOR)

    assert (resultado.value, resultado.source) == (20, 'company_default')
    depois = conn.execute('SELECT COUNT(*) AS n FROM unit_epi_stock_config_audit_logs').fetchone()['n']
    assert depois == antes, 'no-op não pode poluir o histórico'


def test_restaurar_duas_vezes_nao_quebra(conn):
    set_unit_epi_minimum_stock(conn, 1, A, EPI, 7, actor=ATOR)
    primeiro = clear_unit_epi_minimum_stock(conn, 1, A, EPI, actor=ATOR)
    segundo = clear_unit_epi_minimum_stock(conn, 1, A, EPI, actor=ATOR)
    assert primeiro == segundo


# ── auditoria ────────────────────────────────────────────────────────────────

def test_a_restauracao_do_minimo_fica_auditada_com_a_origem_anterior(conn):
    set_unit_epi_minimum_stock(conn, 1, A, EPI, 7, actor=ATOR)
    clear_unit_epi_minimum_stock(conn, 1, A, EPI, actor=ATOR)

    linha = conn.execute(
        "SELECT * FROM unit_epi_minimum_stock_audit_logs WHERE action = 'restore_default'"
    ).fetchone()
    assert linha['previous_minimum_stock'] == 7
    assert linha['new_minimum_stock'] == 100
    assert linha['previous_source'] == 'unit_configured'


def test_a_restauracao_do_alerta_fica_auditada(conn):
    set_unit_epi_alert_enabled(conn, 1, A, EPI, False, actor=ATOR)
    clear_unit_epi_alert_enabled(conn, 1, A, EPI, actor=ATOR)

    linhas = conn.execute(
        "SELECT * FROM unit_epi_stock_config_audit_logs WHERE parameter = 'alert_enabled' "
        'ORDER BY id DESC'
    ).fetchall()
    assert linhas[0]['previous_value'] == 'false'
    assert linhas[0]['new_value'] == 'true'
    assert linhas[0]['previous_source'] == 'unit_configured'


# ── autorização: quem configura qual Unidade ─────────────────────────────────

def test_administrador_geral_configura_a_unidade_que_informar(conn, monkeypatch):
    geral = {'id': 2, 'role': 'general_admin', 'company_id': 1, 'full_name': 'Geral'}
    resposta = _rota(conn, monkeypatch, routes.handle_post_stock_minimum, geral,
                     {'epi_id': EPI, 'minimum_stock': 42, 'unit_id': B})

    assert resposta['unit_id'] == B
    assert resolve_unit_minimum_stock(conn, 1, B, EPI).value == 42
    assert resolve_unit_minimum_stock(conn, 1, A, EPI).source == 'company_default', \
        'configurar B não pode tocar A'


def test_administrador_de_registro_tambem_configura(conn, monkeypatch):
    registro = {'id': 3, 'role': 'registry_admin', 'company_id': 1, 'full_name': 'Registro'}
    resposta = _rota(conn, monkeypatch, routes.handle_post_stock_attention_percentage, registro,
                     {'epi_id': EPI, 'attention_percentage': 35, 'unit_id': C})
    assert resposta['unit_id'] == C
    assert resolve_unit_attention_percentage(conn, 1, C, EPI).value == 35


def test_perfil_livre_sem_unidade_e_recusado(conn, monkeypatch):
    """Configuração é sempre DE uma Unidade; não existe configurar a empresa aqui."""
    geral = {'id': 2, 'role': 'general_admin', 'company_id': 1}
    with pytest.raises(ValueError, match='Informe a Unidade'):
        _rota(conn, monkeypatch, routes.handle_post_stock_minimum, geral,
              {'epi_id': EPI, 'minimum_stock': 42})


def test_unidade_de_outro_tenant_e_recusada(conn, monkeypatch):
    geral = {'id': 2, 'role': 'general_admin', 'company_id': 1}
    with pytest.raises(ValueError):
        _rota(conn, monkeypatch, routes.handle_post_stock_minimum, geral,
              {'epi_id': EPI, 'minimum_stock': 42, 'unit_id': ALHEIA})
    assert resolve_unit_minimum_stock(conn, 2, ALHEIA, EPI).source == 'company_default'


def test_perfil_travado_ignora_o_unit_id_do_cliente(conn, monkeypatch):
    """Gestor da Unidade A não altera B, nem mandando `unit_id=B`."""
    gestor = {'id': 4, 'role': 'user', 'company_id': 1, 'linked_employee_id': 77}
    resposta = _rota(conn, monkeypatch, routes.handle_post_stock_minimum, gestor,
                     {'epi_id': EPI, 'minimum_stock': 9, 'unit_id': B})

    assert resposta['unit_id'] == A
    assert resolve_unit_minimum_stock(conn, 1, A, EPI).value == 9
    assert resolve_unit_minimum_stock(conn, 1, B, EPI).source == 'company_default'


def test_perfil_travado_nao_restaura_outra_unidade(conn, monkeypatch):
    set_unit_epi_minimum_stock(conn, 1, A, EPI, 7, actor=ATOR)
    set_unit_epi_minimum_stock(conn, 1, B, EPI, 8, actor=ATOR)
    gestor = {'id': 4, 'role': 'user', 'company_id': 1, 'linked_employee_id': 77}

    _rota(conn, monkeypatch, routes.handle_post_stock_minimum_restore, gestor,
          {'epi_id': EPI, 'unit_id': B})

    assert resolve_unit_minimum_stock(conn, 1, A, EPI).source == 'company_default', \
        'a restauração foi aplicada na Unidade do ator, como esperado'
    assert resolve_unit_minimum_stock(conn, 1, B, EPI).value == 8, \
        'a Unidade B não podia ser tocada'


@pytest.mark.parametrize('papel', ['buyer', 'approver', 'master_admin'])
def test_papeis_sem_direito_continuam_bloqueados(conn, monkeypatch, papel):
    ator = {'id': 9, 'role': papel, 'company_id': 1}
    with pytest.raises(PermissionError):
        _rota(conn, monkeypatch, routes.handle_post_stock_minimum, ator,
              {'epi_id': EPI, 'minimum_stock': 1, 'unit_id': A})


# ── as três rotas de restauração existem ─────────────────────────────────────

def test_as_tres_rotas_de_restauracao_estao_registradas():
    registradas = []

    class _Router:
        def register(self, metodo, caminho, _handler, **_k):
            registradas.append((metodo, caminho))

    routes.register_routes(_Router())
    for caminho in ('/api/stock/minimum/restore-default',
                    '/api/stock/attention-percentage/restore-default',
                    '/api/stock/alert-enabled/restore-default'):
        assert ('POST', caminho) in registradas, caminho
