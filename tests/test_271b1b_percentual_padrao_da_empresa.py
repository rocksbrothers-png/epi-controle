"""#271-B1b — percentual padrão da EMPRESA, fechando a hierarquia de três níveis.

`company_stock_attention_config` existia desde a #271 e era **somente-leitura
no código inteiro**: um `SELECT` e nenhum escritor. O comentário na função
dizia "para que o Administrador Geral possa mudá-lo sem deploy" — a tabela
existia para isso e nunca ganhou o caminho. Na prática os 20% eram
hardcoded.

A hierarquia agora fecha::

    system_default (20%) → company_configured → unit_configured

E em CADA nível, "configurar com o mesmo valor" e "restaurar herança" são
estados diferentes. Salvar 20% deixa `company_configured = 20`; restaurar
deixa a empresa sem configuração, em `system_default = 20`. Mesmo número,
origens opostas.

A propagação para quem herda é LEITURA, nunca escrita: nenhuma linha de
`unit_epi_attention_percentage` é tocada ao mudar o padrão. Um `UPDATE` em
massa aqui sobrescreveria as personalizações locais — o defeito que a
1.1D-B0 corrigiu quando o mínimo era `UPDATE epis`.
"""

import io
import json
import sqlite3

import pytest

from modules.stock import routes
from modules.stock.service import (
    DEFAULT_ATTENTION_PERCENTAGE,
    MAX_ATTENTION_PERCENTAGE,
    classify_unit_epi_stock,
    clear_company_attention_percentage,
    resolve_company_attention_setting,
    resolve_unit_attention_percentage,
    set_company_attention_percentage,
    set_unit_epi_attention_percentage,
    validate_attention_percentage,
)

