"""Classificação de estoque por Unidade + EPI — fonte única (#271).

A fatia 1.1D-B0 criou o mínimo por Unidade. Faltavam dois parâmetros:

1. uma **faixa de atenção** (laranja) acima do mínimo, para avisar antes de o
   estoque ficar crítico;
2. um **liga/desliga do monitoramento** por Unidade + EPI, porque uma Unidade
   pode ter saldo residual de um EPI que não usa mais — e alerta vermelho
   permanente sobre isso treina o operador a ignorar alertas.

Quatro conceitos independentes, e é a separação deles que dá a resposta certa::

    mínimo efetivo    20 unidades
    faixa de atenção  20%
    condição real     critical          <- underlying_status
    monitoramento     desabilitado      <- stock_alert_enabled

    "O estoque está crítico, mas o alerta foi desabilitado pela Unidade."

`disabled` NUNCA vira `normal`: transformar estoque crítico em saudável
esconderia justamente o que o operador precisa poder consultar.
"""

import pathlib
import re
import sqlite3

from modules.stock.service import (
    ALERT_SOURCE_SYSTEM,
    ALERT_SOURCE_UNIT,
    ATTENTION_SOURCE_COMPANY,
    ATTENTION_SOURCE_UNIT,
    MINIMUM_SOURCE_COMPANY,
    MINIMUM_SOURCE_UNIT,
    STATUS_CRITICAL,
    STATUS_DISABLED,
    STATUS_NEAR_MINIMUM,
    STATUS_NORMAL,
    classify_unit_epi_stock,
    compute_attention_limit,
    resolve_unit_attention_percentage,
    resolve_unit_epi_alert_enabled,
    set_unit_epi_alert_enabled,
    set_unit_epi_attention_percentage,
    set_unit_epi_minimum_stock,
)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
STOCK_SERVICE = RAIZ / 'modules/stock/service.py'
PURCHASES = RAIZ / 'modules/purchases/service.py'
ALERTS = RAIZ / 'modules/alerts/service.py'
SQL = RAIZ / 'supabase/migrations/20260821000000_stock_classification_config.sql'
MIGRACAO = RAIZ / 'epi_backend/migrations/026_stock_classification_config.py'

GESTOR = {'id': 5, 'role': 'user', 'company_id': 1, 'full_name': 'Gestor da Unidade A'}


def _conexao(minimo_corporativo=20):
    """Empresa 1, Unidades 10/11/12, EPI 7 com mínimo corporativo 20.

    Com 20% herdados o limite da faixa é 24, então:
    saldo <= 20 crítico · 21..24 atenção · > 24 normal.
    """
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        '''
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
        CREATE TABLE unit_epi_minimum_stock_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            action TEXT NOT NULL DEFAULT 'set',
            previous_minimum_stock INTEGER, new_minimum_stock INTEGER NOT NULL,
            previous_source TEXT NOT NULL DEFAULT '', actor_user_id INTEGER,
            actor_name TEXT NOT NULL DEFAULT '', actor_role TEXT NOT NULL DEFAULT '',
            ip_address TEXT NOT NULL DEFAULT '', user_agent TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
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
        '''
    )
    conn.execute('INSERT INTO epis (id, company_id, minimum_stock) VALUES (7, 1, ?)',
                 (minimo_corporativo,))
    conn.commit()
    return conn


def _saldo(conn, unidade, quantidade, epi=7):
    conn.execute(
        'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity) VALUES (1, ?, ?, ?)',
        (unidade, epi, quantidade),
    )
    conn.commit()


# ═══════════════════════════════════════════════════════════════════════════
# Arredondamento — os cinco casos travados no contrato
# ═══════════════════════════════════════════════════════════════════════════

def test_limite_de_atencao_arredonda_para_cima():
    assert compute_attention_limit(100, 20) == 120
    assert compute_attention_limit(33, 20) == 40
    assert compute_attention_limit(1, 20) == 2


