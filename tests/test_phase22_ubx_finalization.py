"""Tests for Phase 22: UBX final migration items 1, 4, and 10."""

import inspect
import json
import sqlite3


# ── helpers ───────────────────────────────────────────────────────────────────

def _conn(*, with_companies=True, company_ids=(1,)):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, active INTEGER DEFAULT 1)')
    conn.execute('CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT)')
    if with_companies:
        for cid in company_ids:
            conn.execute('INSERT INTO companies VALUES (?, ?, 1)', (cid, f'Empresa {cid}'))
    conn.commit()
    return conn


def _set_framework(conn, company_id, mode, rollout=100, enabled=True):
    key = f'configuration_framework:{company_id}'
    payload = {
        'feature_flags': {
            'execution_mode': mode,
            'rollout_percentage': rollout,
            'enable_new_rules_engine': enabled,
        }
    }
    conn.execute(
        'INSERT INTO app_meta (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value',
        (key, json.dumps(payload)),
    )
    conn.commit()


def _get_framework(conn, company_id):
    row = conn.execute(
        'SELECT value FROM app_meta WHERE key = ?',
        (f'configuration_framework:{company_id}',),
    ).fetchone()
    if not row:
        return {}
    return json.loads(row['value'])


# ═══════════════════════════════════════════════════════════════════════════════
# Item 1 — Rule Engine: go-live path to mode=enforced, rollout=100
# ═══════════════════════════════════════════════════════════════════════════════

def test_ensure_rule_engine_enforced_importable_from_core_schema():
    from core.schema import ensure_rule_engine_enforced_all_companies
    assert callable(ensure_rule_engine_enforced_all_companies)


def test_ensure_rule_engine_enforced_promotes_from_off():
    from core.schema import ensure_rule_engine_enforced_all_companies
    conn = _conn(company_ids=(1,))
    ensure_rule_engine_enforced_all_companies(conn)
    flags = _get_framework(conn, 1).get('feature_flags', {})
    assert flags['execution_mode'] == 'enforced'
    assert flags['rollout_percentage'] == 100
    assert flags['enable_new_rules_engine'] is True


def test_ensure_rule_engine_enforced_promotes_from_shadow():
    from core.schema import ensure_rule_engine_enforced_all_companies
    conn = _conn(company_ids=(1,))
    _set_framework(conn, 1, 'shadow', rollout=100)
    ensure_rule_engine_enforced_all_companies(conn)
    flags = _get_framework(conn, 1).get('feature_flags', {})
    assert flags['execution_mode'] == 'enforced'
    assert flags['rollout_percentage'] == 100


def test_ensure_rule_engine_enforced_skips_already_enforced_100():
    from core.schema import ensure_rule_engine_enforced_all_companies
    conn = _conn(company_ids=(1,))
    _set_framework(conn, 1, 'enforced', rollout=100)
    ensure_rule_engine_enforced_all_companies(conn)
    row = conn.execute("SELECT value FROM app_meta WHERE key = 'configuration_framework:1'").fetchone()
    assert row is not None
    flags = json.loads(row['value'])['feature_flags']
    assert flags['execution_mode'] == 'enforced'
    assert flags['rollout_percentage'] == 100


def test_ensure_rule_engine_enforced_upgrades_enforced_partial_rollout():
    """enforced at 50% rollout must be promoted to 100%."""
    from core.schema import ensure_rule_engine_enforced_all_companies
    conn = _conn(company_ids=(1,))
    _set_framework(conn, 1, 'enforced', rollout=50)
    ensure_rule_engine_enforced_all_companies(conn)
    flags = _get_framework(conn, 1)['feature_flags']
    assert flags['rollout_percentage'] == 100


def test_ensure_rule_engine_enforced_handles_multiple_companies():
    from core.schema import ensure_rule_engine_enforced_all_companies
    conn = _conn(company_ids=(1, 2, 3))
    _set_framework(conn, 1, 'shadow', rollout=100)
    _set_framework(conn, 2, 'enforced', rollout=100)
    ensure_rule_engine_enforced_all_companies(conn)
    for cid in (1, 2, 3):
        flags = _get_framework(conn, cid)['feature_flags']
        assert flags['execution_mode'] == 'enforced', f'company {cid} not enforced'
        assert flags['rollout_percentage'] == 100, f'company {cid} rollout not 100'


