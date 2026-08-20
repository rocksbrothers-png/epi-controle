"""Estoque mínimo individual por Unidade (fatia 1.1D-B0).

`epis.minimum_stock` é corporativo — chave `epi_id`, sem `unit_id`. Mas a única
rota que o editava, `POST /api/stock/minimum`, é **exclusiva de Administrador
Local e Gestor de EPI** (os dois perfis travados em UMA Unidade) e valida a
visibilidade do EPI *naquela* Unidade antes de gravar na EMPRESA INTEIRA:

    scope_unit_id = actor_operational_unit_id(connection, actor)   # a Unidade dele
    ...
    is_epi_visible_for_unit(..., target_unit_id=scope_unit_id)     # naquela Unidade
    ...
    UPDATE epis SET minimum_stock = ? WHERE id = ?                 # na empresa

O defeito não é de leitura, é **interferência de escrita**: o Gestor da Unidade
A definia 100 e sobrescrevia, em silêncio, o mínimo das Unidades B e C. Último a
salvar vencia, sem aviso a ninguém.

A mesma lacuna produzia a criticidade errada — saldo de cada Unidade contra o
mínimo da EMPRESA marca como crítica toda Unidade de uma empresa cujo estoque
esteja distribuído.

Modelo desta fatia:

    estoque corporativo     = SOMA dos saldos das Unidades
    mínimo corporativo      = APENAS padrão inicial/herdado
    estoque da Unidade      = unit_epi_stock.quantity
    mínimo da Unidade       = unit_epi_minimum_stock.minimum_stock
    criticidade operacional = saldo da Unidade <= mínimo DAQUELA Unidade

**Sem backfill, deliberadamente.** A existência da linha É a configuração da
Unidade. Criá-las em massa marcaria como `unit_configured` quem nunca
configurou nada — e não é preciso, porque o fallback já devolve o mesmo número
de hoje com `source='company_default'`.
"""

import pathlib
import re
import sqlite3

from modules.stock.service import (
    MINIMUM_SOURCE_COMPANY,
    MINIMUM_SOURCE_UNIT,
    UnitMinimum,
    is_stock_critical,
    resolve_unit_minimum_stock,
    set_unit_epi_minimum_stock,
)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SERVICE = RAIZ / 'modules/stock/service.py'
ROUTES = RAIZ / 'modules/stock/routes.py'
SQL = RAIZ / 'supabase/migrations/20260820000000_unit_epi_minimum_stock.sql'
MIGRACAO = RAIZ / 'epi_backend/migrations/025_unit_epi_minimum_stock.py'

GESTOR = {'id': 5, 'role': 'user', 'company_id': 1, 'full_name': 'Gestor da Unidade A'}