ATOR = {'id': 1, 'full_name': 'Admin', 'role': 'general_admin'}
EMPRESA, OUTRA = 1, 2
A, B, C, EPI = 10, 11, 12, 5


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class _PgStyleConn:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(str(sql).replace('%s', '?'), params)

    def close(self):
        """No-op: as rotas fechariam a conexão do teste antes das asserções."""

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
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER, name TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
            active_joinventure TEXT, scope_type TEXT DEFAULT 'GLOBAL',
            minimum_stock INTEGER NOT NULL DEFAULT 10);
        CREATE TABLE unit_epi_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0, updated_at TEXT);
        CREATE TABLE unit_epi_minimum_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            minimum_stock INTEGER NOT NULL DEFAULT 0,
            created_by_user_id INTEGER, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE (company_id, unit_id, epi_id));
        CREATE TABLE company_stock_attention_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL UNIQUE,
            attention_percentage INTEGER NOT NULL DEFAULT 20, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '');
        CREATE TABLE company_stock_attention_config_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            action TEXT NOT NULL DEFAULT 'set',
            previous_percentage INTEGER, new_percentage INTEGER NOT NULL,
            previous_source TEXT NOT NULL DEFAULT '', new_source TEXT NOT NULL DEFAULT '',
            actor_user_id INTEGER, actor_name TEXT NOT NULL DEFAULT '',
            actor_role TEXT NOT NULL DEFAULT '', ip_address TEXT NOT NULL DEFAULT '',
            user_agent TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
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
        INSERT INTO companies (id, name) VALUES (1, 'Norskan'), (2, 'Outra');
        INSERT INTO units (id, company_id, name) VALUES (10, 1, 'A'), (11, 1, 'B'), (12, 1, 'C');
        INSERT INTO epis (id, company_id, unit_id, name, minimum_stock)
            VALUES (5, 1, NULL, 'Capacete', 100);
        INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity)
            VALUES (1, 10, 5, 100), (1, 11, 5, 100), (1, 12, 5, 100);
        """
    )
    raw.commit()
    return _PgStyleConn(raw)


@pytest.fixture(autouse=True)
def _sqlite(monkeypatch):
    import epi_backend.db as db_module
    monkeypatch.setattr(db_module, '_is_sqlite_connection', lambda _c: True)


def _rota(conn, monkeypatch, handler_fn, actor, payload=None, query=''):
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(routes, 'get_connection', lambda: conn)

    class _H:
        path = '/api/stock/company-attention-percentage'
        def send_response(self, *_a, **_k): pass
        def send_header(self, *_a, **_k): pass
        def end_headers(self): pass

    class _P:
        def __init__(self, q): self.query = q

    h = _H()
    h.wfile = io.BytesIO()
    corpo = None if payload is None else {'actor_user_id': actor['id'], **payload}
    handler_fn(h, _P(query), corpo, None)
    return json.loads(h.wfile.getvalue().decode('utf-8'))


# ── validação, nos DOIS níveis ───────────────────────────────────────────────

def test_zero_e_valido_e_nao_e_ausencia():
    """0% = sem faixa laranja; só crítico no mínimo ou abaixo."""
    assert validate_attention_percentage(0) == 0
    assert validate_attention_percentage('0') == 0


@pytest.mark.parametrize('valor', [-1, 101, 500])
def test_fora_da_faixa_e_recusado(valor):
    with pytest.raises(ValueError):
        validate_attention_percentage(valor)


@pytest.mark.parametrize('valor', [None, '', 'abc'])
def test_valor_invalido_e_recusado(valor):
    with pytest.raises(ValueError):
        validate_attention_percentage(valor)


def test_o_teto_e_o_mesmo_nos_dois_niveis(conn):
    """Uma rota aceitando 500 e a outra recusando 101 seriam duas réguas."""
    with pytest.raises(ValueError):
        set_company_attention_percentage(conn, EMPRESA, 101, actor=ATOR)
    with pytest.raises(ValueError):
        set_unit_epi_attention_percentage(conn, EMPRESA, A, EPI, 101, actor=ATOR)
    assert MAX_ATTENTION_PERCENTAGE == 100


def test_zero_e_aceito_nos_dois_niveis(conn):
    assert set_company_attention_percentage(conn, EMPRESA, 0, actor=ATOR).value == 0
    assert set_unit_epi_attention_percentage(conn, EMPRESA, A, EPI, 0, actor=ATOR).value == 0


# ── a hierarquia de três níveis ──────────────────────────────────────────────

def test_sem_configuracao_corporativa_a_empresa_usa_o_padrao_do_sistema(conn):
    atual = resolve_company_attention_setting(conn, EMPRESA)
    assert (atual.value, atual.source) == (DEFAULT_ATTENTION_PERCENTAGE, 'system_default')


def test_com_configuracao_a_origem_e_company_configured(conn):
    set_company_attention_percentage(conn, EMPRESA, 35, actor=ATOR)
    atual = resolve_company_attention_setting(conn, EMPRESA)
    assert (atual.value, atual.source) == (35, 'company_configured')


def test_salvar_20_e_restaurar_para_20_sao_estados_diferentes(conn):
    """Mesmo número, origens opostas — a distinção que fecha a hierarquia."""
    salvo = set_company_attention_percentage(conn, EMPRESA, 20, actor=ATOR)
    assert (salvo.value, salvo.source) == (20, 'company_configured')
    linhas = conn.execute(
        'SELECT COUNT(*) AS n FROM company_stock_attention_config WHERE company_id = ?',
        (EMPRESA,)).fetchone()['n']
    assert linhas == 1

    restaurado = clear_company_attention_percentage(conn, EMPRESA, actor=ATOR)
    assert (restaurado.value, restaurado.source) == (20, 'system_default')
    linhas = conn.execute(
        'SELECT COUNT(*) AS n FROM company_stock_attention_config WHERE company_id = ?',
        (EMPRESA,)).fetchone()['n']
    assert linhas == 0, 'restaurar precisa APAGAR a linha, não gravar 20'


def test_restaurar_o_que_ja_e_system_default_e_no_op(conn):
    antes = conn.execute(
        'SELECT COUNT(*) AS n FROM company_stock_attention_config_audit_logs').fetchone()['n']
    resultado = clear_company_attention_percentage(conn, EMPRESA, actor=ATOR)
    assert resultado.source == 'system_default'
    depois = conn.execute(
        'SELECT COUNT(*) AS n FROM company_stock_attention_config_audit_logs').fetchone()['n']
    assert depois == antes


# ── isolamento: a mudança corporativa não escreve em Unidade nenhuma ─────────

def _fotografia_local(conn):
    return conn.execute(
        'SELECT company_id, unit_id, epi_id, attention_percentage '
        'FROM unit_epi_attention_percentage ORDER BY unit_id'
    ).fetchall()


def test_mudar_o_padrao_nao_altera_nenhuma_linha_local(conn):
    set_unit_epi_attention_percentage(conn, EMPRESA, A, EPI, 55, actor=ATOR)
    antes = _fotografia_local(conn)

    set_company_attention_percentage(conn, EMPRESA, 35, actor=ATOR)

    assert _fotografia_local(conn) == antes


def test_quem_herda_acompanha_e_quem_personalizou_fica_intacto(conn):
    set_unit_epi_attention_percentage(conn, EMPRESA, A, EPI, 55, actor=ATOR)

    set_company_attention_percentage(conn, EMPRESA, 35, actor=ATOR)

    personalizada = resolve_unit_attention_percentage(conn, EMPRESA, A, EPI)
    assert (personalizada.value, personalizada.source) == (55, 'unit_configured')
    for unidade in (B, C):
        herdeira = resolve_unit_attention_percentage(conn, EMPRESA, unidade, EPI)
        assert (herdeira.value, herdeira.source) == (35, 'company_default')


def test_a_mudanca_vale_na_leitura_seguinte_sem_invalidacao(conn):
    """Sem cache: a classificação lê o padrão a cada chamada."""
    antes = classify_unit_epi_stock(conn, EMPRESA, B, EPI, unit_stock=100)
    set_company_attention_percentage(conn, EMPRESA, 50, actor=ATOR)
    depois = classify_unit_epi_stock(conn, EMPRESA, B, EPI, unit_stock=100)

    assert antes.attention_limit == 120, 'mínimo 100 com 20% herdados'
    assert depois.attention_limit == 150, 'mínimo 100 com os 50% novos'


def test_restaurar_o_padrao_nao_altera_configuracoes_locais(conn):
    set_unit_epi_attention_percentage(conn, EMPRESA, A, EPI, 55, actor=ATOR)
    set_company_attention_percentage(conn, EMPRESA, 35, actor=ATOR)
    antes = _fotografia_local(conn)

    clear_company_attention_percentage(conn, EMPRESA, actor=ATOR)

    assert _fotografia_local(conn) == antes
    assert resolve_unit_attention_percentage(conn, EMPRESA, A, EPI).value == 55
    assert resolve_unit_attention_percentage(conn, EMPRESA, B, EPI).value == 20


def test_o_padrao_de_uma_empresa_nao_vaza_para_a_outra(conn):
    set_company_attention_percentage(conn, EMPRESA, 35, actor=ATOR)
    assert resolve_company_attention_setting(conn, OUTRA).source == 'system_default'


def test_nao_existe_update_em_massa_no_modulo():
    """Verificação estrutural: a propagação é leitura, nunca escrita."""
    from pathlib import Path
    fonte = (Path(__file__).resolve().parents[1] / 'modules' / 'stock' / 'service.py'
             ).read_text(encoding='utf-8')
    corpo = '\n'.join(l for l in fonte.splitlines() if not l.lstrip().startswith('#'))
    # O único UPDATE nessa tabela é o do setter por Unidade, via `_upsert_config`,
    # que é parametrizado pela tabela — nenhum literal deve existir.
    assert 'UPDATE unit_epi_attention_percentage' not in corpo


# ── auditoria ────────────────────────────────────────────────────────────────

def test_gravar_registra_origem_anterior_e_nova(conn):
    set_company_attention_percentage(conn, EMPRESA, 35, actor=ATOR)
    linha = conn.execute(
        'SELECT * FROM company_stock_attention_config_audit_logs ORDER BY id DESC').fetchone()
    assert linha['action'] == 'set'
    assert linha['previous_percentage'] is None, 'não havia configuração corporativa'
    assert linha['new_percentage'] == 35
    assert linha['previous_source'] == 'system_default'
    assert linha['new_source'] == 'company_configured'


def test_restaurar_registra_a_transicao_de_volta(conn):
    set_company_attention_percentage(conn, EMPRESA, 35, actor=ATOR)
    clear_company_attention_percentage(conn, EMPRESA, actor=ATOR)
    linha = conn.execute(
        'SELECT * FROM company_stock_attention_config_audit_logs ORDER BY id DESC').fetchone()
    assert linha['action'] == 'restore'
    assert (linha['previous_percentage'], linha['new_percentage']) == (35, 20)
    assert (linha['previous_source'], linha['new_source']) == ('company_configured', 'system_default')


def test_a_auditoria_corporativa_nao_usa_sentinelas_de_unidade(conn):
    set_company_attention_percentage(conn, EMPRESA, 35, actor=ATOR)
    colunas = [d[0] for d in conn.execute(
        'SELECT * FROM company_stock_attention_config_audit_logs').description]
    assert 'unit_id' not in colunas and 'epi_id' not in colunas


# ── autorização e resolução da empresa ───────────────────────────────────────

def test_master_admin_precisa_informar_a_empresa(conn, monkeypatch):
    master = {'id': 9, 'role': 'master_admin', 'company_id': None}
    with pytest.raises(ValueError, match='Informe a empresa'):
        _rota(conn, monkeypatch, routes.handle_post_company_attention_percentage,
              master, {'attention_percentage': 35})


def test_master_admin_com_empresa_valida_altera(conn, monkeypatch):
    master = {'id': 9, 'role': 'master_admin', 'company_id': None}
    resposta = _rota(conn, monkeypatch, routes.handle_post_company_attention_percentage,
                     master, {'attention_percentage': 35, 'company_id': OUTRA})
    assert resposta['company_id'] == OUTRA
    assert resolve_company_attention_setting(conn, OUTRA).value == 35
    assert resolve_company_attention_setting(conn, EMPRESA).source == 'system_default'


def test_master_admin_com_empresa_inexistente_e_recusado(conn, monkeypatch):
    master = {'id': 9, 'role': 'master_admin', 'company_id': None}
    with pytest.raises(ValueError, match='não encontrada'):
        _rota(conn, monkeypatch, routes.handle_post_company_attention_percentage,
              master, {'attention_percentage': 35, 'company_id': 999})


def test_general_admin_nao_altera_outra_empresa(conn, monkeypatch):
    """`company_id` do payload é IGNORADO, não honrado."""
    geral = {'id': 2, 'role': 'general_admin', 'company_id': EMPRESA}
    resposta = _rota(conn, monkeypatch, routes.handle_post_company_attention_percentage,
                     geral, {'attention_percentage': 35, 'company_id': OUTRA})

    assert resposta['company_id'] == EMPRESA
    assert resolve_company_attention_setting(conn, EMPRESA).value == 35
    assert resolve_company_attention_setting(conn, OUTRA).source == 'system_default'


def test_registry_admin_tambem_altera_a_propria_empresa(conn, monkeypatch):
    registro = {'id': 3, 'role': 'registry_admin', 'company_id': EMPRESA}
    resposta = _rota(conn, monkeypatch, routes.handle_post_company_attention_percentage,
                     registro, {'attention_percentage': 42})
    assert resposta['attention_percentage'] == 42


def test_a_rota_corporativa_exige_settings_update(conn, monkeypatch):
    """`admin`/`user` configuram a própria Unidade, nunca o padrão de todas.

    A guarda é a permissão `settings:update`, que nenhum dos dois possui — por
    isso o teste confere a PERMISSÃO exigida, e não uma lista de papéis
    duplicada aqui.
    """
    from core.permissions import PERMISSIONS
    from core.permissions import PERM_SETTINGS_UPDATE
    for papel in ('admin', 'user', 'buyer', 'approver'):
        assert PERM_SETTINGS_UPDATE not in PERMISSIONS.get(papel, set()), papel
    for papel in ('general_admin', 'registry_admin', 'master_admin'):
        assert PERM_SETTINGS_UPDATE in PERMISSIONS.get(papel, set()), papel


# ── contrato de leitura ──────────────────────────────────────────────────────

def test_o_get_distingue_system_default_de_company_configured(conn, monkeypatch):
    geral = {'id': 2, 'role': 'general_admin', 'company_id': EMPRESA}

    antes = _rota(conn, monkeypatch, routes.handle_get_company_attention_percentage, geral)
    assert antes['source'] == 'system_default'
    assert antes['has_company_config'] is False
    assert antes['attention_percentage'] == 20
    assert antes['system_default_percentage'] == 20
    assert antes['max_percentage'] == 100

    set_company_attention_percentage(conn, EMPRESA, 35, actor=ATOR)

    depois = _rota(conn, monkeypatch, routes.handle_get_company_attention_percentage, geral)
    assert depois['source'] == 'company_configured'
    assert depois['has_company_config'] is True
    assert depois['attention_percentage'] == 35


def test_o_get_de_20_configurado_nao_se_confunde_com_o_padrao(conn, monkeypatch):
    geral = {'id': 2, 'role': 'general_admin', 'company_id': EMPRESA}
    set_company_attention_percentage(conn, EMPRESA, 20, actor=ATOR)

    resposta = _rota(conn, monkeypatch, routes.handle_get_company_attention_percentage, geral)

    assert resposta['attention_percentage'] == 20
    assert resposta['source'] == 'company_configured'
    assert resposta['has_company_config'] is True


def test_as_tres_rotas_corporativas_estao_registradas():
    registradas = []

    class _Router:
        def register(self, metodo, caminho, _handler, **_k):
            registradas.append((metodo, caminho))

    routes.register_routes(_Router())
    assert ('GET', '/api/stock/company-attention-percentage') in registradas
    assert ('POST', '/api/stock/company-attention-percentage') in registradas
    assert ('POST', '/api/stock/company-attention-percentage/restore-default') in registradas