def test_minimo_zero_nao_cria_faixa():
    """Quem configurou mínimo 0 disse "só me avise ao zerar". Uma faixa de
    atenção acima de zero contradiria a decisão."""
    assert compute_attention_limit(0, 20) == 0


def test_percentual_zero_deixa_a_faixa_vazia():
    """Limite igual ao mínimo: nada satisfaz `mínimo < saldo <= limite`."""
    assert compute_attention_limit(10, 0) == 10


def test_ceil_evita_que_a_faixa_desapareca():
    """Com `floor`, mínimo 1 + 20% daria 1 — o próprio mínimo — e o EPI
    saltaria de vermelho direto para verde, sem laranja."""
    limite = compute_attention_limit(1, 20)
    assert limite > 1, 'a faixa de atenção sumiu para mínimos pequenos'


def test_aritmetica_usa_decimal_e_nao_float():
    """Mínimo 50 + 10%: o limite correto é 55, mas `float` devolve 56.

    `50 * (1 + 10/100)` em ponto flutuante binário dá 55.00000000000001, e
    `ceil` disso é 56 — um teto errado, que estenderia a faixa laranja por uma
    unidade a mais. Varrendo mínimos de 1 a 400 contra percentuais de 1 a 100,
    **74 combinações divergem** entre `float` e `Decimal`. O defeito só
    apareceria em algumas delas, que é a pior espécie.

    Este teste falha se alguém trocar `Decimal` por `float`.
    """
    import math
    assert compute_attention_limit(50, 10) == 55
    assert math.ceil(50 * (1 + 10 / 100)) == 56, \
        'o cenário perdeu a propriedade que torna o teste interessante'
    # E o mesmo vale para outras combinações plausíveis.
    assert compute_attention_limit(25, 12) == 28
    assert compute_attention_limit(75, 12) == 84


# ═══════════════════════════════════════════════════════════════════════════
# Os três estados, com monitoramento ligado
# ═══════════════════════════════════════════════════════════════════════════

def test_habilitado_e_saldo_critico():
    with _conexao() as conn:
        _saldo(conn, 10, 20)
        c = classify_unit_epi_stock(conn, 1, 10, 7)
    assert c.underlying_status == STATUS_CRITICAL
    assert c.stock_status == STATUS_CRITICAL
    assert c.effective_minimum_stock == 20
    assert c.attention_limit == 24


def test_habilitado_e_saldo_proximo():
    with _conexao() as conn:
        _saldo(conn, 10, 22)
        c = classify_unit_epi_stock(conn, 1, 10, 7)
    assert c.underlying_status == STATUS_NEAR_MINIMUM
    assert c.stock_status == STATUS_NEAR_MINIMUM


def test_habilitado_e_saldo_saudavel():
    with _conexao() as conn:
        _saldo(conn, 10, 25)
        c = classify_unit_epi_stock(conn, 1, 10, 7)
    assert c.underlying_status == STATUS_NORMAL
    assert c.stock_status == STATUS_NORMAL


def test_as_fronteiras_da_faixa():
    """Mínimo 20, limite 24: 20 crítico, 21 e 24 atenção, 25 normal."""
    esperado = {20: STATUS_CRITICAL, 21: STATUS_NEAR_MINIMUM,
                24: STATUS_NEAR_MINIMUM, 25: STATUS_NORMAL}
    for saldo, status in esperado.items():
        with _conexao() as conn:
            _saldo(conn, 10, saldo)
            assert classify_unit_epi_stock(conn, 1, 10, 7).stock_status == status, \
                f'saldo {saldo} classificado fora da faixa esperada'


# ═══════════════════════════════════════════════════════════════════════════
# Desabilitado — o coração da fatia
# ═══════════════════════════════════════════════════════════════════════════