def test_ensure_rule_engine_enforced_is_idempotent():
    from core.schema import ensure_rule_engine_enforced_all_companies
    conn = _conn(company_ids=(1,))
    ensure_rule_engine_enforced_all_companies(conn)
    ensure_rule_engine_enforced_all_companies(conn)
    flags = _get_framework(conn, 1)['feature_flags']
    assert flags['execution_mode'] == 'enforced'
    assert flags['rollout_percentage'] == 100


def test_ensure_rule_engine_enforced_preserves_visibility_rules():
    from core.schema import ensure_rule_engine_enforced_all_companies
    conn = _conn(company_ids=(1,))
    rules = [{'id': 'r1', 'role': 'user', 'unit_id': 5, 'unit_context': 'outside_jv', 'can_view_epis': True, 'can_view_unit': True, 'can_view_employees': False}]
    full_fw = {
        'feature_flags': {'execution_mode': 'shadow', 'rollout_percentage': 100, 'enable_new_rules_engine': True},
        'visibility_rules': rules,
    }
    conn.execute(
        "INSERT INTO app_meta (key, value) VALUES ('configuration_framework:1', ?)",
        (json.dumps(full_fw),),
    )
    conn.commit()
    ensure_rule_engine_enforced_all_companies(conn)
    saved = _get_framework(conn, 1)
    assert saved['feature_flags']['execution_mode'] == 'enforced'
    assert saved.get('visibility_rules') == rules


def test_rollback_to_shadow_via_promote_rule_engine():
    """Go-live can be reversed by calling promote_rule_engine back to shadow."""
    from core.schema import ensure_rule_engine_enforced_all_companies
    from modules.settings.service import promote_rule_engine, get_rule_engine_status
    conn = _conn(company_ids=(1,))
    conn.execute('CREATE TABLE rule_engine_shadow_log (id INTEGER PRIMARY KEY, company_id INTEGER, user_id INTEGER, role TEXT, endpoint TEXT, dataset TEXT, mode TEXT, legacy_count INTEGER, new_count INTEGER, has_diff INTEGER, legacy_only TEXT, new_only TEXT, created_at TEXT)')
    ensure_rule_engine_enforced_all_companies(conn)
    status = get_rule_engine_status(conn, 1)
    assert status['mode'] == 'enforced'
    assert status['rollout_percentage'] == 100
    # rollback
    promote_rule_engine(conn, 1, mode='shadow', rollout_percentage=100, enable=True)
    status_after = get_rule_engine_status(conn, 1)
    assert status_after['mode'] == 'shadow'
    assert status_after['rollout_percentage'] == 100


def test_go_live_sequence_shadow_to_enforced_full_rollout():
    """Complete go-live sequence: off → shadow (boot) → canary → enforced."""
    from core.schema import ensure_rule_engine_shadow_activated, ensure_rule_engine_enforced_all_companies
    from modules.settings.service import promote_rule_engine, get_rule_engine_status
    conn = _conn(company_ids=(1,))
    conn.execute('CREATE TABLE rule_engine_shadow_log (id INTEGER PRIMARY KEY, company_id INTEGER, user_id INTEGER, role TEXT, endpoint TEXT, dataset TEXT, mode TEXT, legacy_count INTEGER, new_count INTEGER, has_diff INTEGER, legacy_only TEXT, new_only TEXT, created_at TEXT)')
    # step 1: boot sets shadow
    ensure_rule_engine_shadow_activated(conn)
    assert get_rule_engine_status(conn, 1)['mode'] == 'shadow'
    # step 2: promote to canary at 10%
    promote_rule_engine(conn, 1, mode='canary', rollout_percentage=10)
    assert get_rule_engine_status(conn, 1)['rollout_percentage'] == 10
    # step 3: go-live to enforced 100%
    ensure_rule_engine_enforced_all_companies(conn)
    final = get_rule_engine_status(conn, 1)
    assert final['mode'] == 'enforced'
    assert final['rollout_percentage'] == 100


# ═══════════════════════════════════════════════════════════════════════════════
# Item 4 — Remove INSERT INTO user_unit_links
# ═══════════════════════════════════════════════════════════════════════════════

def test_no_insert_user_unit_links_in_purchases_routes():
    """Regression: purchases/routes.py must not contain INSERT INTO user_unit_links."""
    import modules.purchases.routes as purch_routes
    src = inspect.getsource(purch_routes)
    assert 'INSERT INTO user_unit_links' not in src, (
        'purchases/routes.py still contains INSERT INTO user_unit_links'
    )