def _conexao(minimo_corporativo=100):
    """Empresa 1 com três Unidades (10, 11, 12) e um EPI com mínimo 100.

    Saldos 30 / 30 / 40 — o caso que originou a decisão: corporativo 100,
    nenhuma Unidade isoladamente alcança 100.
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
            previous_source TEXT NOT NULL DEFAULT '',
            actor_user_id INTEGER, actor_name TEXT NOT NULL DEFAULT '',
            actor_role TEXT NOT NULL DEFAULT '', ip_address TEXT NOT NULL DEFAULT '',
            user_agent TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        );
        '''
    )
    conn.execute('INSERT INTO epis (id, company_id, minimum_stock) VALUES (7, 1, ?)',
                 (minimo_corporativo,))
    conn.executemany(
        'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity) VALUES (1, ?, 7, ?)',
        [(10, 30), (11, 30), (12, 40)],
    )
    conn.commit()
    return conn


def _efetivos(conn):
    return {u: resolve_unit_minimum_stock(conn, 1, u, 7) for u in (10, 11, 12)}


# ═══════════════════════════════════════════════════════════════════════════
# Resolução e fallback
# ═══════════════════════════════════════════════════════════════════════════

def test_sem_configuracao_o_minimo_vem_do_padrao_da_empresa():
    with _conexao() as conn:
        assert resolve_unit_minimum_stock(conn, 1, 10, 7) == UnitMinimum(100, MINIMUM_SOURCE_COMPANY)


def test_com_configuracao_o_minimo_e_da_unidade():
    with _conexao() as conn:
        set_unit_epi_minimum_stock(conn, 1, 10, 7, 40, actor=GESTOR)
        assert resolve_unit_minimum_stock(conn, 1, 10, 7) == UnitMinimum(40, MINIMUM_SOURCE_UNIT)


def test_zero_configurado_e_valor_e_nao_ausencia():
    """A resolução testa a EXISTÊNCIA da linha, nunca a truthiness do valor.

    Uma Unidade que configura 0 está dizendo "só me avise ao zerar". Se a
    resolução usasse `if not minimo:`, ela receberia o padrão da empresa de
    volta e voltaria a ser alertada contra a própria decisão — o mesmo
    antipadrão que a 1.1B tirou do saldo de estoque.
    """
    with _conexao() as conn:
        set_unit_epi_minimum_stock(conn, 1, 10, 7, 0, actor=GESTOR)
        resolvido = resolve_unit_minimum_stock(conn, 1, 10, 7)
    assert resolvido == UnitMinimum(0, MINIMUM_SOURCE_UNIT), \
        'mínimo 0 configurado pela unidade caiu de volta no padrão da empresa'


def test_sem_padrao_na_empresa_cai_no_default_da_coluna():
    with _conexao(minimo_corporativo=None) as conn:
        assert resolve_unit_minimum_stock(conn, 1, 10, 7) == UnitMinimum(10, MINIMUM_SOURCE_COMPANY)


def test_a_origem_distingue_herdado_de_configurado_com_o_mesmo_numero():
    """Herdar 100 e configurar 100 dão o mesmo valor e origens diferentes —
    é para isso que `source` existe."""
    with _conexao() as conn:
        herdado = resolve_unit_minimum_stock(conn, 1, 10, 7)
        set_unit_epi_minimum_stock(conn, 1, 10, 7, 100, actor=GESTOR)
        configurado = resolve_unit_minimum_stock(conn, 1, 10, 7)
    assert herdado.value == configurado.value == 100
    assert herdado.source == MINIMUM_SOURCE_COMPANY
    assert configurado.source == MINIMUM_SOURCE_UNIT


# ═══════════════════════════════════════════════════════════════════════════
# Os seis casos exigidos para a migração
# ═══════════════════════════════════════════════════════════════════════════

def test_migracao_nao_cria_configuracao_local_artificial():
    """(1) e (2) — banco existente, nenhuma linha fabricada."""
    with _conexao() as conn:
        linhas = conn.execute('SELECT COUNT(*) AS n FROM unit_epi_minimum_stock').fetchone()['n']
    assert linhas == 0, 'a migração criou configuração para quem nunca configurou'


def test_valor_efetivo_apos_a_migracao_e_o_antigo_minimo_corporativo():
    """(3) e (4) — o número não muda, a origem diz a verdade."""
    with _conexao() as conn:
        for unidade, resolvido in _efetivos(conn).items():
            assert resolvido.value == 100, f'unidade {unidade} mudou de mínimo na migração'
            assert resolvido.source == MINIMUM_SOURCE_COMPANY


def test_apos_a_primeira_configuracao_a_origem_muda():
    """(5)"""
    with _conexao() as conn:
        assert resolve_unit_minimum_stock(conn, 1, 10, 7).source == MINIMUM_SOURCE_COMPANY
        set_unit_epi_minimum_stock(conn, 1, 10, 7, 50, actor=GESTOR)
        assert resolve_unit_minimum_stock(conn, 1, 10, 7) == UnitMinimum(50, MINIMUM_SOURCE_UNIT)


def test_alterar_a_nao_modifica_b_nem_c():
    """(6) — o coração da fatia: o defeito era exatamente este.

    A sabotagem que este teste pega é voltar ao `UPDATE epis SET
    minimum_stock`, que mudaria as três de uma vez.
    """
    with _conexao() as conn:
        set_unit_epi_minimum_stock(conn, 1, 10, 7, 50, actor=GESTOR)
        efetivos = _efetivos(conn)
        corporativo = conn.execute('SELECT minimum_stock FROM epis WHERE id = 7').fetchone()

    assert efetivos[10] == UnitMinimum(50, MINIMUM_SOURCE_UNIT)
    assert efetivos[11] == UnitMinimum(100, MINIMUM_SOURCE_COMPANY), 'a Unidade B foi afetada'
    assert efetivos[12] == UnitMinimum(100, MINIMUM_SOURCE_COMPANY), 'a Unidade C foi afetada'
    assert corporativo['minimum_stock'] == 100, \
        'o padrão da empresa foi reescrito por uma decisão de uma unidade só'


# ═══════════════════════════════════════════════════════════════════════════
# Criticidade operacional
# ═══════════════════════════════════════════════════════════════════════════

def test_o_caso_que_originou_a_decisao():
    """Mínimo 100 com 30/30/40 distribuídos.

    Logo após a migração, todas herdam 100 e as três continuam críticas —
    **o comportamento de hoje, preservado de propósito**. O que fica travado é
    que o corporativo (100) não é o operando: quando cada Unidade configurar o
    seu mínimo real, o alerta falso desaparece sem nenhuma mudança de código.
    """
    with _conexao() as conn:
        saldos = {10: 30, 11: 30, 12: 40}

        antes = {u: is_stock_critical(saldos[u], m.value) for u, m in _efetivos(conn).items()}
        assert antes == {10: True, 11: True, 12: True}, \
            'o comportamento mudou na migração; o fallback deveria preservá-lo'

        # Cada Unidade define o mínimo que de fato pratica.
        set_unit_epi_minimum_stock(conn, 1, 10, 7, 40, actor=GESTOR)   # 30 <= 40 → crítica
        set_unit_epi_minimum_stock(conn, 1, 11, 7, 25, actor=GESTOR)   # 30 <= 25 → não
        set_unit_epi_minimum_stock(conn, 1, 12, 7, 40, actor=GESTOR)   # 40 <= 40 → crítica

        depois = {u: is_stock_critical(saldos[u], m.value) for u, m in _efetivos(conn).items()}
    assert depois == {10: True, 11: False, 12: True}

    # E o corporativo não participa de nenhuma dessas decisões: 100 <= 100
    # diria "crítico" para as três, inclusive para a Unidade B.
    assert is_stock_critical(sum(saldos.values()), 100) is True
    assert depois[11] is False, 'o mínimo corporativo voltou a decidir a criticidade local'


def test_a_soma_das_unidades_e_o_estoque_corporativo():
    with _conexao() as conn:
        total = conn.execute(
            'SELECT SUM(quantity) AS t FROM unit_epi_stock WHERE company_id = 1 AND epi_id = 7'
        ).fetchone()['t']
    assert total == 100


# ═══════════════════════════════════════════════════════════════════════════
# Auditoria
# ═══════════════════════════════════════════════════════════════════════════

def _auditoria(conn):
    return [dict(r) for r in conn.execute(
        'SELECT * FROM unit_epi_minimum_stock_audit_logs ORDER BY id'
    ).fetchall()]


def test_a_primeira_configuracao_registra_a_transicao_do_padrao():
    with _conexao() as conn:
        set_unit_epi_minimum_stock(conn, 1, 10, 7, 30, actor=GESTOR)
        registros = _auditoria(conn)
    assert len(registros) == 1
    r = registros[0]
    assert r['previous_minimum_stock'] is None, \
        'sem configuração anterior o valor tem de ser NULL, não o herdado'
    assert r['previous_source'] == MINIMUM_SOURCE_COMPANY
    assert r['new_minimum_stock'] == 30
    assert (r['company_id'], r['unit_id'], r['epi_id']) == (1, 10, 7)


def test_a_trajetoria_completa_fica_registrada():
    """HSEQ: demonstrar que o mínimo era 10, foi para 30, depois 50 — por quem
    e quando."""
    with _conexao() as conn:
        for valor in (10, 30, 50):
            set_unit_epi_minimum_stock(conn, 1, 10, 7, valor, actor=GESTOR)
        registros = _auditoria(conn)

    assert [r['new_minimum_stock'] for r in registros] == [10, 30, 50]
    assert [r['previous_minimum_stock'] for r in registros] == [None, 10, 30]
    assert [r['previous_source'] for r in registros] == [
        MINIMUM_SOURCE_COMPANY, MINIMUM_SOURCE_UNIT, MINIMUM_SOURCE_UNIT,
    ]
    for r in registros:
        assert r['actor_user_id'] == 5
        assert r['actor_name'] == 'Gestor da Unidade A'
        assert r['actor_role'] == 'user'
        assert r['created_at'], 'registro de auditoria sem data'


def test_a_auditoria_guarda_metadados_de_requisicao():
    with _conexao() as conn:
        set_unit_epi_minimum_stock(
            conn, 1, 10, 7, 30, actor=GESTOR,
            ip_address='203.0.113.7', user_agent='EpiApp/1.0',
        )
        r = _auditoria(conn)[0]
    assert r['ip_address'] == '203.0.113.7'
    assert r['user_agent'] == 'EpiApp/1.0'


def test_reconfigurar_atualiza_a_linha_sem_duplicar():
    with _conexao() as conn:
        set_unit_epi_minimum_stock(conn, 1, 10, 7, 30, actor=GESTOR)
        set_unit_epi_minimum_stock(conn, 1, 10, 7, 50, actor=GESTOR)
        linhas = conn.execute(
            'SELECT COUNT(*) AS n FROM unit_epi_minimum_stock '
            'WHERE company_id = 1 AND unit_id = 10 AND epi_id = 7'
        ).fetchone()['n']
        assert linhas == 1
        assert resolve_unit_minimum_stock(conn, 1, 10, 7).value == 50
        assert len(_auditoria(conn)) == 2, 'a segunda alteração não foi auditada'


def test_valor_negativo_e_normalizado_para_zero():
    with _conexao() as conn:
        assert set_unit_epi_minimum_stock(conn, 1, 10, 7, -5, actor=GESTOR).value == 0


# ═══════════════════════════════════════════════════════════════════════════
# Fiação e sabotagem
# ═══════════════════════════════════════════════════════════════════════════

def _sem_comentarios(fonte: str) -> str:
    """Descarta comentários: eles CITAM o padrão proibido para explicá-lo."""
    return '\n'.join(
        linha for linha in fonte.split('\n') if not linha.lstrip().startswith('#')
    )


def test_a_escrita_corporativa_nao_existe_mais():
    """Sabotagem central: reintroduzir `UPDATE epis SET minimum_stock` devolve
    a interferência entre Unidades."""
    fonte = _sem_comentarios(SERVICE.read_text(encoding='utf-8'))
    assert not re.search(r'UPDATE\s+epis\s+SET\s+minimum_stock', fonte, re.I), \
        'voltou a escrita no mínimo da EMPRESA a partir de uma rota de Unidade'
    assert 'def set_epi_minimum_stock' not in fonte, \
        'a função cuja semântica é a escrita proibida voltou a existir'


def _corpo_de(nome: str) -> str:
    texto = ROUTES.read_text(encoding='utf-8')
    inicio = texto.index(f'def {nome}')
    return _sem_comentarios(texto[inicio:texto.index('\ndef ', inicio + 1)])


def test_a_rota_grava_por_unidade_e_audita():
    corpo = _corpo_de('handle_post_stock_minimum')
    assert 'set_unit_epi_minimum_stock(' in corpo
    assert 'set_epi_minimum_stock(' not in corpo.replace('set_unit_epi_minimum_stock(', '')
    assert 'get_client_ip(handler)' in corpo and '_user_agent(handler)' in corpo
    # A resolução da Unidade migrou para a guarda compartilhada na #271 — três
    # rotas de configuração passaram a existir e três cópias da autorização
    # divergiriam no primeiro ajuste feito num lado só. O ponto único continua
    # sendo `resolve_unit_scope`; só mudou de altura.
    assert '_authorize_stock_config_write(' in corpo, \
        'a rota deixou de passar pela guarda de autorização compartilhada'
    guarda = _corpo_de('_authorize_stock_config_write')
    assert 'resolve_unit_scope(' in guarda, \
        'a unidade da escrita deixou de vir do ponto único de resolução (1.1D-A)'
    assert 'is_epi_visible_for_unit(' in guarda, \
        'a guarda perdeu a checagem de visibilidade do EPI na unidade'


def test_a_rota_devolve_a_unidade_e_a_origem():
    texto = ROUTES.read_text(encoding='utf-8')
    inicio = texto.index('def handle_post_stock_minimum')
    corpo = texto[inicio:texto.index('\ndef ', inicio + 1)]
    for campo in ("'unit_id'", "'minimum_stock_source'"):
        assert campo in corpo, f'{campo} sumiu da resposta do POST'


def test_a_migracao_nao_tem_backfill():
    """A ausência é o contrato, não um esquecimento.

    Um `INSERT INTO unit_epi_minimum_stock ... SELECT` na migração marcaria
    como `unit_configured` toda Unidade que nunca configurou nada, destruindo
    a distinção que a tabela existe para registrar.
    """
    sql = SQL.read_text(encoding='utf-8')
    codigo = '\n'.join(l for l in sql.split('\n') if not l.lstrip().startswith('--'))
    assert 'INSERT INTO unit_epi_minimum_stock' not in codigo, \
        'a migração voltou a fabricar configuração local'
    assert 'CREATE TABLE IF NOT EXISTS unit_epi_minimum_stock' in codigo


def test_a_migracao_habilita_rls_nas_duas_tabelas():
    """Sem RLS a tabela é legível pela chave anon do PostgREST — e o job
    `PostgreSQL Schema & Multi-Tenant` reprova o build."""
    sql = SQL.read_text(encoding='utf-8')
    assert 'ENABLE ROW LEVEL SECURITY' in sql
    assert 'CREATE POLICY' in sql and 'block_direct_api_access' in sql
    for tabela in ('unit_epi_minimum_stock', 'unit_epi_minimum_stock_audit_logs'):
        assert tabela in sql


def test_a_chave_conceitual_e_company_unit_epi():
    sql = SQL.read_text(encoding='utf-8')
    assert re.search(r'UNIQUE\s*\(\s*company_id,\s*unit_id,\s*epi_id\s*\)', sql), \
        'a chave deixou de impedir duas linhas para o mesmo par Unidade/EPI'


def test_o_par_migration_python_sql_existe():
    """ADR-0005: o módulo Python é a fonte operacional; o `.sql` é o par de
    referência. O pareamento já divergiu uma vez sem ninguém notar."""
    assert MIGRACAO.exists() and SQL.exists()
    modulo = MIGRACAO.read_text(encoding='utf-8')
    assert "MIGRATION_ID = '025_unit_epi_minimum_stock'" in modulo
    assert SQL.name in modulo, 'o módulo aponta para outro arquivo .sql'


def test_o_minimo_por_unidade_nao_vazou_para_os_consumidores_ainda():
    """Escopo da B0: a fatia entrega a FONTE, não migra consumidor.

    `/api/stock/low`, demandas de compra e `replenishment` seguem cruzando
    saldo local com mínimo corporativo — dívida registrada, corrigida nas
    próximas fatias. Quando forem migrados, este teste falha pedindo a
    atualização, que é o objetivo: a dívida não some em silêncio.
    """
    pendentes = {
        'modules/stock/service.py': 'def fetch_low_stock_items',
        'modules/purchases/service.py': 'ues.quantity <= ep.minimum_stock',
        'modules/stock/replenishment.py': 'def _epi_levels',
    }
    for caminho, ancora in pendentes.items():
        fonte = (RAIZ / caminho).read_text(encoding='utf-8')
        assert ancora in fonte, f'{caminho} mudou; revise a dívida registrada'
        assert 'resolve_unit_minimum_stock' not in fonte or caminho == 'modules/stock/service.py', \
            f'{caminho} foi migrado — atualize esta lista e a issue de dívida'