def test_desabilitado_com_saldo_abaixo_do_minimo_e_disabled_nunca_critical():
    """O caso do contrato: saldo 8, mínimo 20, monitoramento desligado."""
    with _conexao() as conn:
        _saldo(conn, 10, 8)
        set_unit_epi_alert_enabled(conn, 1, 10, 7, False, actor=GESTOR)
        c = classify_unit_epi_stock(conn, 1, 10, 7)
    assert c.stock_status == STATUS_DISABLED
    assert c.underlying_status == STATUS_CRITICAL, \
        'a condição física precisa continuar dizendo a verdade'
    assert c.stock_status != STATUS_NORMAL, \
        'estoque crítico virou "normal" ao desligar o alerta'


def test_desabilitado_com_saldo_proximo():
    with _conexao() as conn:
        _saldo(conn, 10, 22)
        set_unit_epi_alert_enabled(conn, 1, 10, 7, False, actor=GESTOR)
        c = classify_unit_epi_stock(conn, 1, 10, 7)
    assert (c.underlying_status, c.stock_status) == (STATUS_NEAR_MINIMUM, STATUS_DISABLED)


def test_desabilitado_com_saldo_normal():
    with _conexao() as conn:
        _saldo(conn, 10, 30)
        set_unit_epi_alert_enabled(conn, 1, 10, 7, False, actor=GESTOR)
        c = classify_unit_epi_stock(conn, 1, 10, 7)
    assert (c.underlying_status, c.stock_status) == (STATUS_NORMAL, STATUS_DISABLED)


def test_desabilitar_preserva_todos_os_numeros_reais():
    """Item 9 do contrato: desligar o alerta não altera nada além da decisão
    de alertar. O Controle de Estoque precisa poder mostrar os valores."""
    with _conexao() as conn:
        _saldo(conn, 10, 8)
        antes = classify_unit_epi_stock(conn, 1, 10, 7)
        set_unit_epi_alert_enabled(conn, 1, 10, 7, False, actor=GESTOR)
        depois = classify_unit_epi_stock(conn, 1, 10, 7)

    assert depois.unit_stock_quantity == antes.unit_stock_quantity == 8
    assert depois.effective_minimum_stock == antes.effective_minimum_stock == 20
    assert depois.minimum_stock_source == antes.minimum_stock_source
    assert depois.effective_attention_percentage == antes.effective_attention_percentage == 20
    assert depois.attention_percentage_source == antes.attention_percentage_source
    assert depois.attention_limit == antes.attention_limit == 24
    assert depois.underlying_status == antes.underlying_status


def test_reativar_recalcula_o_status_imediatamente():
    with _conexao() as conn:
        _saldo(conn, 10, 8)
        set_unit_epi_alert_enabled(conn, 1, 10, 7, False, actor=GESTOR)
        assert classify_unit_epi_stock(conn, 1, 10, 7).stock_status == STATUS_DISABLED
        set_unit_epi_alert_enabled(conn, 1, 10, 7, True, actor=GESTOR)
        c = classify_unit_epi_stock(conn, 1, 10, 7)
    assert c.stock_status == c.underlying_status == STATUS_CRITICAL


def test_reativar_mantem_a_origem_unit_configured():
    """Reativar GRAVA 1; não apaga a linha.

    Apagar devolveria o par ao estado "nunca configurado", perdendo o registro
    de que a Unidade decidiu deliberadamente manter o alerta ligado.
    """
    with _conexao() as conn:
        set_unit_epi_alert_enabled(conn, 1, 10, 7, False, actor=GESTOR)
        set_unit_epi_alert_enabled(conn, 1, 10, 7, True, actor=GESTOR)
        alerta = resolve_unit_epi_alert_enabled(conn, 1, 10, 7)
        linhas = conn.execute(
            'SELECT COUNT(*) AS n FROM unit_epi_stock_alert_settings '
            'WHERE company_id = 1 AND unit_id = 10 AND epi_id = 7'
        ).fetchone()['n']
    assert alerta.enabled is True
    assert alerta.source == ALERT_SOURCE_UNIT, \
        'reativar apagou a linha e o par voltou a parecer "nunca configurado"'
    assert linhas == 1


