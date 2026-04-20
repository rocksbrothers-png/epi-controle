import json

import server_postgres


def test_get_configuration_rules_allows_global_scope(monkeypatch):
    captured_keys = []

    def fake_get_meta(_connection, key):
        captured_keys.append(key)
        return json.dumps([{'id': 'rule-1', 'role': 'user'}])

    monkeypatch.setattr(server_postgres, 'get_meta', fake_get_meta)
    payload = server_postgres.get_configuration_rules(object(), None)
    assert payload == [{'id': 'rule-1', 'role': 'user'}]
    assert captured_keys == ['configuration_rules:global']


def test_save_configuration_rules_allows_global_scope(monkeypatch):
    stored = {}

    def fake_set_meta(_connection, key, value):
        stored[key] = json.loads(value)

    monkeypatch.setattr(server_postgres, 'set_meta', fake_set_meta)
    monkeypatch.setattr(server_postgres, 'get_configuration_framework', lambda _connection, _company_id: {'visibility_rules': []})

    class DummyConnection:
        def commit(self):
            return None

    rules = server_postgres.save_configuration_rules(
        DummyConnection(),
        None,
        [{'id': 'rule-employee', 'role': 'employee', 'unit_id': 0, 'can_view_unit': True}],
    )
    assert rules[0]['unit_id'] == 0
    assert stored['configuration_rules:global'][0]['unit_id'] == 0
    assert stored['configuration_framework:global']['visibility_rules'][0]['unit_id'] == 0
