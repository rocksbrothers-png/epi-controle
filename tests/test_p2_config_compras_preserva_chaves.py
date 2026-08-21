"""P2 — salvar a config de compras não pode apagar as outras chaves.

`purchase_config_{company_id}` guarda mais de um parâmetro. Além de
`require_admin_review`, guarda `po_approval_threshold`, que
`_po_company_approval_threshold` lê para decidir se a PO precisa de segundo
nível de aprovação.

`set_company_purchase_config` montava um dicionário novo a partir do único
campo que recebe e gravava por cima. Alternar a revisão do Admin zerava o
limite de aprovação, e o multi-nível desligava sem que nada acusasse — o
`resolve_approval_outcome` simplesmente passava a finalizar no primeiro nível.
Como esse é o único caminho de escrita da chave, o valor não voltava.

Estes testes travam a preservação. Eles são de UNIDADE: exercitam a função
real contra um SQLite em memória, não leem o arquivo-fonte.
"""

import json
import sqlite3

from modules.purchases.service import (
    _po_company_approval_threshold,
    get_company_purchase_config,
    set_company_purchase_config,
)

ADMIN = {'id': 3, 'full_name': 'Admin Geral', 'role': 'general_admin', 'company_id': 1}


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE purchase_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, entity_type TEXT, entity_id INTEGER,
            action TEXT, status_from TEXT DEFAULT '', status_to TEXT DEFAULT '', comment TEXT DEFAULT '',
            actor_user_id INTEGER, actor_name TEXT DEFAULT '', actor_role TEXT DEFAULT '',
            reason TEXT DEFAULT '', destination TEXT DEFAULT '', ip_address TEXT DEFAULT '',
            session_ref TEXT DEFAULT '', created_at TEXT
        );
        """
    )
    return conn


def _semear(conn, company_id, config):
    conn.execute(
        'INSERT INTO app_meta (key, value) VALUES (?, ?)',
        (f'purchase_config_{company_id}', json.dumps(config)),
    )


def test_alternar_revisao_do_admin_preserva_o_limite_de_aprovacao():
    conn = _conn()
    _semear(conn, 1, {'require_admin_review': True, 'po_approval_threshold': 20000.0})

    config = set_company_purchase_config(conn, ADMIN, 1, False)

    assert config['require_admin_review'] is False
    assert config['po_approval_threshold'] == 20000.0
    assert get_company_purchase_config(conn, 1)['po_approval_threshold'] == 20000.0


def test_o_multinivel_de_aprovacao_continua_ligado_apos_salvar_a_config():
    """O efeito que o bug produzia, medido onde ele doía."""
    conn = _conn()
    _semear(conn, 1, {'po_approval_threshold': 20000.0})
    assert _po_company_approval_threshold(conn, 1) == 20000.0

    set_company_purchase_config(conn, ADMIN, 1, True)

    assert _po_company_approval_threshold(conn, 1) == 20000.0, \
        'salvar a revisão do Admin voltou a desligar o segundo nível de aprovação'


def test_chaves_desconhecidas_tambem_sobrevivem():
    """A preservação não é uma lista de campos conhecidos.

    Qualquer parâmetro que passe a morar nesta chave — inclusive os de
    Unidade que virão na P3 — herda a garantia sem precisar editar o setter.
    """
    conn = _conn()
    _semear(conn, 1, {'parametro_futuro': {'a': 1}, 'outro': 'x'})

    config = set_company_purchase_config(conn, ADMIN, 1, True)

    assert config['parametro_futuro'] == {'a': 1}
    assert config['outro'] == 'x'


def test_sem_config_previa_o_resultado_continua_sendo_so_o_campo_salvo():
    conn = _conn()
    assert set_company_purchase_config(conn, ADMIN, 1, True) == {'require_admin_review': True}


def test_valor_guardado_que_nao_e_objeto_nao_derruba_o_salvamento():
    """Não há o que preservar num escalar, e propagá-lo estouraria o merge."""
    conn = _conn()
    _semear(conn, 1, 'texto-solto')

    assert set_company_purchase_config(conn, ADMIN, 1, True) == {'require_admin_review': True}


def test_o_evento_de_auditoria_continua_sendo_registrado():
    conn = _conn()
    _semear(conn, 1, {'po_approval_threshold': 500.0})

    set_company_purchase_config(conn, ADMIN, 1, True)

    eventos = conn.execute(
        "SELECT comment FROM purchase_events WHERE action = 'purchase_config_updated'"
    ).fetchall()
    assert len(eventos) == 1
    assert 'exigida' in eventos[0]['comment']


def test_a_config_de_uma_empresa_nao_vaza_para_outra():
    conn = _conn()
    _semear(conn, 1, {'po_approval_threshold': 20000.0})

    set_company_purchase_config(conn, ADMIN, 2, True)

    assert get_company_purchase_config(conn, 2) == {'require_admin_review': True}
    assert get_company_purchase_config(conn, 1)['po_approval_threshold'] == 20000.0