def test_sem_linha_o_alerta_e_habilitado_por_system_default():
    with _conexao() as conn:
        alerta = resolve_unit_epi_alert_enabled(conn, 1, 10, 7)
        linhas = conn.execute(
            'SELECT COUNT(*) AS n FROM unit_epi_stock_alert_settings'
        ).fetchone()['n']
    assert alerta.enabled is True
    assert alerta.source == ALERT_SOURCE_SYSTEM, (
        'a origem herdada do alerta é constante do sistema, não decisão da '
        'empresa — não existe liga/desliga corporativo'
    )
    assert linhas == 0, 'nenhuma linha deve ser criada para representar o padrão'


def test_desabilitar_na_unidade_a_nao_afeta_b_nem_c():
    with _conexao() as conn:
        for unidade in (10, 11, 12):
            _saldo(conn, unidade, 8)
        set_unit_epi_alert_enabled(conn, 1, 10, 7, False, actor=GESTOR)
        status = {u: classify_unit_epi_stock(conn, 1, u, 7).stock_status for u in (10, 11, 12)}
    assert status == {10: STATUS_DISABLED, 11: STATUS_CRITICAL, 12: STATUS_CRITICAL}


# ═══════════════════════════════════════════════════════════════════════════
# Independência dos três parâmetros
# ═══════════════════════════════════════════════════════════════════════════

def test_desabilitar_nao_altera_minimo_nem_percentual():
    with _conexao() as conn:
        set_unit_epi_minimum_stock(conn, 1, 10, 7, 50, actor=GESTOR)
        set_unit_epi_attention_percentage(conn, 1, 10, 7, 30, actor=GESTOR)
        set_unit_epi_alert_enabled(conn, 1, 10, 7, False, actor=GESTOR)
        c = classify_unit_epi_stock(conn, 1, 10, 7)
    assert c.effective_minimum_stock == 50
    assert c.minimum_stock_source == MINIMUM_SOURCE_UNIT
    assert c.effective_attention_percentage == 30
    assert c.attention_percentage_source == ATTENTION_SOURCE_UNIT


def test_alterar_minimo_nao_altera_percentual():
    with _conexao() as conn:
        set_unit_epi_attention_percentage(conn, 1, 10, 7, 30, actor=GESTOR)
        set_unit_epi_minimum_stock(conn, 1, 10, 7, 50, actor=GESTOR)
        pct = resolve_unit_attention_percentage(conn, 1, 10, 7)
    assert pct == (30, ATTENTION_SOURCE_UNIT)


def test_alterar_percentual_nao_altera_minimo():
    with _conexao() as conn:
        set_unit_epi_minimum_stock(conn, 1, 10, 7, 50, actor=GESTOR)
        set_unit_epi_attention_percentage(conn, 1, 10, 7, 30, actor=GESTOR)
        c = classify_unit_epi_stock(conn, 1, 10, 7)
    assert c.effective_minimum_stock == 50


# ═══════════════════════════════════════════════════════════════════════════
# Percentual: herança e personalização
# ═══════════════════════════════════════════════════════════════════════════

def test_sem_configuracao_o_percentual_vem_da_empresa():
    with _conexao() as conn:
        assert resolve_unit_attention_percentage(conn, 1, 10, 7) == (20, ATTENTION_SOURCE_COMPANY)


def test_padrao_da_empresa_e_configuravel_em_tabela():
    with _conexao() as conn:
        conn.execute(
            'INSERT INTO company_stock_attention_config (company_id, attention_percentage) '
            'VALUES (1, 35)'
        )
        conn.commit()
        assert resolve_unit_attention_percentage(conn, 1, 10, 7) == (35, ATTENTION_SOURCE_COMPANY)


