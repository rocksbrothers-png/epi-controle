"""Phase 31 — Validação JV end-to-end no canary (inside_jv vs outside_jv)."""

import json
import sqlite3


# ── helpers ───────────────────────────────────────────────────────────────────

def _conn_with_jv_rules(rules, mode='enforced'):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('''
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, active INTEGER DEFAULT 1);
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE rule_engine_shadow_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER, user_id INTEGER, role TEXT,
            endpoint TEXT, dataset TEXT, mode TEXT,
            legacy_count INTEGER, new_count INTEGER,
            has_diff INTEGER, legacy_only TEXT, new_only TEXT, created_at TEXT
        );
        INSERT INTO companies VALUES (1, 'Empresa JV', 1);
    ''')
    framework = {
        'feature_flags': {
            'execution_mode': mode,
            'enable_new_rules_engine': True,
            'rollout_percentage': 100,
            'allow_new_engine_response': True,
        },
        'visibility_rules': rules,
    }
    conn.execute(
        "INSERT INTO app_meta VALUES (?, ?)",
        ('configuration_framework:1', json.dumps(framework)),
    )
    conn.commit()
    return conn


ACTOR = {'id': 1, 'company_id': 1, 'role': 'admin'}


# ── item_context derivation ───────────────────────────────────────────────────

def test_item_with_active_joinventure_gets_inside_jv_context():
    """Items com active_joinventure preenchido devem gerar context=inside_jv no canary."""
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn_with_jv_rules([
        {
            'id': 'rule-deny-jv',
            'role': 'admin',
            'unit_id': 10,
            'unit_context': 'inside_jv',
            'can_view_unit': False,
            'can_view_epis': False,
            'can_view_employees': True,
        }
    ])
    items = [
        {'id': 1, 'unit_id': 10, 'active_joinventure': 'JV-X'},   # inside_jv → denied by rule
        {'id': 2, 'unit_id': 10, 'active_joinventure': ''},        # outside_jv → no rule → allowed
    ]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/bootstrap',
        dataset_name='units',
        legacy_items=items,
    )
    # inside_jv unit is denied → only id=2 remains
    assert [r['id'] for r in result] == [2]


def test_item_without_active_joinventure_gets_outside_jv_context():
    """Items sem active_joinventure são outside_jv e não são afetados por regras inside_jv."""
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn_with_jv_rules([
        {
            'id': 'rule-deny-outside',
            'role': 'admin',
            'unit_id': 10,
            'unit_context': 'outside_jv',
            'can_view_unit': False,
            'can_view_epis': True,
            'can_view_employees': True,
        }
    ])
    items = [
        {'id': 1, 'unit_id': 10, 'active_joinventure': ''},      # outside_jv → denied
        {'id': 2, 'unit_id': 10, 'active_joinventure': 'JV-X'},  # inside_jv → no matching rule → allowed
    ]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/bootstrap',
        dataset_name='units',
        legacy_items=items,
    )
    assert [r['id'] for r in result] == [2]


def test_jv_rule_does_not_affect_other_units():
    """Regra JV com unit_id=10 não afeta itens de outras unidades."""
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn_with_jv_rules([
        {
            'id': 'rule-deny-unit10-jv',
            'role': 'admin',
            'unit_id': 10,
            'unit_context': 'inside_jv',
            'can_view_unit': False,
            'can_view_epis': True,
            'can_view_employees': True,
        }
    ])
    items = [
        {'id': 1, 'unit_id': 10, 'active_joinventure': 'JV-X'},  # denied
        {'id': 2, 'unit_id': 20, 'active_joinventure': 'JV-X'},  # unit_id=20, no rule → allowed
        {'id': 3, 'unit_id': 10, 'active_joinventure': ''},       # outside_jv, no matching rule → allowed
    ]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/bootstrap',
        dataset_name='units',
        legacy_items=items,
    )
    assert [r['id'] for r in result] == [2, 3]