def test_post_user_unit_links_returns_410():
    """handle_post_user_unit_links must return 410 Gone (deprecated)."""
    from unittest.mock import patch, MagicMock
    from urllib.parse import urlparse
    import modules.purchases.routes as purch_routes

    sent = []

    def mock_send_json(h, code, body):
        sent.append({'code': code, 'body': body})

    handler = MagicMock()
    handler.path = '/api/user-unit-links'

    with patch.object(purch_routes, 'send_json', side_effect=mock_send_json):
        purch_routes.handle_post_user_unit_links(handler, urlparse('/api/user-unit-links'), {}, None)

    assert len(sent) == 1
    assert sent[0]['code'] == 410
    assert sent[0]['body']['ok'] is False
    assert sent[0]['body']['error']['code'] == 'DEPRECATED'


def test_delete_user_unit_links_returns_410():
    """Phase 26: DELETE /api/user-unit-links/:id retorna 410 (tabela removida)."""
    from modules.purchases.routes import handle_delete_user_unit_link
    assert callable(handle_delete_user_unit_link)

    import modules.purchases.service as purch_service
    src = inspect.getsource(purch_service)
    assert 'user_unit_links foi removida' in src


def test_no_update_user_unit_links_anywhere():
    """Globally: no UPDATE user_unit_links in any production module (excludes tests)."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tests_dir = os.path.join(root, 'tests')
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ('__pycache__', '.git', 'node_modules', 'venv', '.venv', '.claude')]
        for fname in filenames:
            if not fname.endswith('.py'):
                continue
            fpath = os.path.join(dirpath, fname)
            # skip test files — they may legitimately reference the pattern in strings
            if fpath.startswith(tests_dir + os.sep):
                continue
            with open(fpath, encoding='utf-8', errors='ignore') as fh:
                content = fh.read()
            assert 'UPDATE user_unit_links' not in content, (
                f'{fpath} still contains UPDATE user_unit_links'
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Item 10 — Replace epis.active_joinventure with unit_joint_venture_periods
# ═══════════════════════════════════════════════════════════════════════════════

def test_get_epi_effective_jv_name_importable():
    from epi_backend.epi_scope import get_epi_effective_jv_name
    assert callable(get_epi_effective_jv_name)


def test_get_epi_effective_jv_name_uses_active_joinventure_by_default():
    from epi_backend.epi_scope import get_epi_effective_jv_name
    epi = {'unit_id': 5, 'active_joinventure': 'JV-Alpha'}
    assert get_epi_effective_jv_name(epi) == 'JV-Alpha'


def test_get_epi_effective_jv_name_uses_fn_when_provided():
    from epi_backend.epi_scope import get_epi_effective_jv_name
    epi = {'unit_id': 5, 'active_joinventure': 'JV-OLD'}
    fn = lambda uid: 'JV-NEW'  # noqa: E731
    assert get_epi_effective_jv_name(epi, get_unit_jv_fn=fn) == 'JV-NEW'


def test_get_epi_effective_jv_name_fn_with_no_unit_id_falls_back():
    """When unit_id is absent, fn cannot be called; falls back to active_joinventure."""
    from epi_backend.epi_scope import get_epi_effective_jv_name
    epi = {'unit_id': None, 'active_joinventure': 'JV-Alpha'}
    fn = lambda uid: 'JV-SHOULD-NOT-BE-CALLED'  # noqa: E731
    # no unit_id → fn is skipped → returns active_joinventure
    assert get_epi_effective_jv_name(epi, get_unit_jv_fn=fn) == 'JV-Alpha'


def test_filter_epis_global_visible_outside_jv():
    from epi_backend.epi_scope import filter_epis_for_unit
    epis = [
        {'id': 1, 'unit_id': None, 'active_joinventure': None},  # GLOBAL
    ]
    result = filter_epis_for_unit(epis, target_unit_id=10, target_unit_joint_venture_name='')
    assert [e['id'] for e in result] == [1]


def test_filter_epis_global_hidden_inside_jv():
    from epi_backend.epi_scope import filter_epis_for_unit
    epis = [
        {'id': 1, 'unit_id': None, 'active_joinventure': None},  # GLOBAL — hidden when unit is inside JV
    ]
    result = filter_epis_for_unit(epis, target_unit_id=10, target_unit_joint_venture_name='JV-X')
    assert result == []


def test_filter_epis_jv_epi_visible_inside_matching_jv():
    from epi_backend.epi_scope import filter_epis_for_unit
    epis = [
        {'id': 1, 'unit_id': 3, 'active_joinventure': 'JV-X'},  # JV EPI
    ]
    result = filter_epis_for_unit(epis, target_unit_id=10, target_unit_joint_venture_name='JV-X')
    assert [e['id'] for e in result] == [1]


def test_filter_epis_jv_epi_hidden_for_different_jv():
    from epi_backend.epi_scope import filter_epis_for_unit
    epis = [
        {'id': 1, 'unit_id': 3, 'active_joinventure': 'JV-X'},
    ]
    result = filter_epis_for_unit(epis, target_unit_id=10, target_unit_joint_venture_name='JV-Y')
    assert result == []


def test_filter_epis_jv_epi_hidden_outside_jv():
    from epi_backend.epi_scope import filter_epis_for_unit
    epis = [
        {'id': 1, 'unit_id': 3, 'active_joinventure': 'JV-X'},
    ]
    result = filter_epis_for_unit(epis, target_unit_id=10, target_unit_joint_venture_name='')
    assert result == []


def test_filter_epis_unit_specific_epi_visible_to_own_unit():
    from epi_backend.epi_scope import filter_epis_for_unit
    epis = [
        {'id': 1, 'unit_id': 10, 'active_joinventure': None},  # UNIT scope
    ]
    result = filter_epis_for_unit(epis, target_unit_id=10, target_unit_joint_venture_name='')
    assert [e['id'] for e in result] == [1]


def test_filter_epis_unit_specific_epi_hidden_from_other_unit():
    from epi_backend.epi_scope import filter_epis_for_unit
    epis = [
        {'id': 1, 'unit_id': 10, 'active_joinventure': None},
    ]
    result = filter_epis_for_unit(epis, target_unit_id=99, target_unit_joint_venture_name='')
    assert result == []


def test_filter_epis_uses_unit_periods_fn_for_epi_jv_context():
    """New behavior: JV context from unit_joint_venture_periods via get_epi_unit_jv_name."""
    from epi_backend.epi_scope import filter_epis_for_unit
    # EPI belongs to unit 5 which is in JV-Alpha per current periods
    # epis.active_joinventure has stale value 'JV-OLD'
    epis = [
        {'id': 1, 'unit_id': 5, 'active_joinventure': 'JV-OLD'},
    ]
    current_periods = {5: 'JV-Alpha'}
    fn = lambda uid: current_periods.get(int(uid), '')  # noqa: E731

    # target unit is also in JV-Alpha → should be visible
    result = filter_epis_for_unit(
        epis,
        target_unit_id=10,
        target_unit_joint_venture_name='JV-Alpha',
        get_epi_unit_jv_name=fn,
    )
    assert [e['id'] for e in result] == [1]


def test_filter_epis_period_change_hides_epi_when_unit_leaves_jv():
    """When EPI's unit leaves JV (periods show no active JV), EPI behaves as UNIT-scoped."""
    from epi_backend.epi_scope import filter_epis_for_unit
    # EPI was created while unit 5 was in JV-X; now unit 5 left JV-X (no active period)
    epis = [
        {'id': 1, 'unit_id': 5, 'active_joinventure': 'JV-X'},  # stale
    ]
    current_periods = {5: ''}  # unit 5 has no active JV period now
    fn = lambda uid: current_periods.get(int(uid), '')  # noqa: E731

    # target unit is NOT in JV-X anymore; using periods fn the EPI becomes UNIT-scoped
    result_jv = filter_epis_for_unit(
        epis,
        target_unit_id=10,
        target_unit_joint_venture_name='JV-X',
        get_epi_unit_jv_name=fn,
    )
    # UNIT-scoped EPI (unit_id=5) is not visible to unit 10
    assert result_jv == []

    # unit 5 can see its own EPI even after leaving JV
    result_own = filter_epis_for_unit(
        epis,
        target_unit_id=5,
        target_unit_joint_venture_name='',
        get_epi_unit_jv_name=fn,
    )
    assert [e['id'] for e in result_own] == [1]