def test_percentual_zero_configurado_e_valor_e_nao_ausencia():
    with _conexao() as conn:
        set_unit_epi_attention_percentage(conn, 1, 10, 7, 0, actor=GESTOR)
        pct = resolve_unit_attention_percentage(conn, 1, 10, 7)
    assert pct == (0, ATTENTION_SOURCE_UNIT), \
        'percentual 0 caiu de volta nos 20% da empresa'


def test_cada_unidade_com_seu_percentual():
    """Luva/A → 20% (herdado), Luva/B → 30%, Luva/C → 15%."""
    with _conexao() as conn:
        set_unit_epi_attention_percentage(conn, 1, 11, 7, 30, actor=GESTOR)
        set_unit_epi_attention_percentage(conn, 1, 12, 7, 15, actor=GESTOR)
        limites = {
            u: classify_unit_epi_stock(conn, 1, u, 7).attention_limit for u in (10, 11, 12)
        }
    assert limites == {10: 24, 11: 26, 12: 23}


# ═══════════════════════════════════════════════════════════════════════════
# Auditoria
# ═══════════════════════════════════════════════════════════════════════════

def _auditoria(conn, parameter=None):
    sql = 'SELECT * FROM unit_epi_stock_config_audit_logs'
    args = ()
    if parameter:
        sql += ' WHERE parameter = ?'
        args = (parameter,)
    return [dict(r) for r in conn.execute(sql + ' ORDER BY id', args).fetchall()]


def test_desabilitar_e_auditado_com_origem_anterior():
    with _conexao() as conn:
        set_unit_epi_alert_enabled(conn, 1, 10, 7, False, actor=GESTOR,
                                   ip_address='203.0.113.7', user_agent='EpiApp/1.0')
        r = _auditoria(conn, 'alert_enabled')[0]
    assert r['previous_value'] is None, \
        'sem configuração anterior o valor tem de ser NULL, não "true"'
    assert r['previous_source'] == ALERT_SOURCE_SYSTEM
    assert r['new_value'] == 'false'
    assert (r['company_id'], r['unit_id'], r['epi_id']) == (1, 10, 7)
    assert r['actor_user_id'] == 5
    assert r['actor_name'] == 'Gestor da Unidade A'
    assert r['actor_role'] == 'user'
    assert r['ip_address'] == '203.0.113.7'
    assert r['user_agent'] == 'EpiApp/1.0'
    assert r['created_at']


def test_a_trajetoria_do_liga_desliga_fica_registrada():
    with _conexao() as conn:
        set_unit_epi_alert_enabled(conn, 1, 10, 7, False, actor=GESTOR)
        set_unit_epi_alert_enabled(conn, 1, 10, 7, True, actor=GESTOR)
        set_unit_epi_alert_enabled(conn, 1, 10, 7, False, actor=GESTOR)
        registros = _auditoria(conn, 'alert_enabled')
    assert [r['new_value'] for r in registros] == ['false', 'true', 'false']
    assert [r['previous_value'] for r in registros] == [None, 'false', 'true']
    assert [r['previous_source'] for r in registros] == [
        ALERT_SOURCE_SYSTEM, ALERT_SOURCE_UNIT, ALERT_SOURCE_UNIT,
    ]


def test_percentual_e_auditado_separadamente_do_alerta():
    with _conexao() as conn:
        set_unit_epi_attention_percentage(conn, 1, 10, 7, 30, actor=GESTOR)
        set_unit_epi_alert_enabled(conn, 1, 10, 7, False, actor=GESTOR)
        parametros = [r['parameter'] for r in _auditoria(conn)]
    assert parametros == ['attention_percentage', 'alert_enabled']


# ═══════════════════════════════════════════════════════════════════════════
# Fiação, escopo e sabotagem
# ═══════════════════════════════════════════════════════════════════════════

def _sem_comentarios(fonte: str) -> str:
    return '\n'.join(l for l in fonte.split('\n') if not l.lstrip().startswith('#'))


