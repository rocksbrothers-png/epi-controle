import server_postgres


class _DummyHandler:
    def __init__(self):
        self.path = '/api/login'
        self.command = 'POST'


def test_login_path_is_bootstrap_exempt():
    assert '/api/login' in server_postgres.BOOTSTRAP_READY_EXEMPT_PATHS


def test_require_bootstrap_ready_allows_login_when_not_ready(monkeypatch):
    server_postgres._set_bootstrap_state(
        ready=False,
        error_code='DB_SCHEMA_MISMATCH',
        error_kind='schema_health_failed',
        error_message='schema inconsistente',
        started_at='2026-05-02T00:00:00+00:00',
        completed_at='2026-05-02T00:00:05+00:00',
    )

    called = {'value': False}

    def _fake_send_json(*args, **kwargs):
        called['value'] = True
        return False

    monkeypatch.setattr(server_postgres, 'send_json', _fake_send_json)

    handler = _DummyHandler()
    assert server_postgres.EpiHandler._require_bootstrap_ready(handler, '/api/login') is True
    assert called['value'] is False


def test_require_bootstrap_ready_blocks_non_exempt_path_with_structured_503(monkeypatch):
    server_postgres._set_bootstrap_state(
        ready=False,
        error_code='SCHEMA_MIGRATION_BLOCK',
        error_kind='schema_health_failed',
        error_message='migration failed',
        started_at='2026-05-02T00:00:00+00:00',
        completed_at='2026-05-02T00:00:05+00:00',
    )

    captured = {}

    def _fake_send_json(handler, status, payload):
        captured['status'] = status
        captured['payload'] = payload
        return False

    monkeypatch.setattr(server_postgres, 'send_json', _fake_send_json)

    handler = _DummyHandler()
    result = server_postgres.EpiHandler._require_bootstrap_ready(handler, '/api/users')

    assert result is False
    assert captured['status'] == 503
    assert captured['payload']['ok'] is False
    assert captured['payload']['error']['code'] == 'SCHEMA_MIGRATION_BLOCK'
    assert captured['payload']['error']['details']['kind'] == 'schema_health_failed'
