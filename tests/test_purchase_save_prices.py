"""Auditoria F-02 — endpoint/serviço save-prices da requisição de compra.

Cobre o caminho feliz (salva preço/quantidade e move para 'quoted'), a
preservação da regra R1 (item aprovado não é alterado) e as guardas de
status (requisição já avançada não aceita novos preços).

Desde a decisão de 2026-10-22 (associação de cotação: opção C + bloqueio A),
cada preço precisa vir de uma associação linha → item confirmada pelo
operador e revalidada no backend: confirmação explícita, CA divergente
bloqueia, CA ausente exige outra identificação do produto, fornecedor nunca
basta, item da própria requisição/empresa e versão do item inalterada.
"""

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from modules.purchases.service import (
    _quote_row_signature,
    quote_row_from_association,
    save_purchase_request_prices,
    sign_quote_rows,
    validate_quote_associations,
)

ACTOR = {'id': 7, 'full_name': 'Comprador', 'role': 'buyer', 'company_id': 1}
STAMP = '2026-10-22T10:00:00+00:00'


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE purchase_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, entity_type TEXT, entity_id INTEGER,
            action TEXT, status_from TEXT DEFAULT '', status_to TEXT DEFAULT '', comment TEXT DEFAULT '',
            actor_user_id INTEGER, actor_name TEXT DEFAULT '', actor_role TEXT DEFAULT '',
            reason TEXT DEFAULT '', destination TEXT DEFAULT '', ip_address TEXT DEFAULT '',
            session_ref TEXT DEFAULT '', created_at TEXT
        );
        CREATE TABLE purchase_requests (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            status TEXT DEFAULT 'sent_to_buyer', updated_at TEXT DEFAULT ''
        );
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT DEFAULT '', ca TEXT DEFAULT '',
            manufacturer TEXT DEFAULT '', model_reference TEXT DEFAULT ''
        );
        CREATE TABLE purchase_request_items (
            id INTEGER PRIMARY KEY, purchase_request_id INTEGER, company_id INTEGER, unit_id INTEGER,
            epi_id INTEGER, epi_name TEXT DEFAULT '', ca TEXT DEFAULT '', manufacturer TEXT DEFAULT '',
            supplier TEXT DEFAULT '', quantity_requested INTEGER DEFAULT 1,
            unit_price REAL DEFAULT 0, total_price REAL DEFAULT 0, status TEXT DEFAULT 'included_in_request',
            updated_at TEXT DEFAULT ''
        );
        """
    )
    conn.execute("INSERT INTO purchase_requests (id, company_id, unit_id, status) VALUES (100, 1, 1, 'sent_to_buyer')")
    conn.execute("INSERT INTO purchase_requests (id, company_id, unit_id, status) VALUES (200, 2, 9, 'sent_to_buyer')")
    conn.executescript(
        f"""
        INSERT INTO epis (id, company_id, name, ca, manufacturer, model_reference) VALUES
            (5, 1, 'Luva Nitrílica', '12345', 'Danny', 'DA-500'),
            (6, 1, 'Capacete', '67890', 'MSA', 'V-Gard'),
            (7, 1, 'Bota de Segurança', '', 'Marluvas', 'B-42'),
            (8, 2, 'Luva Nitrílica', '12345', 'Danny', 'DA-500');
        INSERT INTO purchase_request_items
            (id, purchase_request_id, company_id, unit_id, epi_id, epi_name, ca, manufacturer, supplier,
             quantity_requested, status, updated_at)
        VALUES
            (1000, 100, 1, 1, 5, 'Luva Nitrílica', '12345', 'Danny', 'ACME', 10, 'included_in_request', '{STAMP}'),
            (1001, 100, 1, 1, 6, 'Capacete', '67890', 'MSA', 'ACME', 4, 'approved', '{STAMP}'),
            (1002, 100, 1, 1, 7, 'Bota de Segurança', '', 'Marluvas', 'ACME', 2, 'included_in_request', '{STAMP}'),
            (2000, 200, 2, 9, 8, 'Luva Nitrílica', '12345', 'Danny', 'ACME', 3, 'included_in_request', '{STAMP}');
        """
    )
    return conn


def _pr(conn, pr_id=100):
    row = conn.execute('SELECT * FROM purchase_requests WHERE id = ?', (pr_id,)).fetchone()
    return dict(row)


def _sign(payload, actor=ACTOR, issued_at=None):
    """Assina como o parse do servidor faria com a linha do arquivo."""
    issued = issued_at or datetime.now(timezone.utc).isoformat()
    payload['quote_issued_at'] = issued
    payload['quote_sig'] = _quote_row_signature(actor, quote_row_from_association(payload), issued)
    return payload


def _assoc(item_id, unit_price=5.0, *, sign=True, actor=ACTOR, issued_at=None, **overrides):
    """Associação confirmada pelo operador, como a interface envia."""
    defaults = {
        1000: {'quote_epi': 'Luva nitrilica', 'quote_ca': 'CA 12.345', 'quote_manufacturer': 'Danny'},
        1001: {'quote_epi': 'Capacete', 'quote_ca': '67890'},
        1002: {'quote_epi': 'Bota de segurança', 'quote_ca': ''},
        2000: {'quote_epi': 'Luva Nitrílica', 'quote_ca': '12345'},
    }.get(item_id, {})
    payload = {
        'item_id': item_id, 'unit_price': unit_price, 'confirmed': True,
        'expected_updated_at': STAMP, 'quote_line': 1, **defaults,
    }
    if isinstance(unit_price, (int, float)) and unit_price >= 0:
        payload['quote_unit_price'] = f'{unit_price:.2f}'
    if 'quantity' in overrides:
        payload['quote_qty'] = str(overrides['quantity'])
    payload.update(overrides)
    return _sign(payload, actor, issued_at) if sign else payload


def _price(conn, item_id):
    return float(conn.execute('SELECT unit_price FROM purchase_request_items WHERE id = ?', (item_id,)).fetchone()[0])


# ── comportamento preservado ───────────────────────────────────────────────


def test_save_prices_updates_item_and_moves_to_quoted():
    conn = _conn()
    affected, status = save_purchase_request_prices(
        conn, ACTOR, _pr(conn), [_assoc(1000, 12.5, quantity=8)], ip_address='1.2.3.4'
    )
    assert affected == [1000]
    assert status == 'quoted'
    item = conn.execute('SELECT unit_price, total_price, quantity_requested FROM purchase_request_items WHERE id = 1000').fetchone()
    assert float(item['unit_price']) == 12.5
    assert float(item['total_price']) == 100.0  # 12.5 * 8
    assert int(item['quantity_requested']) == 8
    assert conn.execute('SELECT status FROM purchase_requests WHERE id = 100').fetchone()['status'] == 'quoted'
    ev = conn.execute("SELECT action, status_to FROM purchase_events WHERE action = 'prices_saved'").fetchone()
    assert ev['status_to'] == 'quoted'


def test_save_prices_preserves_approved_item():
    conn = _conn()
    # tenta atualizar um item aprovado junto com um válido
    affected, _ = save_purchase_request_prices(
        conn, ACTOR, _pr(conn), [_assoc(1000, 9.0), _assoc(1001, 99.0, quote_line=2)], ip_address=''
    )
    assert affected == [1000]  # item aprovado (1001) ignorado — R1
    assert _price(conn, 1001) == 0  # inalterado


def test_save_prices_defaults_quantity_from_item():
    conn = _conn()
    save_purchase_request_prices(conn, ACTOR, _pr(conn), [_assoc(1000, 5.0)], ip_address='')
    item = conn.execute('SELECT total_price, quantity_requested FROM purchase_request_items WHERE id = 1000').fetchone()
    assert int(item['quantity_requested']) == 10  # mantém a quantidade original
    assert float(item['total_price']) == 50.0


def test_save_prices_rejects_when_request_already_advanced():
    conn = _conn()
    conn.execute("UPDATE purchase_requests SET status = 'approved' WHERE id = 100")
    with pytest.raises(ValueError, match='avançou'):
        save_purchase_request_prices(conn, ACTOR, _pr(conn), [_assoc(1000)], ip_address='')


def test_save_prices_requires_eligible_item():
    conn = _conn()
    with pytest.raises(ValueError, match='Nenhum item'):
        save_purchase_request_prices(conn, ACTOR, _pr(conn), [_assoc(1001)], ip_address='')


def test_save_prices_rejects_invalid_values():
    conn = _conn()
    with pytest.raises(ValueError, match='Preço'):
        save_purchase_request_prices(conn, ACTOR, _pr(conn), [_assoc(1000, -1, quote_unit_price='5.00')], ip_address='')
    with pytest.raises(ValueError, match='Quantidade'):
        save_purchase_request_prices(conn, ACTOR, _pr(conn), [_assoc(1000, 5.0, quantity=0)], ip_address='')


# ── associação confirmada: regras da decisão de 2026-10-22 ──────────────────


def test_unconfirmed_association_is_rejected_and_nothing_is_written():
    conn = _conn()
    for confirmed in (None, False, 'true', 1):
        with pytest.raises(ValueError, match='não confirmada'):
            save_purchase_request_prices(conn, ACTOR, _pr(conn), [_assoc(1000, confirmed=confirmed)], ip_address='')
    assert _price(conn, 1000) == 0


def test_divergent_ca_blocks_association():
    conn = _conn()
    with pytest.raises(ValueError, match='CA divergente'):
        save_purchase_request_prices(
            conn, ACTOR, _pr(conn), [_assoc(1000, quote_epi='Luva Nitrílica', quote_ca='99999')], ip_address=''
        )
    assert _price(conn, 1000) == 0
    assert conn.execute('SELECT COUNT(*) FROM purchase_events').fetchone()[0] == 0


def test_supplier_alone_never_associates():
    conn = _conn()
    # mesma situação do achado P2: linha de outro produto, só o fornecedor coincide
    with pytest.raises(ValueError, match='contradiz o item #1000'):
        save_purchase_request_prices(
            conn, ACTOR, _pr(conn),
            [_assoc(1000, quote_epi='Capacete Classe B', quote_ca='', quote_supplier='ACME', origin='Colaborador')],
            ip_address='',
        )
    assert _price(conn, 1000) == 0


def test_missing_ca_requires_other_product_identification():
    conn = _conn()
    # CA ausente nos dois lados e descrição de outro produto: rejeita
    with pytest.raises(ValueError, match='contradiz o item #1002'):
        save_purchase_request_prices(
            conn, ACTOR, _pr(conn), [_assoc(1002, quote_epi='Protetor auricular', quote_ca='')], ip_address=''
        )
    # CA ausente, mas descrição/modelo identificam o produto e o operador confirmou: aceita
    affected, _ = save_purchase_request_prices(
        conn, ACTOR, _pr(conn), [_assoc(1002, 31.0, quote_epi='Bota de segurança', quote_model='B-42', quote_ca='')],
        ip_address='',
    )
    assert affected == [1002]
    assert _price(conn, 1002) == 31.0


def test_price_is_written_only_to_the_confirmed_item():
    conn = _conn()
    save_purchase_request_prices(conn, ACTOR, _pr(conn), [_assoc(1002, 77.0)], ip_address='')
    assert _price(conn, 1002) == 77.0
    assert _price(conn, 1000) == 0  # mesma requisição, mesmo fornecedor: intocado
    assert _price(conn, 2000) == 0  # outra empresa: intocado


def test_same_item_cannot_receive_two_rows():
    conn = _conn()
    with pytest.raises(ValueError, match='mais de uma linha'):
        save_purchase_request_prices(
            conn, ACTOR, _pr(conn), [_assoc(1000, 5.0), _assoc(1000, 6.0, quote_line=2)], ip_address=''
        )
    assert _price(conn, 1000) == 0


def test_item_from_another_request_or_company_is_rejected():
    conn = _conn()
    with pytest.raises(ValueError, match='não pertence a esta requisição'):
        save_purchase_request_prices(conn, ACTOR, _pr(conn), [_assoc(2000)], ip_address='')
    # item corrompido: requisição da empresa 1 apontando para EPI da empresa 2
    conn.execute('UPDATE purchase_request_items SET epi_id = 8 WHERE id = 1000')
    with pytest.raises(PermissionError, match='fora da empresa'):
        save_purchase_request_prices(conn, ACTOR, _pr(conn), [_assoc(1000)], ip_address='')
    assert _price(conn, 2000) == 0


def test_file_item_id_must_match_the_confirmed_item():
    conn = _conn()
    with pytest.raises(ValueError, match='identifica o item #1002'):
        save_purchase_request_prices(conn, ACTOR, _pr(conn), [_assoc(1000, quote_item_id='1002')], ip_address='')


def test_stale_confirmation_is_rejected_after_concurrent_change():
    conn = _conn()
    # outra operação alterou o item depois que o operador conferiu
    conn.execute("UPDATE purchase_request_items SET unit_price = 3, updated_at = '2026-10-22T10:05:00+00:00' WHERE id = 1000")
    with pytest.raises(ValueError, match='alterado por outra operação'):
        save_purchase_request_prices(conn, ACTOR, _pr(conn), [_assoc(1000, 50.0)], ip_address='')
    assert _price(conn, 1000) == 3.0  # o valor concorrente não é sobrescrito


def test_concurrent_write_between_validation_and_update_is_rejected(monkeypatch):
    conn = _conn()

    def validate_then_race(connection, pr, associations, actor):
        validated = validate_quote_associations(connection, pr, associations, actor)
        connection.execute("UPDATE purchase_request_items SET updated_at = 'race' WHERE id = 1000")
        return validated

    monkeypatch.setattr('modules.purchases.service.validate_quote_associations', validate_then_race)
    with pytest.raises(ValueError, match='durante o salvamento'):
        save_purchase_request_prices(conn, ACTOR, _pr(conn), [_assoc(1000, 50.0)], ip_address='')


def test_confirmed_association_is_audited_with_operator_identity():
    conn = _conn()
    save_purchase_request_prices(conn, ACTOR, _pr(conn), [_assoc(1000, 12.5, quantity=8)], ip_address='10.0.0.9')
    ev = conn.execute(
        "SELECT * FROM purchase_events WHERE action = 'quote_association_confirmed'"
    ).fetchone()
    assert ev is not None
    assert ev['actor_user_id'] == 7
    assert ev['actor_name'] == 'Comprador'
    assert ev['actor_role'] == 'buyer'
    assert ev['ip_address'] == '10.0.0.9'
    assert ev['reason'] == 'operator_confirmed'
    assert 'item #1000' in ev['comment']
    assert 'CA 12.345' in ev['comment']
    assert 'R$ 12.50 × 8' in ev['comment']
    assert 'evidências: CA' in ev['comment']


def test_validate_quote_associations_reports_evidence():
    conn = _conn()
    [entry] = validate_quote_associations(conn, _pr(conn), [_assoc(1000, quote_model='DA-500')], ACTOR)
    assert entry['matches'] == ['CA', 'descrição', 'fabricante', 'modelo']


# ── endurecimento após a auditoria independente ─────────────────────────────


def _rejects(conn, association, message, exc=ValueError):
    with pytest.raises(exc, match=message):
        save_purchase_request_prices(conn, ACTOR, _pr(conn), [association], ip_address='')
    assert _price(conn, int(association['item_id'])) == 0


def test_parse_signature_round_trip_matches_what_the_interface_sends():
    conn = _conn()
    row = {'line': 2, 'item_id': '', 'epi': 'Luva nitrilica', 'ca': 'CA 12345', 'fabricante': 'Danny',
           'modelo': 'DA-500', 'fornecedor': 'ACME', 'tamanho': '', 'tamanho_luva': '', 'tamanho_uniforme': '',
           'qtd': '10', 'valor_unitario': '1234.56'}
    [signed] = sign_quote_rows(ACTOR, [dict(row)])
    association = {
        'item_id': 1000, 'unit_price': 1234.56, 'quantity': 10, 'confirmed': True, 'expected_updated_at': STAMP,
        'quote_line': signed['line'], 'quote_item_id': signed['item_id'], 'quote_epi': signed['epi'],
        'quote_ca': signed['ca'], 'quote_manufacturer': signed['fabricante'], 'quote_model': signed['modelo'],
        'quote_supplier': signed['fornecedor'], 'quote_size': signed['tamanho'],
        'quote_glove_size': signed['tamanho_luva'], 'quote_uniform_size': signed['tamanho_uniforme'],
        'quote_qty': signed['qtd'], 'quote_unit_price': signed['valor_unitario'],
        'quote_sig': signed['quote_sig'], 'quote_issued_at': signed['quote_issued_at'],
    }
    affected, _ = save_purchase_request_prices(conn, ACTOR, _pr(conn), [association], ip_address='')
    assert affected == [1000] and _price(conn, 1000) == 1234.56


def test_fields_changed_after_parse_are_rejected():
    conn = _conn()
    tampered = _assoc(1000, 12.5)
    tampered['quote_ca'] = ''  # tenta escapar do bloqueio de CA omitindo o CA do arquivo
    _rejects(conn, tampered, 'não conferem com o arquivo')
    tampered = _assoc(1000, 12.5)
    tampered['quote_item_id'] = '1000'  # tenta "provar" identidade com um id inventado
    _rejects(conn, tampered, 'não conferem com o arquivo')


def test_unsigned_expired_or_foreign_rows_are_rejected():
    conn = _conn()
    _rejects(conn, _assoc(1000, sign=False), 'sem a assinatura')
    old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    _rejects(conn, _assoc(1000, issued_at=old), 'mais de 24 horas')
    other = {'id': 99, 'full_name': 'Outro', 'role': 'buyer', 'company_id': 1}
    _rejects(conn, _assoc(1000, actor=other), 'não conferem com o arquivo')


def test_price_and_quantity_must_be_the_ones_in_the_file():
    conn = _conn()
    _rejects(conn, _assoc(1000, 99.0, quote_unit_price='12.50'), 'preço confirmado difere')
    _rejects(conn, _assoc(1000, 12.5, quantity=8, quote_qty='3'), 'quantidade confirmada difere')


@pytest.mark.parametrize('bad', ['inf', 'nan', '-inf'])
def test_non_finite_price_is_rejected(bad):
    conn = _conn()
    _rejects(conn, _assoc(1000, bad, quote_unit_price=bad), 'inválido')


def test_partial_description_without_ca_is_not_identification():
    conn = _conn()
    # "Luva" serviria para qualquer luva: sem CA, descrição parcial não basta
    _rejects(conn, _assoc(1000, quote_epi='Luva', quote_ca='', quote_manufacturer=''), 'sem identificação inequívoca')


def test_manufacturer_divergence_without_ca_is_rejected():
    conn = _conn()
    _rejects(conn, _assoc(1000, quote_epi='Luva Nitrílica', quote_ca='', quote_manufacturer='Vonder'),
             'fabricante diferente')


def test_matching_ca_with_contradicting_description_is_rejected():
    conn = _conn()
    _rejects(conn, _assoc(1000, quote_epi='Capacete classe B', quote_ca='12345', quote_manufacturer='MSA'),
             'contradiz o item #1000')


def test_ca_without_digits_counts_as_missing():
    conn = _conn()
    for placeholder in ('N/A', '-', 'ISENTO'):
        [entry] = validate_quote_associations(conn, _pr(conn), [_assoc(1000, quote_ca=placeholder)], ACTOR)
        assert 'CA' not in entry['matches']
        assert 'descrição' in entry['matches']


def test_current_catalogue_ca_prevails_over_item_snapshot():
    conn = _conn()
    conn.execute("UPDATE epis SET ca = '55555' WHERE id = 5")  # CA renovado no cadastro
    _rejects(conn, _assoc(1000, quote_ca='12345'), 'CA divergente')


def test_request_status_changed_concurrently_is_rejected(monkeypatch):
    conn = _conn()

    def validate_then_cancel(connection, pr, associations, actor):
        validated = validate_quote_associations(connection, pr, associations, actor)
        connection.execute("UPDATE purchase_requests SET status = 'cancelled' WHERE id = 100")
        return validated

    monkeypatch.setattr('modules.purchases.service.validate_quote_associations', validate_then_cancel)
    with pytest.raises(ValueError, match='mudou de situação'):
        save_purchase_request_prices(conn, ACTOR, _pr(conn), [_assoc(1000, 9.0)], ip_address='')