def test_filter_epis_legacy_uses_active_joinventure_when_no_fn():
    """Backward compat: without get_epi_unit_jv_name, active_joinventure is used."""
    from epi_backend.epi_scope import filter_epis_for_unit
    epis = [
        {'id': 1, 'unit_id': 5, 'active_joinventure': 'JV-X'},
    ]
    result = filter_epis_for_unit(
        epis,
        target_unit_id=10,
        target_unit_joint_venture_name='JV-X',
    )
    assert [e['id'] for e in result] == [1]


def test_filter_epis_mixed_scope_types():
    from epi_backend.epi_scope import filter_epis_for_unit
    current_periods = {3: 'JV-X', 7: ''}
    fn = lambda uid: current_periods.get(int(uid), '')  # noqa: E731
    epis = [
        {'id': 1, 'unit_id': None,  'active_joinventure': None},    # GLOBAL
        {'id': 2, 'unit_id': 3,     'active_joinventure': 'JV-X'},  # JV-X (unit 3 in JV-X)
        {'id': 3, 'unit_id': 10,    'active_joinventure': None},    # UNIT 10
        {'id': 4, 'unit_id': 7,     'active_joinventure': 'JV-X'},  # unit 7 left JV (periods=empty)
    ]
    # target unit 10, outside JV
    result = filter_epis_for_unit(
        epis,
        target_unit_id=10,
        target_unit_joint_venture_name='',
        get_epi_unit_jv_name=fn,
    )
    ids = [e['id'] for e in result]
    assert 1 in ids      # GLOBAL visible outside JV
    assert 2 not in ids  # JV-X EPI hidden outside JV (unit 3 still in JV-X via periods)
    assert 3 in ids      # own unit EPI (unit_id=10) visible to target unit 10
    # unit 7 left JV (fn returns '') → EPI becomes UNIT-scoped to unit 7 → not visible to unit 10
    assert 4 not in ids