def test_employees_filtered_by_jv_rule():
    """Regra JV com can_view_employees=False deve excluir employees de unidades JV."""
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn_with_jv_rules([
        {
            'id': 'rule-deny-employees-jv',
            'role': 'admin',
            'unit_id': 10,
            'unit_context': 'inside_jv',
            'can_view_unit': True,
            'can_view_epis': True,
            'can_view_employees': False,
        }
    ])
    items = [
        {'id': 1, 'unit_id': 10, 'active_joinventure': 'JV-X'},  # denied
        {'id': 2, 'unit_id': 10, 'active_joinventure': ''},       # outside_jv → allowed
        {'id': 3, 'unit_id': 20, 'active_joinventure': 'JV-X'},  # different unit → allowed
    ]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/bootstrap',
        dataset_name='employees',
        legacy_items=items,
    )
    assert [r['id'] for r in result] == [2, 3]


def test_epis_filtered_by_jv_rule():
    """Regra JV com can_view_epis=False deve excluir EPIs de unidades JV."""
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn_with_jv_rules([
        {
            'id': 'rule-deny-epis-jv',
            'role': 'admin',
            'unit_id': 10,
            'unit_context': 'inside_jv',
            'can_view_unit': True,
            'can_view_epis': False,
            'can_view_employees': True,
        }
    ])
    items = [
        {'id': 1, 'unit_id': 10, 'active_joinventure': 'JV-Alpha'},  # denied
        {'id': 2, 'unit_id': 10, 'active_joinventure': ''},           # outside_jv → allowed
        {'id': 3, 'unit_id': 0,  'active_joinventure': ''},           # unit_id=0 → no rule → allowed
    ]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/bootstrap',
        dataset_name='epis',
        legacy_items=items,
    )
    assert [r['id'] for r in result] == [2, 3]


def test_allow_all_rule_keeps_both_jv_contexts():
    """Regras com can_view_unit=True não filtram nenhum item."""
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn_with_jv_rules([
        {
            'id': 'rule-allow-all',
            'role': 'admin',
            'unit_id': 10,
            'unit_context': 'inside_jv',
            'can_view_unit': True,
            'can_view_epis': True,
            'can_view_employees': True,
        }
    ])
    items = [
        {'id': 1, 'unit_id': 10, 'active_joinventure': 'JV-X'},
        {'id': 2, 'unit_id': 10, 'active_joinventure': ''},
    ]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/bootstrap',
        dataset_name='units',
        legacy_items=items,
    )
    assert len(result) == 2


def test_no_rules_means_all_items_pass():
    """Sem regras de visibilidade, o motor não filtra nenhum item."""
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn_with_jv_rules([])
    items = [
        {'id': 1, 'unit_id': 10, 'active_joinventure': 'JV-X'},
        {'id': 2, 'unit_id': 20, 'active_joinventure': ''},
        {'id': 3, 'unit_id': 30, 'active_joinventure': 'JV-Y'},
    ]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/bootstrap',
        dataset_name='units',
        legacy_items=items,
    )
    assert len(result) == 3


def test_jv_diff_logged_when_items_filtered():
    """Quando o motor filtra itens, has_diff=1 deve ser registrado no shadow log."""
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn_with_jv_rules([
        {
            'id': 'rule-deny',
            'role': 'admin',
            'unit_id': 10,
            'unit_context': 'inside_jv',
            'can_view_unit': False,
            'can_view_epis': True,
            'can_view_employees': True,
        }
    ])
    items = [
        {'id': 1, 'unit_id': 10, 'active_joinventure': 'JV-X'},
        {'id': 2, 'unit_id': 20, 'active_joinventure': ''},
    ]
    canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/bootstrap',
        dataset_name='units',
        legacy_items=items,
    )
    row = conn.execute("SELECT * FROM rule_engine_shadow_log").fetchone()
    assert row is not None
    assert row['has_diff'] == 1
    assert row['legacy_count'] == 2
    assert row['new_count'] == 1


def test_shadow_mode_does_not_filter_returns_legacy():
    """No modo shadow, canary loga mas sempre retorna legacy_items."""
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn_with_jv_rules(
        [{'id': 'deny', 'role': 'admin', 'unit_id': 10, 'unit_context': 'inside_jv',
          'can_view_unit': False, 'can_view_epis': True, 'can_view_employees': True}],
        mode='shadow',
    )
    items = [
        {'id': 1, 'unit_id': 10, 'active_joinventure': 'JV-X'},
        {'id': 2, 'unit_id': 20, 'active_joinventure': ''},
    ]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/bootstrap',
        dataset_name='units',
        legacy_items=items,
    )
    # shadow mode → legacy_items returned (no filtering applied)
    assert len(result) == 2