def test_o_gate_de_habilitacao_existe_no_classificador():
    """Sabotagem: remover o gate faz um EPI desabilitado voltar a ser
    classificado pela condição física, gerando alerta que a Unidade desligou."""
    fonte = _sem_comentarios(STOCK_SERVICE.read_text(encoding='utf-8'))
    assert 'stock_status=subjacente if alerta.enabled else STATUS_DISABLED' in fonte, \
        'o gate `stock_alert_enabled` sumiu da classificação'


def test_compras_nao_tem_mais_a_regra_de_minimo_em_sql():
    fonte = _sem_comentarios(PURCHASES.read_text(encoding='utf-8'))
    assert 'ues.quantity <= ep.minimum_stock' not in fonte, \
        'a comparação inline voltou ao SQL das demandas de compra'
    assert 'COALESCE(uems' not in fonte and 'unit_epi_minimum_stock' not in fonte, \
        'a cadeia de fallback foi reescrita dentro do SQL — segunda implementação'
    assert 'classify_unit_epi_stock(' in fonte


def test_compras_dispara_somente_em_critical():
    fonte = _sem_comentarios(PURCHASES.read_text(encoding='utf-8'))
    assert 'if classificacao.stock_status != STATUS_CRITICAL:' in fonte, \
        'a faixa laranja passou a gerar demanda automática de compra'


def test_compras_mira_o_minimo_e_nunca_o_limite_de_atencao():
    fonte = _sem_comentarios(PURCHASES.read_text(encoding='utf-8'))
    assert 'classificacao.effective_minimum_stock - int(row[' in fonte
    assert 'attention_limit' not in fonte, \
        'a reposição passou a mirar a faixa de atenção e inflaria o estoque-alvo'


def test_alertas_derivam_a_severidade_do_status_classificado():
    fonte = _sem_comentarios(ALERTS.read_text(encoding='utf-8'))
    assert "item.get('stock_status')" in fonte, \
        'os alertas voltaram a recalcular a severidade por conta própria'
    assert 'STATUS_NEAR_MINIMUM' in fonte, 'a faixa laranja sumiu dos alertas'


def test_a_migracao_nao_tem_backfill():
    sql = SQL.read_text(encoding='utf-8')
    codigo = '\n'.join(l for l in sql.split('\n') if not l.lstrip().startswith('--'))
    for tabela in ('unit_epi_attention_percentage', 'unit_epi_stock_alert_settings'):
        assert f'INSERT INTO {tabela}' not in codigo, \
            f'a migração voltou a fabricar configuração local em {tabela}'


def test_a_migracao_habilita_rls_nas_quatro_tabelas():
    sql = SQL.read_text(encoding='utf-8')
    assert sql.count('ENABLE ROW LEVEL SECURITY') == 4
    assert sql.count('block_direct_api_access') >= 4


def test_o_par_migration_python_sql_existe():
    assert MIGRACAO.exists() and SQL.exists()
    modulo = MIGRACAO.read_text(encoding='utf-8')
    assert "MIGRATION_ID = '026_stock_classification_config'" in modulo
    assert SQL.name in modulo


def test_nenhum_consumidor_reimplementa_a_classificacao():
    """A regra dos três estados existe em UM lugar só.

    Procura a comparação com o limite de atenção fora do classificador: se
    aparecer noutro módulo, virou segunda implementação.
    """
    fonte = _sem_comentarios(STOCK_SERVICE.read_text(encoding='utf-8'))
    assert fonte.count('saldo <= limite') == 1, \
        'a comparação da faixa de atenção foi duplicada'
    for caminho in ('modules/dashboard/service.py', 'modules/purchases/service.py',
                    'modules/alerts/service.py'):
        outro = _sem_comentarios((RAIZ / caminho).read_text(encoding='utf-8'))
        assert 'attention_limit' not in outro or caminho == 'modules/dashboard/service.py', \
            f'{caminho} passou a montar a faixa de atenção por conta própria'
        assert not re.search(r'\*\s*\(1\s*\+', outro), \
            f'{caminho} reimplementou a fórmula do limite de atenção'