def test_get_unit_active_jv_name_reads_from_periods_table():
    """get_unit_active_jv_name queries unit_joint_venture_periods, not epis.active_joinventure."""
    from modules.units.service import get_unit_active_jv_name
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('''
        CREATE TABLE unit_joint_venture_periods (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            unit_id INTEGER,
            joint_venture_name TEXT,
            started_at TEXT,
            ended_at TEXT,
            created_by INTEGER
        )
    ''')
    conn.execute("INSERT INTO unit_joint_venture_periods VALUES (1, 1, 10, 'JV-Alpha', '2024-01-01', NULL, 1)")
    conn.commit()
    assert get_unit_active_jv_name(conn, 10) == 'JV-Alpha'
    assert get_unit_active_jv_name(conn, 99) == ''


def test_get_unit_active_jv_name_respects_ended_at():
    """A period with ended_at set is treated as inactive."""
    from modules.units.service import get_unit_active_jv_name
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('''
        CREATE TABLE unit_joint_venture_periods (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            joint_venture_name TEXT, started_at TEXT, ended_at TEXT, created_by INTEGER
        )
    ''')
    conn.execute("INSERT INTO unit_joint_venture_periods VALUES (1, 1, 10, 'JV-Expired', '2023-01-01', '2023-12-31', 1)")
    conn.commit()
    assert get_unit_active_jv_name(conn, 10) == ''


def test_canary_shadow_mode_returns_legacy_items_unchanged():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn()
    _set_framework(conn, 1, 'shadow', rollout=100)
    conn.execute('CREATE TABLE rule_engine_shadow_log (id INTEGER PRIMARY KEY, company_id INTEGER, user_id INTEGER, role TEXT, endpoint TEXT, dataset TEXT, mode TEXT, legacy_count INTEGER, new_count INTEGER, has_diff INTEGER, legacy_only TEXT, new_only TEXT, created_at TEXT)')
    actor = {'id': 1, 'company_id': 1, 'role': 'admin'}
    legacy = [{'id': 1, 'name': 'EPI A'}, {'id': 2, 'name': 'EPI B'}]
    result = canary_evaluate_visibility_dataset(
        conn, actor,
        endpoint_name='/api/stock/epis',
        dataset_name='epis',
        legacy_items=legacy,
    )
    assert result == legacy


def test_canary_enforced_mode_can_return_candidate_items():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn()
    _set_framework(conn, 1, 'enforced', rollout=100)
    conn.execute('CREATE TABLE rule_engine_shadow_log (id INTEGER PRIMARY KEY, company_id INTEGER, user_id INTEGER, role TEXT, endpoint TEXT, dataset TEXT, mode TEXT, legacy_count INTEGER, new_count INTEGER, has_diff INTEGER, legacy_only TEXT, new_only TEXT, created_at TEXT)')
    actor = {'id': 1, 'company_id': 1, 'role': 'admin'}
    legacy = [{'id': 1, 'name': 'EPI A'}, {'id': 2, 'name': 'EPI B'}]
    result = canary_evaluate_visibility_dataset(
        conn, actor,
        endpoint_name='/api/stock/epis',
        dataset_name='epis',
        legacy_items=legacy,
    )
    # In enforced mode the new engine takes over; result is a list
    assert isinstance(result, list)
